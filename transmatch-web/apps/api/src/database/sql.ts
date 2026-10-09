import type { SqlParam } from './database.js';

/** Standard audit columns of table alias `t`, with user ids resolved to names. */
export const auditColumns = (t: string) => `
    ${t}.dtt_created_date AS "createdAt",
    (SELECT u.vch_user_name FROM tm.tm_mst_user u WHERE u.vch_user_id = ${t}.vch_created_by) AS "createdBy",
    ${t}.dtt_modified_date AS "modifiedAt",
    (SELECT u.vch_user_name FROM tm.tm_mst_user u WHERE u.vch_user_id = ${t}.vch_modified_by) AS "modifiedBy"`;

/** Collects WHERE conditions and their positional parameters. */
export class Where {
  readonly params: SqlParam[] = [];
  private readonly conditions: string[] = [];

  constructor(...fixed: string[]) {
    this.conditions.push(...fixed);
  }

  /** Adds a condition; each `?` in it is bound to the next value. */
  add(condition: string, ...values: SqlParam[]): this {
    let i = 0;
    this.conditions.push(
      condition.replace(/\?/g, () => {
        this.params.push(values[i++]);
        return `$${this.params.length}`;
      }),
    );
    return this;
  }

  get sql(): string {
    return this.conditions.length > 0 ? `WHERE ${this.conditions.join(' AND ')}` : '';
  }
}

/** Escapes LIKE wildcards in user input and wraps it for a "contains" search. */
export const contains = (value: string) => `%${value.replace(/[\\%_]/g, '\\$&')}%`;
