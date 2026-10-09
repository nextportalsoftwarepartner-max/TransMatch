import { ConflictException, Injectable, NotFoundException } from '@nestjs/common';
import type { CustomerDto } from '@transmatch/shared';
import { AuditService } from '../audit/audit.service.js';
import { Database } from '../database/database.js';
import { auditColumns, contains, Where } from '../database/sql.js';

const SELECT = `
  SELECT c.vch_customer_id AS "customerId", c.vch_customer_code AS "customerCode", c.vch_customer_name AS "customerName",
         c.vch_email AS "email", c.vch_contact_no AS "contactNo", c.vch_address AS "address", c.vch_remark AS "remark",
         ${auditColumns('c')}
  FROM tm.tm_mst_customer c`;

interface CustomerData {
  customerCode: string;
  customerName: string;
  email: string | null;
  contactNo: string | null;
  address: string | null;
}

@Injectable()
export class CustomersService {
  constructor(
    private readonly db: Database,
    private readonly audit: AuditService,
  ) {}

  list(filter: { code?: string; name?: string }): Promise<CustomerDto[]> {
    const where = new Where('c.bol_rec_actv_stt');
    if (filter.code) where.add('c.vch_customer_code ILIKE ?', contains(filter.code));
    if (filter.name) where.add('c.vch_customer_name ILIKE ?', contains(filter.name));
    return this.db.query<CustomerDto>(`${SELECT} ${where.sql} ORDER BY c.vch_customer_code`, where.params);
  }

  /** Exact lookup used by the transaction entry screens. */
  findByCode(code: string): Promise<CustomerDto | null> {
    return this.db.queryOne<CustomerDto>(
      `${SELECT} WHERE upper(c.vch_customer_code) = upper($1) AND c.bol_rec_actv_stt`,
      [code.trim()],
    );
  }

  async create(data: CustomerData, userId: string): Promise<CustomerDto> {
    await this.assertCodeFree(data.customerCode, null);
    const [row] = await this.db.query<{ id: string }>(
      `INSERT INTO tm.tm_mst_customer (vch_customer_code, vch_customer_name, vch_email, vch_contact_no, vch_address, vch_created_by)
       VALUES ($1, $2, $3, $4, $5, $6) RETURNING vch_customer_id AS "id"`,
      [data.customerCode, data.customerName, data.email, data.contactNo, data.address, userId],
    );
    await this.audit.log(userId, 'CREATE', 'TM_MST_CUSTOMER', row.id, data);
    return this.get(row.id);
  }

  async update(customerId: string, data: CustomerData, userId: string): Promise<CustomerDto> {
    await this.get(customerId);
    await this.assertCodeFree(data.customerCode, customerId);
    await this.db.query(
      `UPDATE tm.tm_mst_customer SET
         vch_customer_code = $1, vch_customer_name = $2, vch_email = $3, vch_contact_no = $4, vch_address = $5,
         vch_modified_by = $6
       WHERE vch_customer_id = $7`,
      [data.customerCode, data.customerName, data.email, data.contactNo, data.address, userId, customerId],
    );
    await this.audit.log(userId, 'UPDATE', 'TM_MST_CUSTOMER', customerId, data);
    return this.get(customerId);
  }

  async setRemark(customerId: string, remark: string | null, userId: string): Promise<CustomerDto> {
    await this.get(customerId);
    await this.db.query(`UPDATE tm.tm_mst_customer SET vch_remark = $1, vch_modified_by = $2 WHERE vch_customer_id = $3`, [
      remark,
      userId,
      customerId,
    ]);
    await this.audit.log(userId, 'UPDATE', 'TM_MST_CUSTOMER', customerId, { remark });
    return this.get(customerId);
  }

  async remove(customerId: string, userId: string): Promise<void> {
    await this.get(customerId);
    const used = await this.db.query(
      'SELECT 1 FROM tm.tm_trn_transaction WHERE vch_customer_id = $1 AND bol_rec_actv_stt LIMIT 1',
      [customerId],
    );
    if (used.length > 0) throw new ConflictException('This customer has transactions and cannot be deleted.');
    await this.db.query(`UPDATE tm.tm_mst_customer SET bol_rec_actv_stt = FALSE, vch_modified_by = $1 WHERE vch_customer_id = $2`, [
      userId,
      customerId,
    ]);
    await this.audit.log(userId, 'DELETE', 'TM_MST_CUSTOMER', customerId);
  }

  private async get(customerId: string): Promise<CustomerDto> {
    const row = await this.db.queryOne<CustomerDto>(`${SELECT} WHERE c.vch_customer_id = $1 AND c.bol_rec_actv_stt`, [
      customerId,
    ]);
    if (!row) throw new NotFoundException('Customer not found.');
    return row;
  }

  private async assertCodeFree(code: string, exceptId: string | null): Promise<void> {
    const rows = await this.db.query(
      `SELECT 1 FROM tm.tm_mst_customer
       WHERE upper(vch_customer_code) = upper($1) AND bol_rec_actv_stt AND vch_customer_id <> coalesce($2, '')`,
      [code, exceptId],
    );
    if (rows.length > 0) throw new ConflictException('Customer Code already exists.');
  }
}
