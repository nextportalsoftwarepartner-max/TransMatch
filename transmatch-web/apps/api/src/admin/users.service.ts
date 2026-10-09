import { BadRequestException, ConflictException, ForbiddenException, Injectable, NotFoundException } from '@nestjs/common';
import type { OptionDto, UserDto } from '@transmatch/shared';
import { AuditService } from '../audit/audit.service.js';
import { AuthService } from '../auth/auth.service.js';
import { Database, type Queryable } from '../database/database.js';
import { auditColumns, contains, Where } from '../database/sql.js';

// A user holds one role on this screen; the role decides the group.
const SELECT = `
  SELECT u.vch_user_id AS "userId", u.vch_login_id AS "loginId", u.vch_user_name AS "userName",
         u.vch_email AS "email", u.vch_contact_no AS "contactNo",
         u.vch_address_1 AS "address1", u.vch_address_2 AS "address2",
         u.vch_address_3 AS "address3", u.vch_address_4 AS "address4",
         u.vch_supervisor_user_id AS "supervisorUserId", sup.vch_user_name AS "supervisorName",
         g.vch_group_id AS "groupId", g.vch_group_name AS "groupName",
         r.vch_role_id AS "roleId", r.vch_role_name AS "roleName",
         u.bol_no_delete_ind AS "noDelete", ${auditColumns('u')}
  FROM tm.tm_mst_user u
  LEFT JOIN tm.tm_mst_user sup ON sup.vch_user_id = u.vch_supervisor_user_id
  LEFT JOIN tm.tm_mst_user_role ur ON ur.vch_user_id = u.vch_user_id AND ur.bol_rec_actv_stt
  LEFT JOIN tm.tm_mst_role r ON r.vch_role_id = ur.vch_role_id
  LEFT JOIN tm.tm_mst_group g ON g.vch_group_id = r.vch_group_id`;

interface UserData {
  roleId: string;
  loginId: string;
  userName: string;
  supervisorUserId: string | null;
  email: string | null;
  contactNo: string | null;
  address1: string | null;
  address2: string | null;
  address3: string | null;
  address4: string | null;
}

@Injectable()
export class UsersService {
  constructor(
    private readonly db: Database,
    private readonly audit: AuditService,
    private readonly auth: AuthService,
  ) {}

  list(filter: { groupId?: string; roleId?: string; name?: string }): Promise<UserDto[]> {
    const where = new Where('u.bol_rec_actv_stt');
    if (filter.groupId) where.add('g.vch_group_id = ?', filter.groupId);
    if (filter.roleId) where.add('r.vch_role_id = ?', filter.roleId);
    if (filter.name) where.add('u.vch_user_name ILIKE ?', contains(filter.name));
    return this.db.query<UserDto>(`${SELECT} ${where.sql} ORDER BY u.vch_user_name, u.vch_user_id`, where.params);
  }

  /** Active users as value/label pairs, for agent and supervisor pickers. */
  options(): Promise<OptionDto[]> {
    return this.db.query<OptionDto>(
      `SELECT vch_user_id AS "value", vch_user_name AS "label"
       FROM tm.tm_mst_user WHERE bol_rec_actv_stt ORDER BY vch_user_name`,
    );
  }

  async create(data: UserData & { password: string }, actorId: string): Promise<UserDto> {
    await this.assertValid(data, null);
    const passwordHash = await this.auth.hashPassword(data.password);
    const userId = await this.db.transaction(async (tx) => {
      const [row] = await tx.query<{ id: string }>(
        `INSERT INTO tm.tm_mst_user (
           vch_login_id, vch_user_name, vch_password_hash, vch_email, vch_contact_no,
           vch_address_1, vch_address_2, vch_address_3, vch_address_4, vch_supervisor_user_id, vch_created_by
         ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11)
         RETURNING vch_user_id AS "id"`,
        [
          data.loginId,
          data.userName,
          passwordHash,
          data.email,
          data.contactNo,
          data.address1,
          data.address2,
          data.address3,
          data.address4,
          data.supervisorUserId,
          actorId,
        ],
      );
      await this.assignRole(tx, row.id, data.roleId, actorId);
      await this.audit.log(actorId, 'CREATE', 'TM_MST_USER', row.id, { loginId: data.loginId, roleId: data.roleId }, tx);
      return row.id;
    });
    return this.get(userId);
  }

  async update(userId: string, data: UserData, actorId: string): Promise<UserDto> {
    await this.get(userId);
    if (data.supervisorUserId === userId) throw new BadRequestException('A user cannot be their own supervisor.');
    await this.assertValid(data, userId);
    await this.db.transaction(async (tx) => {
      await tx.query(
        `UPDATE tm.tm_mst_user SET
           vch_login_id = $1, vch_user_name = $2, vch_email = $3, vch_contact_no = $4,
           vch_address_1 = $5, vch_address_2 = $6, vch_address_3 = $7, vch_address_4 = $8,
           vch_supervisor_user_id = $9, vch_modified_by = $10
         WHERE vch_user_id = $11`,
        [
          data.loginId,
          data.userName,
          data.email,
          data.contactNo,
          data.address1,
          data.address2,
          data.address3,
          data.address4,
          data.supervisorUserId,
          actorId,
          userId,
        ],
      );
      await this.assignRole(tx, userId, data.roleId, actorId);
      await this.audit.log(actorId, 'UPDATE', 'TM_MST_USER', userId, { loginId: data.loginId, roleId: data.roleId }, tx);
    });
    return this.get(userId);
  }

  async remove(userId: string, actorId: string): Promise<void> {
    const user = await this.get(userId);
    if (userId === actorId) throw new ForbiddenException('You cannot delete your own login account.');
    if (user.noDelete) throw new ForbiddenException('This user is protected and cannot be deleted.');
    await this.db.transaction(async (tx) => {
      await tx.query(
        `UPDATE tm.tm_mst_user_role SET bol_rec_actv_stt = FALSE, vch_modified_by = $1 WHERE vch_user_id = $2 AND bol_rec_actv_stt`,
        [actorId, userId],
      );
      await tx.query(`UPDATE tm.tm_mst_user SET bol_rec_actv_stt = FALSE, vch_modified_by = $1 WHERE vch_user_id = $2`, [
        actorId,
        userId,
      ]);
      await this.audit.log(actorId, 'DELETE', 'TM_MST_USER', userId, undefined, tx);
    });
  }

  async resetPassword(userId: string, newPassword: string, actorId: string): Promise<void> {
    await this.get(userId);
    await this.db.query(`UPDATE tm.tm_mst_user SET vch_password_hash = $1, vch_modified_by = $2 WHERE vch_user_id = $3`, [
      await this.auth.hashPassword(newPassword),
      actorId,
      userId,
    ]);
    await this.audit.log(actorId, 'RESET_PASSWORD', 'TM_MST_USER', userId);
  }

  private async get(userId: string): Promise<UserDto> {
    const row = await this.db.queryOne<UserDto>(`${SELECT} WHERE u.vch_user_id = $1 AND u.bol_rec_actv_stt`, [userId]);
    if (!row) throw new NotFoundException('User not found.');
    return row;
  }

  private async assignRole(tx: Queryable, userId: string, roleId: string, actorId: string): Promise<void> {
    const current = await tx.query<{ roleId: string }>(
      'SELECT vch_role_id AS "roleId" FROM tm.tm_mst_user_role WHERE vch_user_id = $1 AND bol_rec_actv_stt',
      [userId],
    );
    if (current.length === 1 && current[0].roleId === roleId) return;
    await tx.query(
      `UPDATE tm.tm_mst_user_role SET bol_rec_actv_stt = FALSE, vch_modified_by = $1 WHERE vch_user_id = $2 AND bol_rec_actv_stt`,
      [actorId, userId],
    );
    await tx.query(`INSERT INTO tm.tm_mst_user_role (vch_user_id, vch_role_id, vch_created_by) VALUES ($1, $2, $3)`, [
      userId,
      roleId,
      actorId,
    ]);
  }

  private async assertValid(data: UserData, exceptId: string | null): Promise<void> {
    const role = await this.db.query('SELECT 1 FROM tm.tm_mst_role WHERE vch_role_id = $1 AND bol_rec_actv_stt', [data.roleId]);
    if (role.length === 0) throw new BadRequestException('Invalid role selection.');

    if (data.supervisorUserId) {
      const supervisor = await this.db.query('SELECT 1 FROM tm.tm_mst_user WHERE vch_user_id = $1 AND bol_rec_actv_stt', [
        data.supervisorUserId,
      ]);
      if (supervisor.length === 0) throw new BadRequestException('Invalid supervisor selection.');
    }

    const duplicate = await this.db.query(
      `SELECT 1 FROM tm.tm_mst_user
       WHERE lower(vch_login_id) = lower($1) AND bol_rec_actv_stt AND vch_user_id <> coalesce($2, '')`,
      [data.loginId, exceptId],
    );
    if (duplicate.length > 0) throw new ConflictException('Login ID already exists.');
  }
}
