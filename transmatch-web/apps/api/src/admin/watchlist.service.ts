import { BadRequestException, ConflictException, Injectable, NotFoundException } from '@nestjs/common';
import type { WatchLists, WatchNameDto } from '@transmatch/shared';
import { normalizeNames } from '@transmatch/shared';
import ExcelJS from 'exceljs';
import { AuditService } from '../audit/audit.service.js';
import { Database } from '../database/database.js';
import { auditColumns, contains, Where } from '../database/sql.js';

export type WatchlistKind = 'blacklisted' | 'suspicious';

// The two name lists share one shape; only the table and column names differ
const TABLES = {
  blacklisted: { table: 'tm.tm_mst_blacklisted', id: 'vch_blacklisted_id', name: 'vch_blacklisted_name', label: 'Blacklisted' },
  suspicious: { table: 'tm.tm_mst_suspicious', id: 'vch_suspicious_id', name: 'vch_suspicious_name', label: 'Suspicious' },
} as const;

const MAX_NAME_LENGTH = 100;

@Injectable()
export class WatchlistService {
  constructor(
    private readonly db: Database,
    private readonly audit: AuditService,
  ) {}

  list(kind: WatchlistKind, filter: { name?: string; existsInBlacklisted?: 'Yes' | 'No' }): Promise<WatchNameDto[]> {
    const t = TABLES[kind];
    const where = new Where('w.bol_rec_actv_stt');
    if (filter.name) where.add(`w.${t.name} ILIKE ?`, contains(filter.name));

    // Suspicious names also show whether the same name is on the blacklist
    const inBlacklist = `EXISTS (
        SELECT 1 FROM tm.tm_mst_blacklisted b
        WHERE b.bol_rec_actv_stt AND trim(lower(b.vch_blacklisted_name)) = trim(lower(w.${t.name})))`;
    if (kind === 'suspicious' && filter.existsInBlacklisted) {
      where.add(filter.existsInBlacklisted === 'Yes' ? inBlacklist : `NOT ${inBlacklist}`);
    }

    return this.db.query<WatchNameDto>(
      `SELECT w.${t.id} AS "id", w.${t.name} AS "name",
              ${kind === 'suspicious' ? `${inBlacklist} AS "existsInBlacklisted",` : ''}
              ${auditColumns('w')}
       FROM ${t.table} w ${where.sql}
       ORDER BY w.dtt_created_date DESC, w.${t.name}`,
      where.params,
    );
  }

  /** Both lists, normalised for matching against transaction descriptions. */
  async loadLists(): Promise<WatchLists> {
    const [blacklisted, suspicious] = await Promise.all([
      this.db.query<{ name: string }>('SELECT vch_blacklisted_name AS "name" FROM tm.tm_mst_blacklisted WHERE bol_rec_actv_stt'),
      this.db.query<{ name: string }>('SELECT vch_suspicious_name AS "name" FROM tm.tm_mst_suspicious WHERE bol_rec_actv_stt'),
    ]);
    return {
      blacklisted: normalizeNames(blacklisted.map((r) => r.name)),
      suspicious: normalizeNames(suspicious.map((r) => r.name)),
    };
  }

  async create(kind: WatchlistKind, name: string, userId: string): Promise<void> {
    const t = TABLES[kind];
    await this.assertNameFree(kind, name, null);
    const [row] = await this.db.query<{ id: string }>(
      `INSERT INTO ${t.table} (${t.name}, vch_created_by) VALUES ($1, $2) RETURNING ${t.id} AS "id"`,
      [name, userId],
    );
    await this.audit.log(userId, 'CREATE', tableName(kind), row.id, { name });
  }

  async update(kind: WatchlistKind, id: string, name: string, userId: string): Promise<void> {
    const t = TABLES[kind];
    await this.assertNameFree(kind, name, id);
    const rows = await this.db.query(
      `UPDATE ${t.table} SET ${t.name} = $1, vch_modified_by = $2 WHERE ${t.id} = $3 AND bol_rec_actv_stt RETURNING 1`,
      [name, userId, id],
    );
    if (rows.length === 0) throw new NotFoundException(`${t.label} name not found.`);
    await this.audit.log(userId, 'UPDATE', tableName(kind), id, { name });
  }

  async removeMany(kind: WatchlistKind, ids: string[], userId: string): Promise<number> {
    const t = TABLES[kind];
    const rows = await this.db.query(
      `UPDATE ${t.table} SET bol_rec_actv_stt = FALSE, vch_modified_by = $1
       WHERE ${t.id} = ANY($2::varchar[]) AND bol_rec_actv_stt RETURNING 1`,
      [userId, ids],
    );
    await this.audit.log(userId, 'DELETE', tableName(kind), null, { ids });
    return rows.length;
  }

  /**
   * Imports names from the first column of the first worksheet, starting at
   * row 2 (row 1 is the heading). Names already on the list are skipped.
   */
  async importExcel(kind: WatchlistKind, file: Buffer, userId: string): Promise<{ inserted: number; skipped: number }> {
    const t = TABLES[kind];
    const workbook = new ExcelJS.Workbook();
    try {
      await workbook.xlsx.load(file as unknown as ArrayBuffer);
    } catch {
      throw new BadRequestException('The file could not be read. Please upload an .xlsx workbook.');
    }
    const sheet = workbook.worksheets[0];
    if (!sheet) throw new BadRequestException('The workbook has no worksheet.');

    const names: string[] = [];
    const seen = new Set<string>();
    sheet.eachRow((row, rowNumber) => {
      if (rowNumber === 1) return;
      const name = row.getCell(1).text.trim();
      if (!name || seen.has(name)) return;
      if (name.length > MAX_NAME_LENGTH) {
        throw new BadRequestException(`Row ${rowNumber}: the name is longer than ${MAX_NAME_LENGTH} characters.`);
      }
      seen.add(name);
      names.push(name);
    });

    const inserted = await this.db.transaction(async (tx) => {
      const existing = new Set(
        (await tx.query<{ name: string }>(`SELECT ${t.name} AS "name" FROM ${t.table} WHERE bol_rec_actv_stt`)).map(
          (r) => r.name,
        ),
      );
      let count = 0;
      for (const name of names) {
        if (existing.has(name)) continue;
        await tx.query(`INSERT INTO ${t.table} (${t.name}, vch_created_by) VALUES ($1, $2)`, [name, userId]);
        count++;
      }
      await this.audit.log(userId, 'IMPORT', tableName(kind), null, { inserted: count }, tx);
      return count;
    });
    return { inserted, skipped: names.length - inserted };
  }

  /** Empty import workbook with the heading row. */
  async template(kind: WatchlistKind): Promise<Buffer> {
    const workbook = new ExcelJS.Workbook();
    const sheet = workbook.addWorksheet(TABLES[kind].label);
    sheet.columns = [{ header: `${TABLES[kind].label} Name`, key: 'name', width: 50 }];
    sheet.getRow(1).font = { bold: true };
    return Buffer.from(await workbook.xlsx.writeBuffer());
  }

  private async assertNameFree(kind: WatchlistKind, name: string, exceptId: string | null): Promise<void> {
    const t = TABLES[kind];
    const rows = await this.db.query(
      `SELECT 1 FROM ${t.table} WHERE ${t.name} = $1 AND bol_rec_actv_stt AND ${t.id} <> coalesce($2, '')`,
      [name, exceptId],
    );
    if (rows.length > 0) throw new ConflictException(`'${name}' is already on the ${t.label.toLowerCase()} list.`);
  }
}

const tableName = (kind: WatchlistKind) => TABLES[kind].table.replace('tm.', '').toUpperCase();
