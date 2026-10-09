import type { ExtractionResult, StatementInfo, StatementTransaction } from './types.js';
import { formatIso, isRealDate, parseDateAny, type DateParts } from './util/dates.js';

export interface NormalizedStatement {
  bankId: number;
  bankTemplate: string;
  info: StatementInfo & { statementDateIso: string | null };
  transactions: Array<StatementTransaction & { dateIso: string | null }>;
}

/** Statement dates as the templates print them: 31/12/24, 31/12/2024, 31-12-2024 or 2024-12-31. */
export function parseStatementDate(raw: string): DateParts | null {
  return parseDateAny(raw.trim(), ['%d/%m/%y', '%d/%m/%Y', '%d-%m-%Y', '%Y-%m-%d']);
}

/**
 * Resolves a transaction date to a full date.
 *
 * - "DD/MM"        year taken from the statement date; a month later than the
 *                  statement month belongs to the previous year (a January
 *                  statement listing December transactions)
 * - "DD/MM/YY", "DD/MM/YYYY", "DD-MM-YYYY", "YYYY-MM-DD"
 */
export function resolveTransactionDate(raw: string, statementDate: DateParts | null): DateParts | null {
  const value = raw.trim();

  const dayMonth = /^(\d{2})\/(\d{2})$/.exec(value);
  if (dayMonth) {
    if (!statementDate) return null;
    const day = Number(dayMonth[1]);
    const month = Number(dayMonth[2]);
    const year = month > statementDate.month ? statementDate.year - 1 : statementDate.year;
    return isRealDate(year, month, day) ? { year, month, day } : null;
  }

  return parseDateAny(value, ['%d/%m/%y', '%d/%m/%Y', '%d-%m-%Y', '%Y-%m-%d']);
}

/** Adds ISO (yyyy-mm-dd) dates to an extraction result; null where a date could not be resolved. */
export function normalizeStatement(result: ExtractionResult): NormalizedStatement {
  const statementDate = parseStatementDate(result.info.statementDate);
  return {
    bankId: result.bankId,
    bankTemplate: result.bankTemplate,
    info: { ...result.info, statementDateIso: statementDate ? formatIso(statementDate) : null },
    transactions: result.transactions.map((trx) => {
      const date = resolveTransactionDate(trx.date, statementDate);
      return { ...trx, dateIso: date ? formatIso(date) : null };
    }),
  };
}
