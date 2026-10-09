export type SqlParam = string | number | boolean | null | string[] | Date;

/** Anything a query can be run on: the database itself or an open transaction. */
export interface Queryable {
  query<T = Record<string, unknown>>(sql: string, params?: SqlParam[]): Promise<T[]>;
}

/**
 * Database access used by the whole API. Two implementations exist: a
 * PostgreSQL connection pool and an embedded PGlite instance for development
 * and tests. Both return DATE columns as "YYYY-MM-DD" strings, NUMERIC and
 * BIGINT as numbers and TIMESTAMPTZ as ISO-8601 strings.
 */
export abstract class Database implements Queryable {
  abstract query<T = Record<string, unknown>>(sql: string, params?: SqlParam[]): Promise<T[]>;

  /** Runs `work` in a transaction; commits when it resolves, rolls back when it throws. */
  abstract transaction<T>(work: (tx: Queryable) => Promise<T>): Promise<T>;

  /** Runs a script of several statements (no parameters). */
  abstract exec(sql: string): Promise<void>;

  abstract close(): Promise<void>;

  async queryOne<T = Record<string, unknown>>(sql: string, params?: SqlParam[]): Promise<T | null> {
    const rows = await this.query<T>(sql, params);
    return rows[0] ?? null;
  }
}

// PostgreSQL type OIDs whose default driver representation is replaced
export const PG_TYPE = { INT8: 20, DATE: 1082, TIMESTAMPTZ: 1184, NUMERIC: 1700 } as const;

export const parseTimestamp = (value: string) => new Date(value).toISOString();
