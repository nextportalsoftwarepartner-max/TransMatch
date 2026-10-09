// Applies pending migrations to the configured database:  pnpm db:migrate
import { loadConfig } from '../config/app-config.js';
import { createDatabase } from './database.module.js';
import { runMigrations } from './migrator.js';

const config = loadConfig();
const db = createDatabase(config);
try {
  const applied = await runMigrations(db);
  console.log(applied.length > 0 ? `Applied: ${applied.join(', ')}` : 'Database is up to date.');
} finally {
  await db.close();
}
