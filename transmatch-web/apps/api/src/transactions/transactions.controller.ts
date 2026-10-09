import {
  BadRequestException,
  Body,
  Controller,
  Get,
  Inject,
  Param,
  Post,
  Put,
  Query,
  UploadedFile,
  UseInterceptors,
} from '@nestjs/common';
import { FileInterceptor } from '@nestjs/platform-express';
import {
  can,
  enrichmentSearchSchema,
  PERMISSIONS,
  saveBatchSchema,
  updateTransactionSchema,
  type SessionUser,
} from '@transmatch/shared';
import { ForbiddenException } from '@nestjs/common';
import { basename } from 'node:path';
import type { z } from 'zod';
import { CustomersService } from '../admin/customers.service.js';
import { UsersService } from '../admin/users.service.js';
import { CurrentUser, RequirePermission } from '../auth/auth.decorators.js';
import { ZodPipe } from '../common/zod.pipe.js';
import { APP_CONFIG, type AppConfig } from '../config/app-config.js';
import { StatementExtractionService } from './statement-extraction.service.js';
import { TransactionsService } from './transactions.service.js';

const PDF_SIGNATURE = '%PDF-';

@Controller('transactions')
export class TransactionsController {
  constructor(
    private readonly transactions: TransactionsService,
    private readonly extraction: StatementExtractionService,
    private readonly customers: CustomersService,
    private readonly users: UsersService,
    @Inject(APP_CONFIG) private readonly config: AppConfig,
  ) {}

  // ---- Pickers used by the transaction screens (any signed-in user) ----

  @Get('lookups/bank-templates')
  bankTemplates() {
    return this.extraction.bankTemplates();
  }

  @Get('lookups/banks')
  banks() {
    return this.transactions.bankOptions();
  }

  @Get('lookups/customers')
  customerOptions() {
    return this.transactions.customerOptions();
  }

  @Get('lookups/customer-by-code')
  async customerByCode(@Query('code') code?: string) {
    const customer = code?.trim() ? await this.customers.findByCode(code) : null;
    return customer
      ? { found: true, customerCode: customer.customerCode, customerName: customer.customerName, address: customer.address }
      : { found: false };
  }

  @Get('lookups/file-names')
  fileNames() {
    return this.transactions.fileNames();
  }

  @Get('lookups/agents')
  agents() {
    return this.users.options();
  }

  // ---- PDF upload ----

  @Post('pdf/extract')
  @RequirePermission(PERMISSIONS.TRN_PDF_UPLOAD, 'CREATE')
  @UseInterceptors(FileInterceptor('file'))
  extract(@UploadedFile() file: Express.Multer.File | undefined, @Body('bankId') bankId?: string) {
    if (!file) throw new BadRequestException('Please choose a PDF file.');
    if (file.size > this.config.uploadMaxBytes) {
      throw new BadRequestException(`The file is larger than ${Math.round(this.config.uploadMaxBytes / 1048576)} MB.`);
    }
    if (file.buffer.subarray(0, 1024).indexOf(PDF_SIGNATURE) < 0) {
      throw new BadRequestException('Only PDF files can be uploaded.');
    }
    const template = bankId ? Number(bankId) : undefined;
    if (template !== undefined && !this.extraction.bankTemplates().some((t) => t.id === template)) {
      throw new BadRequestException('Unknown bank template.');
    }
    // Browsers send the name as latin1 bytes; keep only the file name, never a path
    const fileName = basename(Buffer.from(file.originalname, 'latin1').toString('utf8')).slice(0, 255);
    return this.transactions.previewStatement(fileName, file.buffer, template);
  }

  // ---- Save a reviewed statement or a manual-entry session ----

  @Post('batches')
  saveBatch(@Body(new ZodPipe(saveBatchSchema)) body: z.infer<typeof saveBatchSchema>, @CurrentUser() user: SessionUser) {
    const permission = body.source === 'PU' ? PERMISSIONS.TRN_PDF_UPLOAD : PERMISSIONS.TRN_MANUAL_INPUT;
    if (!can(user, permission, 'CREATE')) throw new ForbiddenException('You do not have access to this function.');
    return this.transactions.saveBatch(body, user.userId);
  }

  // ---- Data enrichment ----

  @Get()
  @RequirePermission(PERMISSIONS.TRN_DATA_ENRICHMENT)
  search(@Query(new ZodPipe(enrichmentSearchSchema)) query: z.infer<typeof enrichmentSearchSchema>) {
    return this.transactions.search(query);
  }

  @Get(':id')
  @RequirePermission(PERMISSIONS.TRN_DATA_ENRICHMENT)
  get(@Param('id') id: string) {
    return this.transactions.get(id);
  }

  @Put(':id')
  @RequirePermission(PERMISSIONS.TRN_DATA_ENRICHMENT, 'UPDATE')
  update(
    @Param('id') id: string,
    @Body(new ZodPipe(updateTransactionSchema)) body: z.infer<typeof updateTransactionSchema>,
    @CurrentUser() user: SessionUser,
  ) {
    return this.transactions.update(id, body, user.userId);
  }
}
