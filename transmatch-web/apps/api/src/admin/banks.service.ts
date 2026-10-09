import { ConflictException, Injectable, NotFoundException } from '@nestjs/common';
import type { BankDto } from '@transmatch/shared';
import { AuditService } from '../audit/audit.service.js';
import { Database } from '../database/database.js';
import { auditColumns, contains, Where } from '../database/sql.js';

const SELECT = `
  SELECT b.vch_bank_id AS "bankId", b.vch_bank_name AS "bankName", b.vch_bank_display_name AS "bankDisplayName",
         b.vch_bank_reg_no AS "bankRegNo", b.vch_bank_address AS "bankAddress", ${auditColumns('b')}
  FROM tm.tm_mst_bank b`;

interface BankData {
  bankName: string;
  bankDisplayName: string | null;
  bankRegNo: string | null;
  bankAddress: string | null;
}

@Injectable()
export class BanksService {
  constructor(
    private readonly db: Database,
    private readonly audit: AuditService,
  ) {}

  list(name?: string): Promise<BankDto[]> {
    const where = new Where('b.bol_rec_actv_stt');
    if (name) where.add('b.vch_bank_name ILIKE ?', contains(name));
    return this.db.query<BankDto>(`${SELECT} ${where.sql} ORDER BY b.vch_bank_name`, where.params);
  }

  async create(data: BankData, userId: string): Promise<BankDto> {
    await this.assertNameFree(data.bankName, null);
    const [row] = await this.db.query<{ id: string }>(
      `INSERT INTO tm.tm_mst_bank (vch_bank_name, vch_bank_display_name, vch_bank_reg_no, vch_bank_address, vch_created_by)
       VALUES ($1, $2, $3, $4, $5) RETURNING vch_bank_id AS "id"`,
      // The display name defaults to the bank name
      [data.bankName, data.bankDisplayName ?? data.bankName.slice(0, 50), data.bankRegNo, data.bankAddress, userId],
    );
    await this.audit.log(userId, 'CREATE', 'TM_MST_BANK', row.id, data);
    return this.get(row.id);
  }

  async update(bankId: string, data: BankData, userId: string): Promise<BankDto> {
    await this.get(bankId);
    await this.assertNameFree(data.bankName, bankId);
    await this.db.query(
      `UPDATE tm.tm_mst_bank SET
         vch_bank_name = $1, vch_bank_display_name = $2, vch_bank_reg_no = $3, vch_bank_address = $4, vch_modified_by = $5
       WHERE vch_bank_id = $6`,
      [data.bankName, data.bankDisplayName ?? data.bankName.slice(0, 50), data.bankRegNo, data.bankAddress, userId, bankId],
    );
    await this.audit.log(userId, 'UPDATE', 'TM_MST_BANK', bankId, data);
    return this.get(bankId);
  }

  async remove(bankId: string, userId: string): Promise<void> {
    await this.get(bankId);
    const used = await this.db.query(
      'SELECT 1 FROM tm.tm_trn_transaction WHERE vch_bank_id = $1 AND bol_rec_actv_stt LIMIT 1',
      [bankId],
    );
    if (used.length > 0) throw new ConflictException('This bank has transactions and cannot be deleted.');
    await this.db.query(`UPDATE tm.tm_mst_bank SET bol_rec_actv_stt = FALSE, vch_modified_by = $1 WHERE vch_bank_id = $2`, [
      userId,
      bankId,
    ]);
    await this.audit.log(userId, 'DELETE', 'TM_MST_BANK', bankId);
  }

  private async get(bankId: string): Promise<BankDto> {
    const row = await this.db.queryOne<BankDto>(`${SELECT} WHERE b.vch_bank_id = $1 AND b.bol_rec_actv_stt`, [bankId]);
    if (!row) throw new NotFoundException('Bank not found.');
    return row;
  }

  private async assertNameFree(name: string, exceptId: string | null): Promise<void> {
    const rows = await this.db.query(
      `SELECT 1 FROM tm.tm_mst_bank WHERE vch_bank_name = $1 AND bol_rec_actv_stt AND vch_bank_id <> coalesce($2, '')`,
      [name, exceptId],
    );
    if (rows.length > 0) throw new ConflictException('Bank Name already exists.');
  }
}
