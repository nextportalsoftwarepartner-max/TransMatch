import { readdirSync, readFileSync } from 'node:fs';
import { join } from 'node:path';
import { fileURLToPath } from 'node:url';
import type { Database } from './database.js';

// <repo>/database/migrations, four levels up from src/database or dist/database
export const MIGRATIONS_DIR = fileURLToPath(new URL('../../../../database/migrations', import.meta.url));

/**
 * Applies the SQL files in database/migrations that have not run yet, in file
 * name order. Applied files are recorded in tm.tm_his_schema_migration.
 */
export async function runMigrations(db: Database, dir: string = MIGRATIONS_DIR): Promise<string[]> {
  await db.exec(`
    CREATE SCHEMA IF NOT EXISTS tm;
    CREATE TABLE IF NOT EXISTS tm.tm_his_schema_migration (
        vch_migration_name  VARCHAR(255)  NOT NULL PRIMARY KEY,
        dtt_applied_date    TIMESTAMPTZ   NOT NULL DEFAULT now()
    );
  `);

  const done = new Set(
    (await db.query<{ name: string }>('SELECT vch_migration_name AS name FROM tm.tm_his_schema_migration')).map(
      (r) => r.name,
    ),
  );

  const applied: string[] = [];
  for (const file of readdirSync(dir).filter((f) => f.endsWith('.sql')).sort()) {
    if (done.has(file)) continue;
    const sql = readFileSync(join(dir, file), 'utf8');
    const name = file.replaceAll("'", "''");
    // One script, one transaction: a failing migration leaves nothing behind
    await db.exec(
      `BEGIN;\n${sql}\n;INSERT INTO tm.tm_his_schema_migration (vch_migration_name) VALUES ('${name}');\nCOMMIT;`,
    );
    applied.push(file);
  }
  return applied;
}
