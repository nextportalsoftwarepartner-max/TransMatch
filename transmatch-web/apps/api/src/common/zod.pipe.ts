import { BadRequestException, type PipeTransform } from '@nestjs/common';
import type { ZodType } from 'zod';

/** Validates and normalises a request body or query string with a zod schema. */
export class ZodPipe<T> implements PipeTransform<unknown, T> {
  constructor(private readonly schema: ZodType<T>) {}

  transform(value: unknown): T {
    const result = this.schema.safeParse(value ?? {});
    if (!result.success) {
      const details = result.error.issues.map((issue) => ({ path: issue.path.join('.'), message: issue.message }));
      throw new BadRequestException({
        statusCode: 400,
        message: details[0]?.message ?? 'Invalid request.',
        code: 'VALIDATION_FAILED',
        details,
      });
    }
    return result.data;
  }
}
