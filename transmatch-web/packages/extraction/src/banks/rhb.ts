import { extractName } from '../names/name-extractor.js';
import type { PdfDocument, PdfWord } from '../pdf/pdf-document.js';
import { ExtractionError, type StatementInfo, type StatementTransaction } from '../types.js';
import { formatShort, parseDateAny } from '../util/dates.js';
import { titleCase } from '../util/text.js';
import type { BankParser, ParserContext } from './parser.js';

// ===================== RHB Bank, RHB Islamic & RHB Reflex =====================

const RHB_REFLEX = 8;

// ---------------------------------------------------------------------------
// RHB Reflex (cash management): fixed-layout statement read by coordinates
// ---------------------------------------------------------------------------

// Column x-ranges of the Reflex transaction table, in points
const REFLEX_COLUMNS = {
  Date: [10, 58],
  Branch: [59, 85],
  Description: [86, 130],
  Sender: [135, 185],
  Ref1: [191, 245],
  Ref2: [246, 305],
  RefNum: [306, 350],
  AmountDR: [351, 435],
  AmountCR: [436, 515],
  Balance: [516, 585],
} as const;
type ReflexColumn = keyof typeof REFLEX_COLUMNS;
type ReflexRow = Record<ReflexColumn, string>;

// Words within this vertical distance of a row's first word belong to that row
const REFLEX_ROW_TOLERANCE = 30;

// Header fields: [xmin, xmax, ymin, ymax] on the first page
const REFLEX_HEADER_BOXES = {
  customerName: [10, 300, 60, 72],
  customerAddress: [10, 300, 73, 130],
  statementDate: [320, 375, 150, 160],
  accountNumber: [10, 200, 180, 195],
} as const;

function readReflexRows(pdf: PdfDocument): ReflexRow[] {
  const rows: ReflexRow[] = [];
  for (let pageIndex = 0; pageIndex < pdf.pageCount; pageIndex++) {
    const pageWords = pdf.pageWords(pageIndex);
    if (pageWords.length === 0) continue;

    // Top to bottom (stable, so words on one line keep their left-to-right order)
    pageWords.sort((a, b) => a.top - b.top);

    const groups: PdfWord[][] = [];
    let group: PdfWord[] = [];
    let groupTop: number | null = null;
    for (const word of pageWords) {
      if (groupTop === null || Math.abs(word.top - groupTop) <= REFLEX_ROW_TOLERANCE) {
        groupTop ??= word.top;
        group.push(word);
      } else {
        groups.push(group);
        group = [word];
        groupTop = word.top;
      }
    }
    if (group.length > 0) groups.push(group);

    for (const rowWords of groups) {
      const row = {} as ReflexRow;
      for (const [column, [xmin, xmax]] of Object.entries(REFLEX_COLUMNS) as Array<[ReflexColumn, readonly [number, number]]>) {
        row[column] = rowWords
          .filter((w) => xmin <= w.x0 && w.x0 < xmax)
          .map((w) => w.text)
          .join(' ')
          .trim();
      }
      // Only rows that start with a transaction date (06-06-2024) are transactions
      if (!/^\d{2}-\d{2}-\d{4}$/.test(row.Date)) continue;
      rows.push(row);
    }
  }
  return rows;
}

function extractReflexInfo({ pdf }: ParserContext): StatementInfo {
  const pageWords = pdf.pageCount > 0 ? pdf.pageWords(0) : [];
  const readBox = ([xmin, xmax, ymin, ymax]: readonly number[], fallback: string) => {
    const found = pageWords
      .filter((w) => xmin <= w.x0 && w.x0 < xmax && ymin <= w.top && w.top < ymax)
      .map((w) => w.text)
      .join(' ')
      .trim();
    return found || fallback;
  };

  // e.g. "30 JUNE 2025" or "30 Jun 2025"
  const rawDate = readBox(REFLEX_HEADER_BOXES.statementDate, 'NA');
  const parsedDate = parseDateAny(titleCase(rawDate), ['%d %B %Y', '%d %b %Y']);

  return {
    bankName: 'RHB Bank Berhad',
    bankRegistrationNo: 'NA',
    bankAddress: 'NA',
    customerName: readBox(REFLEX_HEADER_BOXES.customerName, 'Unknown Customer'),
    customerAddress: readBox(REFLEX_HEADER_BOXES.customerAddress, 'NA'),
    statementDate: parsedDate ? formatShort(parsedDate) : 'NA',
    accountNumber: readBox(REFLEX_HEADER_BOXES.accountNumber, 'NA'),
  };
}

/** Amount cell to a number, ignoring separators and signs; blank or unreadable cells count as 0. */
function reflexAmount(raw: string): number {
  const value = raw.replaceAll(',', '').replaceAll('+', '').replaceAll('-', '').trim();
  return /^(\d+\.?\d*|\.\d+)$/.test(value) ? Number(value) : 0;
}

function extractReflexTransactions({ pdf }: ParserContext): StatementTransaction[] {
  return readReflexRows(pdf).map((row) => {
    const descriptionOthers = [row.Sender.replace(/(DISTRIBUTO)([A-Z0-9])/g, '$1 $2'), row.Ref1, row.Ref2]
      .filter(Boolean)
      .join(' ')
      .trim();

    // The sender column is the counterparty; fall back to the reference columns
    let targetName = row.Sender || [row.Ref1, row.Ref2].filter(Boolean).join(' ').trim();
    // The sender column is narrow: drop whatever is glued on after "DISTRIBUTO"
    targetName = targetName
      .replace(/DISTRIBUTO\S*/g, 'DISTRIBUTO')
      .replace(/\s{2,}/g, ' ')
      .trim();

    return {
      date: row.Date,
      description: row.Description,
      descriptionOthers,
      targetName,
      creditAmount: reflexAmount(row.AmountCR),
      debitAmount: reflexAmount(row.AmountDR),
      statementBalance: reflexAmount(row.Balance),
    };
  });
}

// ---------------------------------------------------------------------------
// RHB savings / current account statements: read from the text stream
// ---------------------------------------------------------------------------

const nonEmptyTrimmed = (text: string) =>
  text
    .split('\n')
    .map((ln) => ln.trim())
    .filter(Boolean);

const STATEMENT_PERIOD_LINE = /Statement\s+Period|Tempoh\s+Penyata/i;
// e.g. "Statement Period / Tempoh Penyata : 1 Jul 24 – 31 Jul 24"
const STATEMENT_PERIOD_RANGE = /(\d{1,2}\s+\w+\s+\d{2,4})\s*[–-]\s*(\d{1,2}\s+\w+\s+\d{2,4})/;

function extractAccountInfo({ headText: text }: ParserContext): StatementInfo {
  // The registration number follows the bank name on the same line
  const regMatch = /RHB\s+Bank\s+Berhad\s*(.+)/i.exec(text);

  const lines = nonEmptyTrimmed(text);
  const customerName = lines.length > 0 ? titleCase(lines[0].trim()) : 'Unknown Customer';

  const addressLines: string[] = [];
  for (const line of lines.slice(1)) {
    if (line.toUpperCase().includes('ACCOUNT STATEMENT / PENYATA AKAUN')) break;
    addressLines.push(line);
  }

  // The account number is the first line holding exactly 14 digits
  let accountNumber = 'Unknown';
  for (const line of lines) {
    const digits = line.replace(/\D/g, '');
    if (/^\d{14}$/.test(digits)) {
      accountNumber = digits;
      break;
    }
  }

  // The statement date is the end of the statement period
  let statementDate = 'NA';
  const periodLine = lines.find((line) => STATEMENT_PERIOD_LINE.test(line));
  const range = periodLine ? STATEMENT_PERIOD_RANGE.exec(periodLine) : null;
  if (range) {
    const parsed = parseDateAny(range[2], ['%d %b %y', '%d %B %y']);
    if (parsed) statementDate = formatShort(parsed);
  }

  return {
    bankName: 'RHB Bank Berhad',
    bankRegistrationNo: regMatch ? regMatch[1].trim() : 'NA',
    bankAddress: 'NA',
    customerName,
    customerAddress: addressLines.length > 0 ? addressLines.join(' ').trim() : 'Unknown Address',
    statementDate,
    accountNumber,
  };
}

/** Parses "27,764.33" or "27,764.33-" (trailing minus = overdrawn), ignoring the sign. */
function unsignedAmount(line: string): number | null {
  let value = line.trim().replaceAll(',', '');
  if (value.endsWith('-')) value = value.slice(0, -1);
  return /^\d+\.\d{2}$/.test(value) ? Number(value) : null;
}

function extractAccountTransactions({ fullText, bankId }: ParserContext): StatementTransaction[] {
  const trimmed = nonEmptyTrimmed(fullText);

  // Opening balance: the first amount after "B/F BALANCE"
  let previousBalance: number | null = null;
  const bfIdx = trimmed.findIndex((line) => line.toUpperCase().includes('B/F BALANCE'));
  if (bfIdx >= 0) {
    for (const line of trimmed.slice(bfIdx + 1)) {
      const amount = unsignedAmount(line);
      if (amount !== null) {
        previousBalance = amount;
        break;
      }
    }
  }

  // Transactions print day and month only; the year comes from the statement period
  let statementYear: number | null = null;
  const periodLine = trimmed.find((line) => STATEMENT_PERIOD_LINE.test(line));
  const range = periodLine ? STATEMENT_PERIOD_RANGE.exec(periodLine) : null;
  if (range) {
    statementYear = parseDateAny(range[2], ['%d %b %y', '%d %B %y', '%d %b %Y'])?.year ?? null;
  }

  // Step 1: keep what follows the opening balance (the line right after "B/F BALANCE" is its amount)
  const rawLines = fullText.split('\n');
  const firstLineOfPage = rawLines.length > 0 ? rawLines[0] : '';
  let lines: string[] = [];
  let started = false;
  let seenOpening = false;
  for (const line of rawLines) {
    if (line.toUpperCase().trim().includes('B/F BALANCE')) {
      seenOpening = true;
      continue;
    }
    if (seenOpening && !started) {
      started = true;
      continue;
    }
    if (started) lines.push(line.trim());
  }

  // Step 2: drop each following page header, from its first line down to the "Balance / Baki" heading
  let source = lines;
  lines = [];
  let skip = false;
  source.forEach((line, i) => {
    const current = line.trim();
    if (!current) return;
    const previous = i > 0 ? source[i - 1].trim() : '';
    if (current === firstLineOfPage) skip = true;
    else if (previous === 'Balance' && current === 'Baki') {
      skip = false;
      return;
    }
    if (!skip) lines.push(current);
  });

  // Step 3: stop at the line before "C/F BALANCE"
  source = lines;
  lines = [];
  for (let i = 0; i < source.length; i++) {
    const current = source[i].trim();
    if (!current) continue;
    const next = i + 1 < source.length ? source[i + 1].trim().toUpperCase() : '';
    if (next.includes('C/F BALANCE')) break;
    lines.push(current);
  }

  // A line such as "02 Jul" starts a new transaction block
  const blocks: string[][] = [];
  let block: string[] = [];
  for (const line of lines) {
    if (/^\d{1,2}\s+[A-Za-z]{3,}$/.test(line)) {
      if (block.length > 0) blocks.push(block);
      block = [line];
    } else {
      block.push(line);
    }
  }
  if (block.length > 0) blocks.push(block);

  const transactions: StatementTransaction[] = [];
  for (const entry of blocks) {
    const date = entry[0];
    const description = entry.length > 1 ? entry[1] : '';

    // Amount lines: the first is the transaction amount, the second the running balance
    const amounts = entry.map(unsignedAmount).filter((n): n is number => n !== null);
    if (amounts.length < 2) continue;
    const [amount, balance] = amounts;

    // Credit or debit is told by the movement of the (unsigned) balance
    let creditAmount = 0;
    let debitAmount = 0;
    if (previousBalance !== null) {
      if (balance <= previousBalance) creditAmount = amount;
      else debitAmount = amount;
    }

    // Everything else in the block is extra description; a 10-digit reference goes last
    const others: string[] = [];
    let reference: string | null = null;
    for (const raw of entry.slice(2)) {
      let value = raw.trim();
      if (!value) continue;
      if (value.endsWith('-')) value = value.slice(0, -1).trim();
      if (/^\d{10}$/.test(value)) {
        reference = value;
        continue;
      }
      if (/^[\d,]+\.\d{2}$/.test(value)) continue;
      if (value === description.trim()) continue;
      others.push(value);
    }
    if (reference) others.push(reference);
    const descriptionOthers = others.join(' ').trim();

    let formattedDate = date;
    if (statementYear) {
      const parsed = parseDateAny(`${date} ${statementYear}`, ['%d %b %Y']);
      if (!parsed) {
        throw new ExtractionError('PARSE_FAILED', `Unrecognised RHB transaction date "${date}".`, bankId);
      }
      formattedDate = formatShort(parsed);
    }

    transactions.push({
      date: formattedDate,
      description,
      descriptionOthers,
      targetName: extractName(`${description} ${descriptionOthers}`) || '',
      creditAmount,
      debitAmount,
      statementBalance: balance,
    });
    previousBalance = balance;
  }
  return transactions;
}

export const rhbParser: BankParser = {
  extractInfo: (ctx) => (ctx.bankId === RHB_REFLEX ? extractReflexInfo(ctx) : extractAccountInfo(ctx)),
  extractTransactions: (ctx) =>
    ctx.bankId === RHB_REFLEX ? extractReflexTransactions(ctx) : extractAccountTransactions(ctx),
};
