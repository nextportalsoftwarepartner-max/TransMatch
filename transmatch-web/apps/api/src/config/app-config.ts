import { randomBytes } from 'node:crypto';
import { existsSync } from 'node:fs';
import { resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import { z } from 'zod';

const API_ROOT = fileURLToPath(new URL('../../', import.meta.url));

const bool = (fallback: boolean) =>
  z
    .enum(['true', 'false'])
    .optional()
    .transform((v) => (v === undefined ? fallback : v === 'true'));

const envSchema = z.object({
  NODE_ENV: z.enum(['development', 'test', 'production']).default('development'),
  PORT: z.coerce.number().int().positive().default(3201),

  // "postgres" for a real server (Supabase), "pglite" for the embedded database used in development
  DB_DRIVER: z.enum(['postgres', 'pglite']).default('pglite'),
  DATABASE_URL: z.string().optional(),
  DB_SSL: bool(true),
  DB_POOL_MAX: z.coerce.number().int().positive().default(10),
  PGLITE_DATA_DIR: z.string().default('.pgdata'),
  DB_AUTO_MIGRATE: z.enum(['true', 'false']).optional(),

  JWT_SECRET: z.string().min(32).optional(),
  SESSION_HOURS: z.coerce.number().positive().default(8),
  COOKIE_SECURE: z.enum(['true', 'false']).optional(),

  // Embedding model for target-name extraction on UOB statements
  NER_ML_ENABLED: bool(true),
  NER_ML_CACHE_DIR: z.string().default('.model-cache'),

  UPLOAD_MAX_MB: z.coerce.number().positive().default(25),
});

export interface AppConfig {
  env: 'development' | 'test' | 'production';
  port: number;
  db: {
    driver: 'postgres' | 'pglite';
    url?: string;
    ssl: boolean;
    poolMax: number;
    pgliteDataDir: string;
    autoMigrate: boolean;
  };
  auth: { jwtSecret: string; sessionHours: number; cookieSecure: boolean };
  ner: { mlEnabled: boolean; cacheDir: string };
  uploadMaxBytes: number;
}

export const APP_CONFIG = Symbol('APP_CONFIG');

/** Reads apps/api/.env (if present) and validates the environment. */
export function loadConfig(): AppConfig {
  const envFile = resolve(API_ROOT, '.env');
  if (existsSync(envFile)) process.loadEnvFile(envFile);

  const parsed = envSchema.safeParse(process.env);
  if (!parsed.success) {
    const problems = parsed.error.issues.map((i) => `${i.path.join('.')}: ${i.message}`).join('; ');
    throw new Error(`Invalid configuration: ${problems}`);
  }
  const env = parsed.data;
  const production = env.NODE_ENV === 'production';

  if (env.DB_DRIVER === 'postgres' && !env.DATABASE_URL) {
    throw new Error('Invalid configuration: DATABASE_URL is required when DB_DRIVER=postgres');
  }
  if (production && !env.JWT_SECRET) {
    throw new Error('Invalid configuration: JWT_SECRET is required in production');
  }

  return {
    env: env.NODE_ENV,
    port: env.PORT,
    db: {
      driver: env.DB_DRIVER,
      url: env.DATABASE_URL,
      ssl: env.DB_SSL,
      poolMax: env.DB_POOL_MAX,
      pgliteDataDir: resolve(API_ROOT, env.PGLITE_DATA_DIR),
      // The embedded database sets itself up; a real server is migrated deliberately
      autoMigrate: env.DB_AUTO_MIGRATE ? env.DB_AUTO_MIGRATE === 'true' : env.DB_DRIVER === 'pglite',
    },
    auth: {
      // Without a configured secret, sessions only last until the next restart
      jwtSecret: env.JWT_SECRET ?? randomBytes(48).toString('hex'),
      sessionHours: env.SESSION_HOURS,
      cookieSecure: env.COOKIE_SECURE ? env.COOKIE_SECURE === 'true' : production,
    },
    ner: { mlEnabled: env.NER_ML_ENABLED, cacheDir: resolve(API_ROOT, env.NER_ML_CACHE_DIR) },
    uploadMaxBytes: Math.floor(env.UPLOAD_MAX_MB * 1024 * 1024),
  };
}
