import { Global, Inject, Injectable, Logger, Module, type OnApplicationShutdown, type OnModuleInit } from '@nestjs/common';
import { mkdirSync } from 'node:fs';
import { dirname } from 'node:path';
import { APP_CONFIG, type AppConfig } from '../config/app-config.js';
import { Database } from './database.js';
import { runMigrations } from './migrator.js';
import { PgDatabase } from './pg-database.js';
import { PgliteDatabase } from './pglite-database.js';

export function createDatabase(config: AppConfig): Database {
  if (config.db.driver === 'postgres') {
    return new PgDatabase({ url: config.db.url!, ssl: config.db.ssl, poolMax: config.db.poolMax });
  }
  mkdirSync(dirname(config.db.pgliteDataDir), { recursive: true });
  return new PgliteDatabase(config.db.pgliteDataDir);
}

@Injectable()
class DatabaseLifecycle implements OnModuleInit, OnApplicationShutdown {
  private readonly logger = new Logger('Database');

  constructor(
    private readonly db: Database,
    @Inject(APP_CONFIG) private readonly config: AppConfig,
  ) {}

  async onModuleInit(): Promise<void> {
    if (this.config.db.driver === 'pglite') {
      this.logger.warn(`Using the embedded PGlite database at ${this.config.db.pgliteDataDir} (development only)`);
    }
    if (this.config.db.autoMigrate) {
      const applied = await runMigrations(this.db);
      if (applied.length > 0) this.logger.log(`Applied migrations: ${applied.join(', ')}`);
    }
  }

  async onApplicationShutdown(): Promise<void> {
    await this.db.close();
  }
}

@Global()
@Module({
  providers: [
    { provide: Database, useFactory: createDatabase, inject: [APP_CONFIG] },
    DatabaseLifecycle,
  ],
  exports: [Database],
})
export class DatabaseModule {}
