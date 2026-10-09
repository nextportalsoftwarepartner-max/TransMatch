import { Body, Controller, Get, HttpCode, Post, Query, StreamableFile } from '@nestjs/common';
import { enquirySearchSchema, exportSchema, PERMISSIONS, type SessionUser } from '@transmatch/shared';
import type { z } from 'zod';
import { CurrentUser, RequirePermission } from '../auth/auth.decorators.js';
import { ZodPipe } from '../common/zod.pipe.js';
import { ReportsService } from './reports.service.js';

type ExportBody = z.infer<typeof exportSchema>;

@Controller('reports/enquiry')
@RequirePermission(PERMISSIONS.RPT_ENQUIRY)
export class ReportsController {
  constructor(private readonly reports: ReportsService) {}

  @Get()
  enquiry(@Query(new ZodPipe(enquirySearchSchema)) query: z.infer<typeof enquirySearchSchema>) {
    return this.reports.enquiry(query);
  }

  @Post('export/text')
  @HttpCode(200)
  async exportText(@Body(new ZodPipe(exportSchema)) body: ExportBody, @CurrentUser() user: SessionUser) {
    return { text: await this.reports.exportText(body.transactionIds, user.userId) };
  }

  @Post('export/excel')
  @HttpCode(200)
  async exportExcel(@Body(new ZodPipe(exportSchema)) body: ExportBody, @CurrentUser() user: SessionUser) {
    const stamp = new Date().toLocaleString('sv-SE', { timeZone: 'Asia/Kuala_Lumpur' }).replace(/[-:]/g, '').replace(' ', '_');
    return new StreamableFile(await this.reports.exportExcel(body.transactionIds, user.userId), {
      type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
      disposition: `attachment; filename="Transaction_Export_${stamp}.xlsx"`,
    });
  }
}
