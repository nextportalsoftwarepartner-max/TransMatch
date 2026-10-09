import {
  BadRequestException,
  HttpException,
  HttpStatus,
  Inject,
  Injectable,
  UnauthorizedException,
} from '@nestjs/common';
import { JwtService } from '@nestjs/jwt';
import { mergeRights, type SessionUser } from '@transmatch/shared';
import bcrypt from 'bcryptjs';
import { APP_CONFIG, type AppConfig } from '../config/app-config.js';
import { Database } from '../database/database.js';

const BCRYPT_ROUNDS = 12;

// Consecutive failed logins allowed before a login id is locked out for a while
const MAX_FAILED_ATTEMPTS = 5;
const LOCKOUT_MS = 15 * 60 * 1000;

interface UserRow {
  userId: string;
  loginId: string;
  userName: string;
  passwordHash: string | null;
  bypass: boolean;
}

export interface LoginContext {
  ip?: string;
  userAgent?: string;
}

@Injectable()
export class AuthService {
  private readonly failures = new Map<string, { count: number; lockedUntil: number }>();

  constructor(
    private readonly db: Database,
    private readonly jwt: JwtService,
    @Inject(APP_CONFIG) private readonly config: AppConfig,
  ) {}

  hashPassword(password: string): Promise<string> {
    return bcrypt.hash(password, BCRYPT_ROUNDS);
  }

  /** Checks the credentials and returns a session token with the user it belongs to. */
  async login(loginId: string, password: string, ctx: LoginContext): Promise<{ token: string; user: SessionUser }> {
    const key = loginId.toLowerCase();
    const failure = this.failures.get(key);
    if (failure && failure.lockedUntil > Date.now()) {
      await this.logLogin(loginId, null, false, 'LOCKED_OUT', ctx);
      throw new HttpException(
        { statusCode: 429, message: 'Too many failed attempts. Please try again in a few minutes.', code: 'LOCKED_OUT' },
        HttpStatus.TOO_MANY_REQUESTS,
      );
    }

    const row = await this.db.queryOne<UserRow>(
      `SELECT vch_user_id AS "userId", vch_login_id AS "loginId", vch_user_name AS "userName",
              vch_password_hash AS "passwordHash", bol_bypass_ind AS "bypass"
       FROM tm.tm_mst_user
       WHERE lower(vch_login_id) = lower($1) AND bol_rec_actv_stt AND chr_user_status = 'A'`,
      [loginId],
    );

    const valid = !!row?.passwordHash && (await bcrypt.compare(password, row.passwordHash));
    if (!row || !valid) {
      const count = (failure?.count ?? 0) + 1;
      this.failures.set(key, { count, lockedUntil: count >= MAX_FAILED_ATTEMPTS ? Date.now() + LOCKOUT_MS : 0 });
      await this.logLogin(loginId, row?.userId ?? null, false, row ? 'WRONG_PASSWORD' : 'UNKNOWN_USER', ctx);
      throw new UnauthorizedException({ statusCode: 401, message: 'Invalid username or password.', code: 'BAD_CREDENTIALS' });
    }

    this.failures.delete(key);
    await this.db.query('UPDATE tm.tm_mst_user SET dtt_last_login_date = now() WHERE vch_user_id = $1', [row.userId]);
    await this.logLogin(loginId, row.userId, true, null, ctx);

    const token = await this.jwt.signAsync({ sub: row.userId });
    return { token, user: await this.buildSessionUser(row) };
  }

  /** Resolves a session token to its user, or null when the token or the user is no longer valid. */
  async resolveSession(token: string): Promise<SessionUser | null> {
    let userId: string;
    try {
      userId = (await this.jwt.verifyAsync<{ sub: string }>(token)).sub;
    } catch {
      return null;
    }
    const row = await this.db.queryOne<UserRow>(
      `SELECT vch_user_id AS "userId", vch_login_id AS "loginId", vch_user_name AS "userName",
              vch_password_hash AS "passwordHash", bol_bypass_ind AS "bypass"
       FROM tm.tm_mst_user
       WHERE vch_user_id = $1 AND bol_rec_actv_stt AND chr_user_status = 'A'`,
      [userId],
    );
    return row ? this.buildSessionUser(row) : null;
  }

  async changePassword(userId: string, currentPassword: string, newPassword: string): Promise<void> {
    const row = await this.db.queryOne<{ hash: string | null }>(
      'SELECT vch_password_hash AS "hash" FROM tm.tm_mst_user WHERE vch_user_id = $1',
      [userId],
    );
    if (!row?.hash || !(await bcrypt.compare(currentPassword, row.hash))) {
      throw new BadRequestException('The current password is not correct.');
    }
    await this.db.query('UPDATE tm.tm_mst_user SET vch_password_hash = $1, vch_modified_by = $2 WHERE vch_user_id = $2', [
      await this.hashPassword(newPassword),
      userId,
    ]);
  }

  get sessionMaxAgeMs(): number {
    return this.config.auth.sessionHours * 60 * 60 * 1000;
  }

  /** Rights come from every active role the user holds, in an active group. */
  private async buildSessionUser(row: UserRow): Promise<SessionUser> {
    const rights = await this.db.query<{ code: string; rights: string }>(
      `SELECT p.vch_permission_code AS "code", rp.chr_access_rights AS "rights"
       FROM tm.tm_mst_user_role ur
       JOIN tm.tm_mst_role r ON r.vch_role_id = ur.vch_role_id AND r.bol_rec_actv_stt AND r.chr_role_status = 'A'
       JOIN tm.tm_mst_group g ON g.vch_group_id = r.vch_group_id AND g.bol_rec_actv_stt AND g.chr_group_status = 'A'
       JOIN tm.tm_mst_role_permission rp ON rp.vch_role_id = r.vch_role_id AND rp.bol_rec_actv_stt
       JOIN tm.tm_mst_permission p ON p.vch_permission_id = rp.vch_permission_id AND p.bol_rec_actv_stt
       WHERE ur.vch_user_id = $1 AND ur.bol_rec_actv_stt`,
      [row.userId],
    );
    const permissions: Record<string, string> = {};
    for (const { code, rights: r } of rights) {
      permissions[code] = permissions[code] ? mergeRights(permissions[code], r) : r;
    }
    return { userId: row.userId, loginId: row.loginId, userName: row.userName, isSuperUser: row.bypass, permissions };
  }

  private async logLogin(
    loginId: string,
    userId: string | null,
    success: boolean,
    reason: string | null,
    ctx: LoginContext,
  ): Promise<void> {
    await this.db.query(
      `INSERT INTO tm.tm_his_login_log (vch_login_id, vch_user_id, bol_success_ind, vch_failure_reason, vch_ip_address, vch_user_agent)
       VALUES ($1, $2, $3, $4, $5, $6)`,
      [loginId.slice(0, 100), userId, success, reason, ctx.ip?.slice(0, 64) ?? null, ctx.userAgent?.slice(0, 255) ?? null],
    );
  }
}
