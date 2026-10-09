import { PGlite } from '@electric-sql/pglite';
import { Database, PG_TYPE, parseTimestamp, type Queryable, type SqlParam } from './database.js';

const parsers = {
  [PG_TYPE.DATE]: (v: string) => v,
  [PG_TYPE.INT8]: Number,
  [PG_TYPE.NUMERIC]: Number,
  [PG_TYPE.TIMESTAMPTZ]: parseTimestamp,
};

/**
 * PostgreSQL running inside the Node process (WASM). Needs no server, so it is
 * used for local development and tests. Pass no directory for an in-memory
 * database.
 */
export class PgliteDatabase extends Database {
  private readonly db: PGlite;

  constructor(dataDir?: string) {
    super();
    this.db = dataDir ? new PGlite(dataDir, { parsers }) : new PGlite({ parsers });
  }

  async query<T>(sql: string, params: SqlParam[] = []): Promise<T[]> {
    return (await this.db.query<T>(sql, params)).rows;
  }

  transaction<T>(work: (tx: Queryable) => Promise<T>): Promise<T> {
    return this.db.transaction((tx) =>
      work({
        query: async <R>(sql: string, params: SqlParam[] = []) => (await tx.query<R>(sql, params)).rows,
      }),
    ) as Promise<T>;
  }

  async exec(sql: string): Promise<void> {
    try {
      await this.db.exec(sql);
    } catch (err) {
      // A script may fail inside its own BEGIN; leave no failed transaction open
      await this.db.exec('ROLLBACK').catch(() => undefined);
      throw err;
    }
  }

  async close(): Promise<void> {
    await this.db.close();
  }
}
