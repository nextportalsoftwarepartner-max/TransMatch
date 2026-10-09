import { Catch, HttpException, HttpStatus, Logger, type ArgumentsHost, type ExceptionFilter } from '@nestjs/common';
import type { Response } from 'express';

// PostgreSQL error codes worth translating for the user
const UNIQUE_VIOLATION = '23505';
const FOREIGN_KEY_VIOLATION = '23503';

/** Gives every error the same JSON shape: { statusCode, message, code?, details? }. */
@Catch()
export class AllExceptionsFilter implements ExceptionFilter {
  private readonly logger = new Logger('Exception');

  catch(exception: unknown, host: ArgumentsHost): void {
    const response = host.switchToHttp().getResponse<Response>();

    if (exception instanceof HttpException) {
      const status = exception.getStatus();
      const body = exception.getResponse();
      const payload =
        typeof body === 'string'
          ? { statusCode: status, message: body }
          : { statusCode: status, ...(body as object), message: flattenMessage((body as { message?: unknown }).message) };
      response.status(status).json(payload);
      return;
    }

    const pgCode = (exception as { code?: unknown } | null)?.code;
    if (pgCode === UNIQUE_VIOLATION) {
      response
        .status(HttpStatus.CONFLICT)
        .json({ statusCode: 409, message: 'A record with the same value already exists.', code: 'DUPLICATE' });
      return;
    }
    if (pgCode === FOREIGN_KEY_VIOLATION) {
      response.status(HttpStatus.CONFLICT).json({
        statusCode: 409,
        message: 'The record is referenced by other records or refers to one that does not exist.',
        code: 'REFERENCE',
      });
      return;
    }

    this.logger.error(exception instanceof Error ? (exception.stack ?? exception.message) : String(exception));
    response
      .status(HttpStatus.INTERNAL_SERVER_ERROR)
      .json({ statusCode: 500, message: 'Unexpected error. Please contact the IT department.' });
  }
}

function flattenMessage(message: unknown): string {
  if (Array.isArray(message)) return message.join('; ');
  return typeof message === 'string' ? message : 'Request failed.';
}
