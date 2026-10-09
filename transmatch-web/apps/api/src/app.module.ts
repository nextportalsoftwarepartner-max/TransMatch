import { Module } from '@nestjs/common';
import { AdminModule } from './admin/admin.module.js';
import { AuditModule } from './audit/audit.service.js';
import { AuthModule } from './auth/auth.module.js';
import { ConfigModule } from './config/config.module.js';
import { DatabaseModule } from './database/database.module.js';
import { ReportsModule } from './reports/reports.module.js';
import { TransactionsModule } from './transactions/transactions.module.js';

@Module({
  imports: [ConfigModule, DatabaseModule, AuditModule, AuthModule, AdminModule, TransactionsModule, ReportsModule],
})
export class AppModule {}
