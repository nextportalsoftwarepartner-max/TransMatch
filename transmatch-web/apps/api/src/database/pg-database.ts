import pg from 'pg';
import { Database, PG_TYPE, parseTimestamp, type Queryable, type SqlParam } from './database.js';

export interface PgDatabaseOptions {
  url: string;
  ssl: boolean;
  poolMax: number;
}

const types = new pg.TypeOverrides();
types.setTypeParser(PG_TYPE.DATE, (v) => v);
types.setTypeParser(PG_TYPE.INT8, Number);
types.setTypeParser(PG_TYPE.NUMERIC, Number);
types.setTypeParser(PG_TYPE.TIMESTAMPTZ, parseTimestamp);

export class PgDatabase extends Database {
  private readonly pool: pg.Pool;

  constructor(options: PgDatabaseOptions) {
    super();
    this.pool = new pg.Pool({
      connectionString: options.url,
      max: options.poolMax,
      ssl: options.ssl ? { rejectUnauthorized: false } : undefined,
      types,
    });
  }

  async query<T>(sql: string, params: SqlParam[] = []): Promise<T[]> {
    return (await this.pool.query(sql, params)).rows as T[];
  }

  async transaction<T>(work: (tx: Queryable) => Promise<T>): Promise<T> {
    const client = await this.pool.connect();
    try {
      await client.query('BEGIN');
      const result = await work({
        query: async <R>(sql: string, params: SqlParam[] = []) => (await client.query(sql, params)).rows as R[],
      });
      await client.query('COMMIT');
      return result;
    } catch (err) {
      await client.query('ROLLBACK').catch(() => undefined);
      throw err;
    } finally {
      client.release();
    }
  }

  async exec(sql: string): Promise<void> {
    const client = await this.pool.connect();
    try {
      await client.query(sql);
    } catch (err) {
      // A script may fail inside its own BEGIN; do not hand back a connection stuck in a failed transaction
      await client.query('ROLLBACK').catch(() => undefined);
      throw err;
    } finally {
      client.release();
    }
  }

  async close(): Promise<void> {
    await this.pool.end();
  }
}
