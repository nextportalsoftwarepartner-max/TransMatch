import { ConflictException, ForbiddenException, Injectable, NotFoundException } from '@nestjs/common';
import type { GroupDto } from '@transmatch/shared';
import { AuditService } from '../audit/audit.service.js';
import { Database } from '../database/database.js';
import { auditColumns, contains, Where } from '../database/sql.js';

const SELECT = `
  SELECT g.vch_group_id AS "groupId", g.vch_group_name AS "groupName", g.vch_group_desc AS "groupDesc",
         g.chr_group_status AS "status", g.bol_no_delete_ind AS "noDelete", ${auditColumns('g')}
  FROM tm.tm_mst_group g`;

interface GroupData {
  groupName: string;
  groupDesc: string | null;
}

@Injectable()
export class GroupsService {
  constructor(
    private readonly db: Database,
    private readonly audit: AuditService,
  ) {}

  list(name?: string): Promise<GroupDto[]> {
    const where = new Where('g.bol_rec_actv_stt');
    if (name) where.add('g.vch_group_name ILIKE ?', contains(name));
    return this.db.query<GroupDto>(`${SELECT} ${where.sql} ORDER BY g.vch_group_name`, where.params);
  }

  async create(data: GroupData, userId: string): Promise<GroupDto> {
    await this.assertNameFree(data.groupName, null);
    const [row] = await this.db.query<{ id: string }>(
      `INSERT INTO tm.tm_mst_group (vch_group_name, vch_group_desc, vch_created_by)
       VALUES ($1, $2, $3) RETURNING vch_group_id AS "id"`,
      [data.groupName, data.groupDesc, userId],
    );
    await this.audit.log(userId, 'CREATE', 'TM_MST_GROUP', row.id, data);
    return this.get(row.id);
  }

  async update(groupId: string, data: GroupData, userId: string): Promise<GroupDto> {
    await this.get(groupId);
    await this.assertNameFree(data.groupName, groupId);
    await this.db.query(
      `UPDATE tm.tm_mst_group SET vch_group_name = $1, vch_group_desc = $2, vch_modified_by = $3 WHERE vch_group_id = $4`,
      [data.groupName, data.groupDesc, userId, groupId],
    );
    await this.audit.log(userId, 'UPDATE', 'TM_MST_GROUP', groupId, data);
    return this.get(groupId);
  }

  async setStatus(groupId: string, status: 'A' | 'I', userId: string): Promise<GroupDto> {
    const group = await this.get(groupId);
    if (group.noDelete && status === 'I') throw new ForbiddenException('This group is protected and cannot be deactivated.');
    await this.db.query(`UPDATE tm.tm_mst_group SET chr_group_status = $1, vch_modified_by = $2 WHERE vch_group_id = $3`, [
      status,
      userId,
      groupId,
    ]);
    await this.audit.log(userId, 'UPDATE', 'TM_MST_GROUP', groupId, { status });
    return this.get(groupId);
  }

  async remove(groupId: string, userId: string): Promise<void> {
    const group = await this.get(groupId);
    if (group.noDelete) throw new ForbiddenException('This group is protected and cannot be deleted.');
    const roles = await this.db.query(
      'SELECT 1 FROM tm.tm_mst_role WHERE vch_group_id = $1 AND bol_rec_actv_stt LIMIT 1',
      [groupId],
    );
    if (roles.length > 0) throw new ConflictException('This group still has roles. Delete its roles first.');
    await this.db.query(`UPDATE tm.tm_mst_group SET bol_rec_actv_stt = FALSE, vch_modified_by = $1 WHERE vch_group_id = $2`, [
      userId,
      groupId,
    ]);
    await this.audit.log(userId, 'DELETE', 'TM_MST_GROUP', groupId);
  }

  private async get(groupId: string): Promise<GroupDto> {
    const row = await this.db.queryOne<GroupDto>(`${SELECT} WHERE g.vch_group_id = $1 AND g.bol_rec_actv_stt`, [groupId]);
    if (!row) throw new NotFoundException('User group not found.');
    return row;
  }

  private async assertNameFree(name: string, exceptId: string | null): Promise<void> {
    const rows = await this.db.query(
      `SELECT 1 FROM tm.tm_mst_group
       WHERE upper(vch_group_name) = upper($1) AND bol_rec_actv_stt AND vch_group_id <> coalesce($2, '')`,
      [name, exceptId],
    );
    if (rows.length > 0) throw new ConflictException('Group Name already exists.');
  }
}
