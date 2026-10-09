import { Injectable } from '@nestjs/common';
import {
  classifyTransaction,
  exportCategory,
  type enquirySearchSchema,
  type EnquiryResultDto,
  type EnquiryRowDto,
  type WatchStatus,
} from '@transmatch/shared';
import ExcelJS from 'exceljs';
import type { z } from 'zod';
import { WatchlistService } from '../admin/watchlist.service.js';
import { AuditService } from '../audit/audit.service.js';
import { Database } from '../database/database.js';
import { contains, Where } from '../database/sql.js';

type EnquirySearch = z.infer<typeof enquirySearchSchema>;

const SEARCH_LIMIT = 10000;

const CONDITION_STATUS: Record<Exclude<EnquirySearch['condition'], 'All'>, WatchStatus> = {
  Blacklisted: 'BLACKLISTED',
  'Blacklisted-PartialMatch': 'BLACKLISTED_PARTIAL',
  Suspicious: 'SUSPICIOUS',
  Whitelist: 'NONE',
};

const ENTRY_DATE = `(t.dtt_created_date AT TIME ZONE 'Asia/Kuala_Lumpur')::date`;

const SELECT = `
  SELECT t.vch_transaction_id AS "transactionId",
         c.vch_customer_code AS "customerCode", c.vch_customer_name AS "customerName",
         trim(replace(trim(coalesce(t.vch_trn_desc_1, '')), '  ', ' ') || ' ' ||
              replace(trim(coalesce(t.vch_trn_desc_2, '')), '  ', '')) AS "description",
         t.vch_target_name AS "targetName",
         coalesce(b.vch_bank_display_name, b.vch_bank_name) AS "bankName",
         t.num_credit_amount AS "creditAmount", t.num_debit_amount AS "debitAmount",
         t.dtt_transaction_date AS "transactionDate", t.dtt_created_date AS "entryDate",
         t.bol_printed_stt AS "printed", u.vch_user_name AS "agentName", t.vch_file_name AS "fileName"
  FROM tm.tm_trn_transaction t
  JOIN tm.tm_mst_customer c ON c.vch_customer_id = t.vch_customer_id
  JOIN tm.tm_mst_bank b ON b.vch_bank_id = t.vch_bank_id
  JOIN tm.tm_mst_user u ON u.vch_user_id = t.vch_agent_user_id`;

type RawRow = Omit<EnquiryRowDto, 'watchStatus'>;

const MONTHS = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];

/** 2024-12-01 -> 01-Dec-24 */
function shortDate(iso: string): string {
  const [year, month, day] = iso.split('-');
  return `${day}-${MONTHS[Number(month) - 1]}-${year.slice(2)}`;
}

const money = (n: number) => n.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 });

/** Entry timestamp in Malaysia time: YYYY-MM-DD HH:MM:SS */
const entryDateTime = (iso: string) =>
  new Date(iso).toLocaleString('sv-SE', { timeZone: 'Asia/Kuala_Lumpur' });

@Injectable()
export class ReportsService {
  constructor(
    private readonly db: Database,
    private readonly watchlist: WatchlistService,
    private readonly audit: AuditService,
  ) {}

  async enquiry(filter: EnquirySearch): Promise<EnquiryResultDto> {
    const where = new Where('t.bol_rec_actv_stt');
    if (filter.customerCode) where.add('c.vch_customer_code ILIKE ?', contains(filter.customerCode));
    if (filter.customerName) {
      if (filter.customerNameMatch === 'Equal') where.add('c.vch_customer_name = ?', filter.customerName);
      else where.add('c.vch_customer_name ILIKE ?', contains(filter.customerName));
    }
    if (filter.description) {
      if (filter.descriptionMatch === 'Equal') {
        where.add('(t.vch_trn_desc_1 = ? OR t.vch_trn_desc_2 = ?)', filter.description, filter.description);
      } else {
        const pattern = contains(filter.description);
        where.add('(t.vch_trn_desc_1 ILIKE ? OR t.vch_trn_desc_2 ILIKE ?)', pattern, pattern);
      }
    }
    if (filter.bankName) where.add('b.vch_bank_name = ?', filter.bankName);
    if (filter.fileName) where.add('t.vch_file_name = ?', filter.fileName);
    if (filter.printed !== 'All') where.add('t.bol_printed_stt = ?', filter.printed === 'Yes');
    if (filter.agentUserId) where.add('t.vch_agent_user_id = ?', filter.agentUserId);

    const dateColumn = filter.dateType === 'entry' ? ENTRY_DATE : 't.dtt_transaction_date';
    if (filter.dateFrom) where.add(`${dateColumn} >= ?::date`, filter.dateFrom);
    if (filter.dateTo) where.add(`${dateColumn} <= ?::date`, filter.dateTo);

    const raw = await this.db.query<RawRow>(
      `${SELECT} ${where.sql} ORDER BY t.dtt_transaction_date DESC, t.vch_transaction_id LIMIT ${SEARCH_LIMIT + 1}`,
      where.params,
    );
    const truncated = raw.length > SEARCH_LIMIT;

    const lists = await this.watchlist.loadLists();
    let rows: EnquiryRowDto[] = raw
      .slice(0, SEARCH_LIMIT)
      .map((row) => ({ ...row, watchStatus: classifyTransaction(row.description, lists) }));
    if (filter.condition !== 'All') {
      const wanted = CONDITION_STATUS[filter.condition];
      rows = rows.filter((row) => row.watchStatus === wanted);
    }
    return { rows, truncated };
  }

  /** Plain-text report: per customer, transactions grouped under the keyword or name they matched. */
  async exportText(transactionIds: string[], userId: string): Promise<string> {
    const rows = await this.loadRows(transactionIds);
    const lists = await this.watchlist.loadLists();

    interface CustomerGroup {
      code: string;
      name: string;
      blacklisted: Map<string, string[]>;
      suspected: Map<string, string[]>;
      others: Map<string, string[]>;
    }
    const customers = new Map<string, CustomerGroup>();
    const agents = new Set<string>();
    const push = (map: Map<string, string[]>, key: string, line: string) => {
      const lines = map.get(key);
      if (lines) lines.push(line);
      else map.set(key, [line]);
    };

    for (const row of rows) {
      agents.add(row.agentName);
      const customerKey = `${row.customerCode}\u0000${row.customerName}`;
      let group = customers.get(customerKey);
      if (!group) {
        group = { code: row.customerCode, name: row.customerName, blacklisted: new Map(), suspected: new Map(), others: new Map() };
        customers.set(customerKey, group);
      }

      // Credits are shown with +, debits with -
      let amount = '+0.00';
      if (row.creditAmount > 0) amount = `+${money(row.creditAmount)}`;
      else if (row.debitAmount > 0) amount = `-${money(row.debitAmount)}`;
      const line = `${shortDate(row.transactionDate)} | RM ${amount}`;

      const { category, keyword } = exportCategory(row.description, lists);
      if (category === 'Blacklisted') push(group.blacklisted, keyword!, line);
      else if (category === 'Suspected') push(group.suspected, keyword!, line);
      else push(group.others, row.targetName ?? '', line);
    }

    const out: string[] = [];
    const section = (title: string, groups: Map<string, string[]>) => {
      if (groups.size === 0) return;
      out.push(title, '===================================');
      for (const [key, lines] of groups) {
        out.push(key, '- - - - - - - - - - - - - - - -', ...lines, '');
      }
    };
    for (const group of customers.values()) {
      out.push(`Customer ID: ${group.code}`, `Customer: ${group.name}\n`);
      section('BLACKLISTED', group.blacklisted);
      section('SUSPECTED', group.suspected);
      section('OTHERS', group.others);
      out.push('');
    }
    for (const agent of agents) out.push(`Agent Name: ${agent}`);

    await this.audit.log(userId, 'EXPORT', 'TM_TRN_TRANSACTION', null, { format: 'text', rows: rows.length });
    return out.join('\n');
  }

  /** Excel report: one block of rows per customer. */
  async exportExcel(transactionIds: string[], userId: string): Promise<Buffer> {
    const rows = await this.loadRows(transactionIds);
    const lists = await this.watchlist.loadLists();

    const byCustomer = new Map<string, RawRow[]>();
    for (const row of rows) {
      const key = `${row.customerCode}\u0000${row.customerName}`;
      const list = byCustomer.get(key);
      if (list) list.push(row);
      else byCustomer.set(key, [row]);
    }

    const workbook = new ExcelJS.Workbook();
    const sheet = workbook.addWorksheet('Transactions');
    for (const customerRows of byCustomer.values()) {
      sheet.addRow([`Customer ID: ${customerRows[0].customerCode}`]);
      sheet.addRow([`Customer Name: ${customerRows[0].customerName}`]);
      sheet.addRow([]);
      sheet.addRow([
        'Category Keyword',
        'Category',
        'Transaction Date',
        'Transaction Description',
        'Target Audience',
        'Bank Display Name',
        'Credit Amount',
        'Debit Amount',
        'Data Entry Date',
        'Printed Status',
        'Agent Name',
        'File Name',
      ]).font = { bold: true };

      for (const row of customerRows) {
        const { category, keyword } = exportCategory(row.description, lists);
        sheet.addRow([
          keyword ?? row.targetName ?? '',
          category,
          shortDate(row.transactionDate),
          row.description,
          row.targetName ?? '',
          row.bankName ?? '',
          row.creditAmount,
          row.debitAmount,
          entryDateTime(row.entryDate),
          row.printed ? 'Y' : 'N',
          row.agentName,
          row.fileName ?? '',
        ]);
      }
      sheet.addRow([]);
    }
    sheet.getColumn(7).numFmt = '#,##0.00';
    sheet.getColumn(8).numFmt = '#,##0.00';

    await this.audit.log(userId, 'EXPORT', 'TM_TRN_TRANSACTION', null, { format: 'excel', rows: rows.length });
    return Buffer.from(await workbook.xlsx.writeBuffer());
  }

  /** Loads the selected transactions, kept in the order they were selected. */
  private async loadRows(transactionIds: string[]): Promise<RawRow[]> {
    const rows = await this.db.query<RawRow>(
      `${SELECT} WHERE t.vch_transaction_id = ANY($1::varchar[]) AND t.bol_rec_actv_stt`,
      [transactionIds],
    );
    const byId = new Map(rows.map((row) => [row.transactionId, row]));
    return transactionIds.map((id) => byId.get(id)).filter((row): row is RawRow => row !== undefined);
  }
}
