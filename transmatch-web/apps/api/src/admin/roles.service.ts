import { BadRequestException, ConflictException, ForbiddenException, Injectable, NotFoundException } from '@nestjs/common';
import type { PermissionDto, RoleDto, RolePermissionDto, RolePermissionsInput } from '@transmatch/shared';
import { NO_RIGHTS } from '@transmatch/shared';
import { AuditService } from '../audit/audit.service.js';
import { Database } from '../database/database.js';
import { auditColumns, contains, Where } from '../database/sql.js';

const SELECT = `
  SELECT r.vch_role_id AS "roleId", r.vch_group_id AS "groupId", g.vch_group_name AS "groupName",
         r.vch_role_name AS "roleName", r.vch_role_desc AS "roleDesc",
         r.chr_role_status AS "status", r.bol_no_delete_ind AS "noDelete", ${auditColumns('r')}
  FROM tm.tm_mst_role r
  JOIN tm.tm_mst_group g ON g.vch_group_id = r.vch_group_id`;

interface RoleData {
  groupId: string;
  roleName: string;
  roleDesc: string | null;
}

@Injectable()
export class RolesService {
  constructor(
    private readonly db: Database,
    private readonly audit: AuditService,
  ) {}

  list(filter: { name?: string; groupId?: string }): Promise<RoleDto[]> {
    const where = new Where('r.bol_rec_actv_stt');
    if (filter.name) where.add('r.vch_role_name ILIKE ?', contains(filter.name));
    if (filter.groupId) where.add('r.vch_group_id = ?', filter.groupId);
    return this.db.query<RoleDto>(`${SELECT} ${where.sql} ORDER BY r.vch_role_name`, where.params);
  }

  async create(data: RoleData, userId: string): Promise<RoleDto> {
    await this.assertValid(data, null);
    const [row] = await this.db.query<{ id: string }>(
      `INSERT INTO tm.tm_mst_role (vch_group_id, vch_role_name, vch_role_desc, vch_created_by)
       VALUES ($1, $2, $3, $4) RETURNING vch_role_id AS "id"`,
      [data.groupId, data.roleName, data.roleDesc, userId],
    );
    await this.audit.log(userId, 'CREATE', 'TM_MST_ROLE', row.id, data);
    return this.get(row.id);
  }

  async update(roleId: string, data: RoleData, userId: string): Promise<RoleDto> {
    await this.get(roleId);
    await this.assertValid(data, roleId);
    await this.db.query(
      `UPDATE tm.tm_mst_role SET vch_group_id = $1, vch_role_name = $2, vch_role_desc = $3, vch_modified_by = $4
       WHERE vch_role_id = $5`,
      [data.groupId, data.roleName, data.roleDesc, userId, roleId],
    );
    await this.audit.log(userId, 'UPDATE', 'TM_MST_ROLE', roleId, data);
    return this.get(roleId);
  }

  async setStatus(roleId: string, status: 'A' | 'I', userId: string): Promise<RoleDto> {
    const role = await this.get(roleId);
    if (role.noDelete && status === 'I') throw new ForbiddenException('This role is protected and cannot be deactivated.');
    await this.db.query(`UPDATE tm.tm_mst_role SET chr_role_status = $1, vch_modified_by = $2 WHERE vch_role_id = $3`, [
      status,
      userId,
      roleId,
    ]);
    await this.audit.log(userId, 'UPDATE', 'TM_MST_ROLE', roleId, { status });
    return this.get(roleId);
  }

  async remove(roleId: string, userId: string): Promise<void> {
    const role = await this.get(roleId);
    if (role.noDelete) throw new ForbiddenException('This role is protected and cannot be deleted.');
    const assigned = await this.db.query(
      'SELECT 1 FROM tm.tm_mst_user_role WHERE vch_role_id = $1 AND bol_rec_actv_stt LIMIT 1',
      [roleId],
    );
    if (assigned.length > 0) throw new ConflictException('This role is still assigned to users.');
    await this.db.transaction(async (tx) => {
      await tx.query(
        `UPDATE tm.tm_mst_role_permission SET bol_rec_actv_stt = FALSE, vch_modified_by = $1
         WHERE vch_role_id = $2 AND bol_rec_actv_stt`,
        [userId, roleId],
      );
      await tx.query(`UPDATE tm.tm_mst_role SET bol_rec_actv_stt = FALSE, vch_modified_by = $1 WHERE vch_role_id = $2`, [
        userId,
        roleId,
      ]);
      await this.audit.log(userId, 'DELETE', 'TM_MST_ROLE', roleId, undefined, tx);
    });
  }

  // ---- Permissions ("User Rights") ----

  listPermissions(): Promise<PermissionDto[]> {
    return this.db.query<PermissionDto>(
      `SELECT p.vch_permission_id AS "permissionId", p.vch_permission_code AS "code", p.vch_permission_name AS "name",
              p.vch_permission_desc AS "description", p.vch_parent_permission_id AS "parentPermissionId",
              p.bol_main_menu_ind AS "mainMenu", p.num_display_order AS "displayOrder"
       FROM tm.tm_mst_permission p
       LEFT JOIN tm.tm_mst_permission parent ON parent.vch_permission_id = p.vch_parent_permission_id
       WHERE p.bol_rec_actv_stt
       ORDER BY coalesce(parent.num_display_order, p.num_display_order), p.bol_main_menu_ind DESC, p.num_display_order`,
    );
  }

  async getRolePermissions(roleId: string): Promise<RolePermissionDto[]> {
    await this.get(roleId);
    return this.db.query<RolePermissionDto>(
      `SELECT vch_permission_id AS "permissionId", chr_access_rights AS "rights"
       FROM tm.tm_mst_role_permission WHERE vch_role_id = $1 AND bol_rec_actv_stt`,
      [roleId],
    );
  }

  /** Replaces the rights a role holds. An entry with no right set removes the permission. */
  async setRolePermissions(roleId: string, input: RolePermissionsInput, userId: string): Promise<RolePermissionDto[]> {
    const role = await this.get(roleId);
    if (role.noDelete) throw new ForbiddenException('The rights of this protected role cannot be changed.');

    const known = new Set((await this.listPermissions()).map((p) => p.permissionId));
    if (input.items.some((item) => !known.has(item.permissionId))) {
      throw new BadRequestException('Unknown permission.');
    }
    const wanted = new Map(
      input.items.filter((item) => item.rights !== NO_RIGHTS).map((item) => [item.permissionId, item.rights]),
    );

    await this.db.transaction(async (tx) => {
      const current = await tx.query<{ id: string; permissionId: string; rights: string }>(
        `SELECT vch_role_permission_id AS "id", vch_permission_id AS "permissionId", chr_access_rights AS "rights"
         FROM tm.tm_mst_role_permission WHERE vch_role_id = $1 AND bol_rec_actv_stt`,
        [roleId],
      );
      for (const row of current) {
        const rights = wanted.get(row.permissionId);
        if (rights === undefined) {
          await tx.query(
            `UPDATE tm.tm_mst_role_permission SET bol_rec_actv_stt = FALSE, vch_modified_by = $1 WHERE vch_role_permission_id = $2`,
            [userId, row.id],
          );
        } else if (rights !== row.rights) {
          await tx.query(
            `UPDATE tm.tm_mst_role_permission SET chr_access_rights = $1, vch_modified_by = $2 WHERE vch_role_permission_id = $3`,
            [rights, userId, row.id],
          );
        }
        wanted.delete(row.permissionId);
      }
      for (const [permissionId, rights] of wanted) {
        await tx.query(
          `INSERT INTO tm.tm_mst_role_permission (vch_role_id, vch_permission_id, chr_access_rights, vch_created_by)
           VALUES ($1, $2, $3, $4)`,
          [roleId, permissionId, rights, userId],
        );
      }
      await this.audit.log(userId, 'UPDATE', 'TM_MST_ROLE_PERMISSION', roleId, input.items, tx);
    });
    return this.getRolePermissions(roleId);
  }

  private async get(roleId: string): Promise<RoleDto> {
    const row = await this.db.queryOne<RoleDto>(`${SELECT} WHERE r.vch_role_id = $1 AND r.bol_rec_actv_stt`, [roleId]);
    if (!row) throw new NotFoundException('User role not found.');
    return row;
  }

  private async assertValid(data: RoleData, exceptId: string | null): Promise<void> {
    const group = await this.db.query('SELECT 1 FROM tm.tm_mst_group WHERE vch_group_id = $1 AND bol_rec_actv_stt', [
      data.groupId,
    ]);
    if (group.length === 0) throw new BadRequestException('Selected group is not recognized.');

    const duplicate = await this.db.query(
      `SELECT 1 FROM tm.tm_mst_role
       WHERE vch_group_id = $1 AND upper(vch_role_name) = upper($2) AND bol_rec_actv_stt AND vch_role_id <> coalesce($3, '')`,
      [data.groupId, data.roleName, exceptId],
    );
    if (duplicate.length > 0) throw new ConflictException('This role already exists under the selected group.');
  }
}
