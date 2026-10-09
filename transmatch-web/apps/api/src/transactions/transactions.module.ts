import { Module } from '@nestjs/common';
import { AdminModule } from '../admin/admin.module.js';
import { StatementExtractionService } from './statement-extraction.service.js';
import { TransactionsController } from './transactions.controller.js';
import { TransactionsService } from './transactions.service.js';

@Module({
  imports: [AdminModule],
  controllers: [TransactionsController],
  providers: [TransactionsService, StatementExtractionService],
})
export class TransactionsModule {}
