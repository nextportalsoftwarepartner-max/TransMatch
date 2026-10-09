import { Global, Injectable, Module } from '@nestjs/common';
import { Database, type Queryable } from '../database/database.js';

export type AuditAction = 'CREATE' | 'UPDATE' | 'DELETE' | 'IMPORT' | 'EXPORT' | 'RESET_PASSWORD';

/** Writes TM_HIS_AUDIT_LOG entries for data changes. */
@Injectable()
export class AuditService {
  constructor(private readonly db: Database) {}

  /** Pass the transaction as `on` so the log entry commits or rolls back with the change. */
  async log(
    userId: string,
    action: AuditAction,
    entityName: string,
    entityId: string | null,
    detail?: unknown,
    on: Queryable = this.db,
  ): Promise<void> {
    await on.query(
      `INSERT INTO tm.tm_his_audit_log (vch_user_id, vch_action, vch_entity_name, vch_entity_id, jsn_change_detail)
       VALUES ($1, $2, $3, $4, $5::jsonb)`,
      [userId, action, entityName, entityId, detail === undefined ? null : JSON.stringify(detail)],
    );
  }
}

@Global()
@Module({ providers: [AuditService], exports: [AuditService] })
export class AuditModule {}
