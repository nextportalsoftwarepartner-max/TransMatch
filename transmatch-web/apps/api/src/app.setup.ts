import type { INestApplication } from '@nestjs/common';
import cookieParser from 'cookie-parser';
import { AllExceptionsFilter } from './common/all-exceptions.filter.js';

/** HTTP setup shared by the server and the end-to-end tests. */
export function setupApp(app: INestApplication): void {
  app.setGlobalPrefix('api');
  app.use(cookieParser());
  app.useGlobalFilters(new AllExceptionsFilter());
  app.enableShutdownHooks();
}
