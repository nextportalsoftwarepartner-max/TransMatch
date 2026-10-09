import { BadRequestException, ConflictException, Injectable, NotFoundException } from '@nestjs/common';
import type {
  enrichmentSearchSchema,
  OptionDto,
  saveBatchSchema,
  StatementPreviewDto,
  TransactionDetailDto,
  TransactionListRowDto,
  updateTransactionSchema,
} from '@transmatch/shared';
import type { z } from 'zod';
import { AuditService } from '../audit/audit.service.js';
import { Database, type Queryable, type SqlParam } from '../database/database.js';
import { contains, Where } from '../database/sql.js';
import { StatementExtractionService } from './statement-extraction.service.js';

type SaveBatch = z.infer<typeof saveBatchSchema>;
type UpdateTransaction = z.infer<typeof updateTransactionSchema>;
type EnrichmentSearch = z.infer<typeof enrichmentSearchSchema>;

const SEARCH_LIMIT = 5000;
const INSERT_CHUNK = 200;

// Placeholders the statement templates produce when a detail could not be read
const UNKNOWN_BANK = new Set(['unknown', 'unknown bank']);
const UNKNOWN_CUSTOMER = new Set(['unknown', 'unknown customer']);

// Entry date as the business sees it (Malaysia time)
const ENTRY_DATE = `(t.dtt_created_date AT TIME ZONE 'Asia/Kuala_Lumpur')::date`;

@Injectable()
export class TransactionsService {
  constructor(
    private readonly db: Database,
    private readonly audit: AuditService,
    private readonly extraction: StatementExtractionService,
  ) {}

  // ---- PDF upload ----

  /** Reads an uploaded statement and returns it for review; nothing is saved yet. */
  async previewStatement(fileName: string, pdf: Uint8Array, bankId?: number): Promise<StatementPreviewDto> {
    await this.assertFileNotUploaded(this.db, fileName);

    const statement = await this.extraction.extract(pdf, bankId);
    const { info } = statement;

    // A customer already on file under this name brings its code along
    const customerName = info.customerName.trim();
    const known = customerName
      ? await this.db.queryOne<{ code: string }>(
          `SELECT vch_customer_code AS "code" FROM tm.tm_mst_customer WHERE vch_customer_name = $1 AND bol_rec_actv_stt`,
          [customerName],
        )
      : null;

    return {
      fileName,
      bankTemplate: statement.bankTemplate,
      bankName: info.bankName,
      bankRegistrationNo: info.bankRegistrationNo,
      bankAddress: info.bankAddress,
      customerCode: known?.code ?? '',
      customerKnown: !!known,
      customerName,
      customerAddress: info.customerAddress,
      statementDate: info.statementDateIso,
      accountNumber: info.accountNumber,
      transactions: statement.transactions.map((trx) => ({
        transactionDate: trx.dateIso,
        rawDate: trx.date,
        description: trx.description,
        descriptionOthers: trx.descriptionOthers,
        targetName: trx.targetName,
        creditAmount: trx.creditAmount,
        debitAmount: trx.debitAmount,
        statementBalance: trx.statementBalance,
      })),
    };
  }

  // ---- Save (PDF upload and manual input) ----

  /** Saves a reviewed statement or a manual-entry session: all rows or none. */
  async saveBatch(input: SaveBatch, userId: string): Promise<{ batchId: string; saved: number }> {
    if (UNKNOWN_BANK.has(input.bank.name.toLowerCase())) {
      throw new BadRequestException('Bank Name is invalid or unknown.');
    }
    if (UNKNOWN_CUSTOMER.has(input.customer.name.toLowerCase())) {
      throw new BadRequestException('Customer Name is invalid or unknown.');
    }

    return this.db.transaction(async (tx) => {
      if (input.source === 'PU' && input.fileName) await this.assertFileNotUploaded(tx, input.fileName);

      const source = await tx.query<{ id: string }>(
        `SELECT vch_data_entry_source_id AS "id" FROM tm.tm_mst_data_entry_source
         WHERE vch_source_code = $1 AND bol_rec_actv_stt`,
        [input.source],
      );
      if (source.length === 0) throw new BadRequestException(`Data entry source ${input.source} is not set up.`);

      const bankId = await this.getOrCreateBank(tx, input.bank, userId);
      const customerId = await this.getOrCreateCustomer(tx, input.customer, userId);

      const [batch] = await tx.query<{ id: string }>(
        `INSERT INTO tm.tm_trn_import_batch (
           vch_data_entry_source_id, vch_bank_id, vch_customer_id, vch_file_name, vch_account_no,
           dtt_statement_date, num_total_rows, vch_created_by
         ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
         RETURNING vch_import_batch_id AS "id"`,
        [source[0].id, bankId, customerId, input.fileName, input.accountNo, input.statementDate, input.transactions.length, userId],
      );

      // Shared by every row of the batch: $1..$9
      const shared: SqlParam[] = [
        batch.id,
        bankId,
        source[0].id,
        customerId,
        userId,
        input.accountNo,
        input.statementDate,
        input.fileName,
        userId,
      ];
      for (let start = 0; start < input.transactions.length; start += INSERT_CHUNK) {
        const chunk = input.transactions.slice(start, start + INSERT_CHUNK);
        const params = [...shared];
        const values = chunk.map((row) => {
          const base = params.length;
          params.push(
            row.transactionDate,
            row.description,
            row.descriptionOthers,
            row.targetName,
            row.creditAmount,
            row.debitAmount,
            row.statementBalance,
          );
          const p = (n: number) => `$${base + n}`;
          return `($1, $2, $3, $4, $5, $6, $7, ${p(1)}, ${p(2)}, ${p(3)}, ${p(4)}, ${p(5)}, ${p(6)}, ${p(7)}, $8, $9)`;
        });
        await tx.query(
          `INSERT INTO tm.tm_trn_transaction (
             vch_import_batch_id, vch_bank_id, vch_data_entry_source_id, vch_customer_id, vch_agent_user_id,
             vch_account_no, dtt_statement_date, dtt_transaction_date,
             vch_trn_desc_1, vch_trn_desc_2, vch_target_name,
             num_credit_amount, num_debit_amount, num_statement_balance,
             vch_file_name, vch_created_by
           ) VALUES ${values.join(', ')}`,
          params,
        );
      }

      await this.audit.log(
        userId,
        'IMPORT',
        'TM_TRN_IMPORT_BATCH',
        batch.id,
        { source: input.source, fileName: input.fileName, rows: input.transactions.length },
        tx,
      );
      return { batchId: batch.id, saved: input.transactions.length };
    });
  }

  // ---- Data enrichment ----

  async search(filter: EnrichmentSearch): Promise<TransactionListRowDto[]> {
    const where = new Where('t.bol_rec_actv_stt');
    if (filter.customerCode) where.add('c.vch_customer_code = ?', filter.customerCode);
    if (filter.customerName) {
      if (filter.customerNameMatch === 'Equal') where.add('c.vch_customer_name = ?', filter.customerName);
      else where.add('c.vch_customer_name ILIKE ?', contains(filter.customerName));
    }
    if (filter.accountNo) where.add('t.vch_account_no ILIKE ?', contains(filter.accountNo));
    if (filter.targetName) where.add('t.vch_target_name ILIKE ?', contains(filter.targetName));
    if (filter.fileName) where.add('t.vch_file_name = ?', filter.fileName);
    if (filter.description) {
      if (filter.descriptionMatch === 'Equal') {
        where.add('(t.vch_trn_desc_1 = ? OR t.vch_trn_desc_2 = ?)', filter.description, filter.description);
      } else {
        const pattern = contains(filter.description);
        where.add('(t.vch_trn_desc_1 ILIKE ? OR t.vch_trn_desc_2 ILIKE ?)', pattern, pattern);
      }
    }
    const dateColumn = filter.dateType === 'entry' ? ENTRY_DATE : 't.dtt_transaction_date';
    if (filter.dateFrom) where.add(`${dateColumn} >= ?::date`, filter.dateFrom);
    if (filter.dateTo) where.add(`${dateColumn} <= ?::date`, filter.dateTo);

    return this.db.query<TransactionListRowDto>(
      `SELECT t.vch_transaction_id AS "transactionId", c.vch_customer_code AS "customerCode",
              c.vch_customer_name AS "customerName", t.vch_account_no AS "accountNo",
              t.vch_target_name AS "targetName", t.vch_file_name AS "fileName",
              trim(replace(trim(coalesce(t.vch_trn_desc_1, '')), '  ', ' ') || ' ' ||
                   replace(trim(coalesce(t.vch_trn_desc_2, '')), '  ', ' ')) AS "description",
              t.dtt_transaction_date AS "transactionDate", t.dtt_created_date AS "entryDate"
       FROM tm.tm_trn_transaction t
       JOIN tm.tm_mst_customer c ON c.vch_customer_id = t.vch_customer_id
       ${where.sql}
       ORDER BY t.vch_transaction_id
       LIMIT ${SEARCH_LIMIT}`,
      where.params,
    );
  }

  async get(transactionId: string): Promise<TransactionDetailDto> {
    const row = await this.db.queryOne<TransactionDetailDto>(
      `SELECT t.vch_transaction_id AS "transactionId", t.vch_file_name AS "fileName",
              t.vch_bank_id AS "bankId", t.vch_customer_id AS "customerId", t.vch_agent_user_id AS "agentUserId",
              t.vch_account_no AS "accountNo", t.dtt_statement_date AS "statementDate",
              t.dtt_transaction_date AS "transactionDate",
              t.vch_trn_desc_1 AS "description", t.vch_trn_desc_2 AS "descriptionOthers",
              t.vch_target_name AS "targetName",
              t.num_credit_amount AS "creditAmount", t.num_debit_amount AS "debitAmount",
              t.num_statement_balance AS "statementBalance", t.bol_printed_stt AS "printed"
       FROM tm.tm_trn_transaction t
       WHERE t.vch_transaction_id = $1 AND t.bol_rec_actv_stt`,
      [transactionId],
    );
    if (!row) throw new NotFoundException('No data found for this record.');
    return row;
  }

  async update(transactionId: string, input: UpdateTransaction, userId: string): Promise<TransactionDetailDto> {
    await this.get(transactionId);
    await this.assertExists('tm.tm_mst_bank', 'vch_bank_id', input.bankId, 'Invalid Bank selected.');
    await this.assertExists('tm.tm_mst_customer', 'vch_customer_id', input.customerId, 'Invalid Customer selected.');
    await this.assertExists('tm.tm_mst_user', 'vch_user_id', input.agentUserId, 'Invalid Agent selected.');

    await this.db.query(
      `UPDATE tm.tm_trn_transaction SET
         vch_file_name = $1, vch_bank_id = $2, vch_customer_id = $3, vch_agent_user_id = $4,
         vch_account_no = $5, dtt_statement_date = $6, dtt_transaction_date = $7,
         vch_trn_desc_1 = $8, vch_trn_desc_2 = $9, vch_target_name = $10,
         num_credit_amount = $11, num_debit_amount = $12, num_statement_balance = $13,
         bol_printed_stt = $14, vch_modified_by = $15
       WHERE vch_transaction_id = $16`,
      [
        input.fileName,
        input.bankId,
        input.customerId,
        input.agentUserId,
        input.accountNo,
        input.statementDate,
        input.transactionDate,
        input.description,
        input.descriptionOthers,
        input.targetName,
        input.creditAmount,
        input.debitAmount,
        input.statementBalance,
        input.printed,
        userId,
        transactionId,
      ],
    );
    await this.audit.log(userId, 'UPDATE', 'TM_TRN_TRANSACTION', transactionId, input);
    return this.get(transactionId);
  }

  // ---- Pickers ----

  async fileNames(): Promise<string[]> {
    const rows = await this.db.query<{ name: string }>(
      `SELECT DISTINCT vch_file_name AS "name" FROM tm.tm_trn_transaction
       WHERE bol_rec_actv_stt AND vch_file_name IS NOT NULL AND vch_file_name <> '' ORDER BY 1`,
    );
    return rows.map((r) => r.name);
  }

  bankOptions(): Promise<Array<OptionDto & { registrationNo: string | null; address: string | null; displayName: string | null }>> {
    return this.db.query(
      `SELECT vch_bank_id AS "value", vch_bank_name AS "label", vch_bank_display_name AS "displayName",
              vch_bank_reg_no AS "registrationNo", vch_bank_address AS "address"
       FROM tm.tm_mst_bank WHERE bol_rec_actv_stt ORDER BY vch_bank_name`,
    );
  }

  customerOptions(): Promise<Array<OptionDto & { name: string; address: string | null }>> {
    return this.db.query(
      `SELECT vch_customer_id AS "value", vch_customer_code AS "label", vch_customer_name AS "name", vch_address AS "address"
       FROM tm.tm_mst_customer WHERE bol_rec_actv_stt ORDER BY vch_customer_code`,
    );
  }

  // ---- Helpers ----

  private async assertFileNotUploaded(on: Queryable, fileName: string): Promise<void> {
    const rows = await on.query(
      'SELECT 1 FROM tm.tm_trn_transaction WHERE vch_file_name = $1 AND bol_rec_actv_stt LIMIT 1',
      [fileName],
    );
    if (rows.length > 0) {
      throw new ConflictException({
        statusCode: 409,
        message: 'The uploaded bank statement already exists in the system. Please upload another PDF.',
        code: 'DUPLICATE_FILE',
      });
    }
  }

  private async assertExists(table: string, column: string, id: string, message: string): Promise<void> {
    const rows = await this.db.query(`SELECT 1 FROM ${table} WHERE ${column} = $1 AND bol_rec_actv_stt`, [id]);
    if (rows.length === 0) throw new BadRequestException(message);
  }

  private async getOrCreateBank(tx: Queryable, bank: SaveBatch['bank'], userId: string): Promise<string> {
    const existing = await tx.query<{ id: string }>(
      'SELECT vch_bank_id AS "id" FROM tm.tm_mst_bank WHERE vch_bank_name = $1 AND bol_rec_actv_stt',
      [bank.name],
    );
    if (existing.length > 0) return existing[0].id;
    const [row] = await tx.query<{ id: string }>(
      `INSERT INTO tm.tm_mst_bank (vch_bank_name, vch_bank_display_name, vch_bank_reg_no, vch_bank_address, vch_created_by)
       VALUES ($1, $2, $3, $4, $5) RETURNING vch_bank_id AS "id"`,
      [bank.name, bank.name.slice(0, 50), bank.registrationNo, bank.address, userId],
    );
    return row.id;
  }

  private async getOrCreateCustomer(tx: Queryable, customer: SaveBatch['customer'], userId: string): Promise<string> {
    const existing = await tx.query<{ id: string; name: string }>(
      `SELECT vch_customer_id AS "id", vch_customer_name AS "name" FROM tm.tm_mst_customer
       WHERE upper(vch_customer_code) = upper($1) AND bol_rec_actv_stt`,
      [customer.code],
    );
    if (existing.length > 0) {
      if (existing[0].name !== customer.name) {
        throw new ConflictException({
          statusCode: 409,
          message: `The customer code '${customer.code}' already exists for another customer name. Please enter a new unique customer code.`,
          code: 'CUSTOMER_CODE_TAKEN',
        });
      }
      return existing[0].id;
    }
    const [row] = await tx.query<{ id: string }>(
      `INSERT INTO tm.tm_mst_customer (vch_customer_code, vch_customer_name, vch_address, vch_created_by)
       VALUES ($1, $2, $3, $4) RETURNING vch_customer_id AS "id"`,
      [customer.code, customer.name, customer.address, userId],
    );
    return row.id;
  }
}
