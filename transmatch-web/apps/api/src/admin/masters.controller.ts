import {
  BadRequestException,
  Body,
  Controller,
  Delete,
  Get,
  HttpCode,
  Param,
  Post,
  Put,
  Query,
  StreamableFile,
  UploadedFile,
  UseInterceptors,
} from '@nestjs/common';
import { FileInterceptor } from '@nestjs/platform-express';
import {
  bankSchema,
  customerRemarkSchema,
  customerSchema,
  deleteManySchema,
  PERMISSIONS,
  watchNameSchema,
  type SessionUser,
} from '@transmatch/shared';
import type { z } from 'zod';
import { CurrentUser, RequirePermission } from '../auth/auth.decorators.js';
import { ZodPipe } from '../common/zod.pipe.js';
import { BanksService } from './banks.service.js';
import { CustomersService } from './customers.service.js';
import { WatchlistService, type WatchlistKind } from './watchlist.service.js';

const XLSX_MIME = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet';
const IMPORT_MAX_BYTES = 5 * 1024 * 1024;

@Controller('customers')
@RequirePermission(PERMISSIONS.ADM_CUSTOMER_PROFILE)
export class CustomersController {
  constructor(private readonly customers: CustomersService) {}

  @Get()
  list(@Query('code') code?: string, @Query('name') name?: string) {
    return this.customers.list({ code: code?.trim() || undefined, name: name?.trim() || undefined });
  }

  @Post()
  @RequirePermission(PERMISSIONS.ADM_CUSTOMER_PROFILE, 'CREATE')
  create(@Body(new ZodPipe(customerSchema)) body: z.infer<typeof customerSchema>, @CurrentUser() user: SessionUser) {
    return this.customers.create(body, user.userId);
  }

  @Put(':id')
  @RequirePermission(PERMISSIONS.ADM_CUSTOMER_PROFILE, 'UPDATE')
  update(
    @Param('id') id: string,
    @Body(new ZodPipe(customerSchema)) body: z.infer<typeof customerSchema>,
    @CurrentUser() user: SessionUser,
  ) {
    return this.customers.update(id, body, user.userId);
  }

  @Put(':id/remark')
  @RequirePermission(PERMISSIONS.ADM_CUSTOMER_PROFILE, 'UPDATE')
  setRemark(
    @Param('id') id: string,
    @Body(new ZodPipe(customerRemarkSchema)) body: z.infer<typeof customerRemarkSchema>,
    @CurrentUser() user: SessionUser,
  ) {
    return this.customers.setRemark(id, body.remark, user.userId);
  }

  @Delete(':id')
  @HttpCode(204)
  @RequirePermission(PERMISSIONS.ADM_CUSTOMER_PROFILE, 'DELETE')
  remove(@Param('id') id: string, @CurrentUser() user: SessionUser) {
    return this.customers.remove(id, user.userId);
  }
}

@Controller('banks')
@RequirePermission(PERMISSIONS.ADM_BANK_PROFILE)
export class BanksController {
  constructor(private readonly banks: BanksService) {}

  @Get()
  list(@Query('name') name?: string) {
    return this.banks.list(name?.trim() || undefined);
  }

  @Post()
  @RequirePermission(PERMISSIONS.ADM_BANK_PROFILE, 'CREATE')
  create(@Body(new ZodPipe(bankSchema)) body: z.infer<typeof bankSchema>, @CurrentUser() user: SessionUser) {
    return this.banks.create(body, user.userId);
  }

  @Put(':id')
  @RequirePermission(PERMISSIONS.ADM_BANK_PROFILE, 'UPDATE')
  update(
    @Param('id') id: string,
    @Body(new ZodPipe(bankSchema)) body: z.infer<typeof bankSchema>,
    @CurrentUser() user: SessionUser,
  ) {
    return this.banks.update(id, body, user.userId);
  }

  @Delete(':id')
  @HttpCode(204)
  @RequirePermission(PERMISSIONS.ADM_BANK_PROFILE, 'DELETE')
  remove(@Param('id') id: string, @CurrentUser() user: SessionUser) {
    return this.banks.remove(id, user.userId);
  }
}

/** Routes shared by the blacklisted and suspicious name lists. */
abstract class WatchlistController {
  protected abstract readonly kind: WatchlistKind;
  constructor(protected readonly watchlist: WatchlistService) {}

  protected listNames(name?: string, existsInBlacklisted?: string) {
    return this.watchlist.list(this.kind, {
      name: name?.trim() || undefined,
      existsInBlacklisted: existsInBlacklisted === 'Yes' || existsInBlacklisted === 'No' ? existsInBlacklisted : undefined,
    });
  }

  protected async templateFile(): Promise<StreamableFile> {
    return new StreamableFile(await this.watchlist.template(this.kind), {
      type: XLSX_MIME,
      disposition: `attachment; filename="${this.kind}_template.xlsx"`,
    });
  }

  protected importFile(file: Express.Multer.File | undefined, user: SessionUser) {
    if (!file) throw new BadRequestException('Please choose an Excel file to import.');
    return this.watchlist.importExcel(this.kind, file.buffer, user.userId);
  }
}

type NameBody = z.infer<typeof watchNameSchema>;
type DeleteManyBody = z.infer<typeof deleteManySchema>;
const importInterceptor = () => FileInterceptor('file', { limits: { fileSize: IMPORT_MAX_BYTES } });

@Controller('blacklisted')
@RequirePermission(PERMISSIONS.ADM_BLACKLISTED)
export class BlacklistedController extends WatchlistController {
  protected readonly kind = 'blacklisted';
  constructor(watchlist: WatchlistService) {
    super(watchlist);
  }

  @Get()
  list(@Query('name') name?: string) {
    return this.listNames(name);
  }

  @Get('template')
  template() {
    return this.templateFile();
  }

  @Post()
  @HttpCode(204)
  @RequirePermission(PERMISSIONS.ADM_BLACKLISTED, 'CREATE')
  create(@Body(new ZodPipe(watchNameSchema)) body: NameBody, @CurrentUser() user: SessionUser) {
    return this.watchlist.create(this.kind, body.name, user.userId);
  }

  @Post('import')
  @RequirePermission(PERMISSIONS.ADM_BLACKLISTED, 'CREATE')
  @UseInterceptors(importInterceptor())
  import(@UploadedFile() file: Express.Multer.File | undefined, @CurrentUser() user: SessionUser) {
    return this.importFile(file, user);
  }

  @Post('delete')
  @RequirePermission(PERMISSIONS.ADM_BLACKLISTED, 'DELETE')
  async removeMany(@Body(new ZodPipe(deleteManySchema)) body: DeleteManyBody, @CurrentUser() user: SessionUser) {
    return { deleted: await this.watchlist.removeMany(this.kind, body.ids, user.userId) };
  }

  @Put(':id')
  @HttpCode(204)
  @RequirePermission(PERMISSIONS.ADM_BLACKLISTED, 'UPDATE')
  update(@Param('id') id: string, @Body(new ZodPipe(watchNameSchema)) body: NameBody, @CurrentUser() user: SessionUser) {
    return this.watchlist.update(this.kind, id, body.name, user.userId);
  }
}

@Controller('suspicious')
@RequirePermission(PERMISSIONS.ADM_SUSPICIOUS)
export class SuspiciousController extends WatchlistController {
  protected readonly kind = 'suspicious';
  constructor(watchlist: WatchlistService) {
    super(watchlist);
  }

  @Get()
  list(@Query('name') name?: string, @Query('existsInBlacklisted') existsInBlacklisted?: string) {
    return this.listNames(name, existsInBlacklisted);
  }

  @Get('template')
  template() {
    return this.templateFile();
  }

  @Post()
  @HttpCode(204)
  @RequirePermission(PERMISSIONS.ADM_SUSPICIOUS, 'CREATE')
  create(@Body(new ZodPipe(watchNameSchema)) body: NameBody, @CurrentUser() user: SessionUser) {
    return this.watchlist.create(this.kind, body.name, user.userId);
  }

  @Post('import')
  @RequirePermission(PERMISSIONS.ADM_SUSPICIOUS, 'CREATE')
  @UseInterceptors(importInterceptor())
  import(@UploadedFile() file: Express.Multer.File | undefined, @CurrentUser() user: SessionUser) {
    return this.importFile(file, user);
  }

  @Post('delete')
  @RequirePermission(PERMISSIONS.ADM_SUSPICIOUS, 'DELETE')
  async removeMany(@Body(new ZodPipe(deleteManySchema)) body: DeleteManyBody, @CurrentUser() user: SessionUser) {
    return { deleted: await this.watchlist.removeMany(this.kind, body.ids, user.userId) };
  }

  @Put(':id')
  @HttpCode(204)
  @RequirePermission(PERMISSIONS.ADM_SUSPICIOUS, 'UPDATE')
  update(@Param('id') id: string, @Body(new ZodPipe(watchNameSchema)) body: NameBody, @CurrentUser() user: SessionUser) {
    return this.watchlist.update(this.kind, id, body.name, user.userId);
  }
}
