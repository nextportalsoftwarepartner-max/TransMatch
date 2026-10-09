import { extractNameSmart } from '../names/name-extractor.js';
import { ExtractionError, type StatementInfo, type StatementTransaction } from '../types.js';
import { formatShort, parseDate, type DateParts } from '../util/dates.js';
import { titleCase } from '../util/text.js';
import type { BankParser, ParserContext } from './parser.js';

// ===================== UOB & UOB Islamic =====================

const nonEmptyTrimmed = (text: string) =>
  text
    .split('\n')
    .map((ln) => ln.trim())
    .filter(Boolean);

function extractInfo({ headText }: ParserContext): StatementInfo {
  const lines = nonEmptyTrimmed(headText);

  // Customer name: the first line that carries "SDN BHD"
  const nameLine = lines.find((line) => /\bSDN\.?\s+BHD\.?\b/i.test(line));

  // e.g. "Current Account MYR 1103010670"
  let accountNumber = 'NA';
  for (const line of lines) {
    if (!line.toUpperCase().includes('CURRENT ACCOUNT')) continue;
    const match = /Current\s+Account.*?(\d{6,})/i.exec(line);
    if (match) {
      accountNumber = match[1].trim();
      break;
    }
  }

  // The line under "Statement Date" holds the period, e.g. "01/06/2024 - 30/06/2024"; take the later date
  let statementDate = 'NA';
  const labelIdx = lines.findIndex((line) => line.trim().toLowerCase() === 'statement date');
  if (labelIdx >= 0 && labelIdx + 1 < lines.length) {
    const found = lines[labelIdx + 1].match(/\d{2}\/\d{2}\/\d{4}/g) ?? [];
    const dates = found.map((d) => parseDate(d, '%d/%m/%Y'));
    if (dates.length > 0 && dates.every((d): d is DateParts => d !== null)) {
      const latest = dates.reduce((a, b) => (ordinal(b) > ordinal(a) ? b : a));
      statementDate = formatShort(latest);
    }
  }

  return {
    bankName: 'UOB Bank Berhad',
    bankRegistrationNo: 'NA',
    bankAddress: 'NA',
    customerName: nameLine ? titleCase(nameLine.trim()) : 'NA',
    customerAddress: 'NA',
    statementDate,
    accountNumber,
  };
}

const ordinal = (d: DateParts) => d.year * 10000 + d.month * 100 + d.day;

// Amount formats: 44,866.97 / -44,866.97 / 44,866.97-
const AMOUNT = /^-?\d{1,3}(?:,\d{3})*\.\d{2}-?$/;

function signedAmount(raw: string): number {
  let value = raw.trim().replaceAll(',', '');
  let negative = false;
  if (value.startsWith('-')) {
    negative = true;
    value = value.slice(1);
  }
  if (value.endsWith('-')) {
    negative = true;
    value = value.slice(0, -1);
  }
  const amount = /^\d+\.\d{2}$/.test(value) ? Number(value) : 0;
  return negative ? -amount : amount;
}

async function extractTransactions({
  fullText,
  bankId,
  embeddingNameExtractor,
}: ParserContext): Promise<StatementTransaction[]> {
  // Step 1: drop each page header, from "Account Activities" down to the "Ledger Balance(MYR)" heading
  let lines: string[] = [];
  let skip = false;
  for (const line of nonEmptyTrimmed(fullText)) {
    const upper = line.toUpperCase();
    if (upper.includes('ACCOUNT ACTIVITIES')) {
      skip = true;
      continue;
    }
    if (upper.includes('LEDGER BALANCE(MYR)')) {
      skip = false;
      continue;
    }
    if (!skip) lines.push(line);
  }

  // Step 2: stop at the totals section
  const totalsIdx = lines.findIndex((line) => line.toUpperCase().includes('TOTAL DEPOSITS(MYR)'));
  if (totalsIdx >= 0) lines = lines.slice(0, totalsIdx);

  // Step 3: drop the posting timestamp ("01/06/2024 10:33:32") and the AM/PM line under it
  const source = lines;
  lines = [];
  for (let i = 0; i < source.length; i++) {
    if (/\d{2}\/\d{2}\/\d{4}\s+\d{1,2}:\d{2}:\d{2}/.test(source[i])) {
      i += 1;
      continue;
    }
    lines.push(source[i]);
  }

  // A line that is only a date (02/06/2024) starts a new transaction block
  const blocks: string[][] = [];
  let block: string[] = [];
  for (const line of lines) {
    if (/^\d{2}\/\d{2}\/\d{4}$/.test(line)) {
      if (block.length > 0) blocks.push(block);
      block = [line];
    } else {
      block.push(line);
    }
  }
  if (block.length > 0) blocks.push(block);

  const transactions: StatementTransaction[] = [];
  for (const entry of blocks) {
    if (entry.length < 5) continue; // not enough lines to be a transaction

    // Three amounts are expected, in order: withdrawal, deposit, ledger balance
    const amountLines = entry.filter((line) => AMOUNT.test(line));
    if (amountLines.length < 3) continue;

    const parsedDate = parseDate(entry[0].trim(), '%d/%m/%Y');
    if (!parsedDate) {
      throw new ExtractionError('PARSE_FAILED', `Unrecognised UOB transaction date "${entry[0]}".`, bankId);
    }

    const description = entry[1].trim();
    // Everything between the description and the first amount is extra description
    const descriptionOthers = entry.slice(2, entry.indexOf(amountLines[0])).join(' ').trim();
    const targetName = await extractNameSmart(`${description} ${descriptionOthers}`, embeddingNameExtractor);

    transactions.push({
      date: formatShort(parsedDate),
      description,
      descriptionOthers,
      targetName: targetName || '',
      creditAmount: signedAmount(amountLines[1]),
      debitAmount: signedAmount(amountLines[0]),
      statementBalance: signedAmount(amountLines[2]),
    });
  }
  return transactions;
}

export const uobParser: BankParser = { extractInfo, extractTransactions };
