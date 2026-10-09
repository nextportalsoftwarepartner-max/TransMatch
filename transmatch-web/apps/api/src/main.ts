import 'reflect-metadata';
import { Logger } from '@nestjs/common';
import { NestFactory } from '@nestjs/core';
import type { NestExpressApplication } from '@nestjs/platform-express';
import { AppModule } from './app.module.js';
import { setupApp } from './app.setup.js';
import { APP_CONFIG, type AppConfig } from './config/app-config.js';

async function bootstrap() {
  const app = await NestFactory.create<NestExpressApplication>(AppModule);
  // The web app proxies to the API, so the client address arrives in X-Forwarded-For
  app.set('trust proxy', 'loopback');
  setupApp(app);
  const config = app.get<AppConfig>(APP_CONFIG);
  await app.listen(config.port);
  new Logger('Bootstrap').log(`TransMatch API listening on http://localhost:${config.port}/api`);
}
await bootstrap();
