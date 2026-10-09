import { extractNameBasic } from '../names/name-extractor.js';
import { ExtractionError, type StatementInfo, type StatementTransaction } from '../types.js';
import { formatShort, parseDate } from '../util/dates.js';
import { toNumber, words } from '../util/text.js';
import type { BankParser, ParserContext } from './parser.js';

// ===================== Public Bank & Public Islamic Bank =====================

const PUBLIC_ISLAMIC_BANK = 1;
const PUBLIC_BANK = 2;

const isDayMonth = (s: string) => /^\d{2}\/\d{2}$/.test(s);
const isTwoDecimalNumeric = (s: string) => /^\d+\.\d{2}$/.test(s.replaceAll(',', '').trim());

function extractInfo({ headText, bankId }: ParserContext): StatementInfo {
  const lines = headText.split('\n');

  // The branch address sits between a marker line and the "TEL:" line.
  // The registration number is not printed on this template.
  const addressLines: string[] = [];
  let collecting = false;
  for (const line of lines) {
    const upper = line.toUpperCase();
    if (bankId === PUBLIC_ISLAMIC_BANK && upper.includes('CALL 03-2170 8000 OR VISIT OUR WEBSITE')) {
      collecting = true;
      continue;
    }
    if (bankId === PUBLIC_BANK && upper.includes('T&C APPLY')) {
      collecting = true;
      continue;
    }
    if (upper.includes('TEL:')) break;
    if (collecting) addressLines.push(line.trim());
  }

  const customerName = lines.length > 1 ? lines[1].trim() : 'Unknown Customer';

  // Customer address: from the third line up to the first line containing a full stop
  const customerAddressLines: string[] = [];
  for (let i = 2; i < lines.length; i++) {
    if (lines[i].includes('.')) break;
    customerAddressLines.push(lines[i].trim());
  }

  const dateIdx = lines.findIndex((line) => line.toUpperCase().includes('STATEMENT DATE'));
  if (dateIdx < 0 || dateIdx + 1 >= lines.length) {
    throw new ExtractionError('PARSE_FAILED', 'Statement date not found on the Public Bank statement.', bankId);
  }
  const parsedDate = parseDate(lines[dateIdx + 1].trim(), '%d %b %Y');
  const statementDate = parsedDate ? formatShort(parsedDate) : 'Invalid Date';

  const accountIdx = lines.findIndex((line) => line.toUpperCase().includes('ACCOUNT NUMBER'));
  if (accountIdx < 0 || accountIdx + 1 >= lines.length) {
    throw new ExtractionError('PARSE_FAILED', 'Account number not found on the Public Bank statement.', bankId);
  }

  return {
    bankName: 'Public Bank',
    bankRegistrationNo: 'N/A',
    bankAddress: addressLines.join(' '),
    customerName,
    customerAddress: customerAddressLines.join(' '),
    statementDate,
    accountNumber: lines[accountIdx + 1].trim(),
  };
}

function extractTransactions({ fullText }: ParserContext): StatementTransaction[] {
  const allLines = fullText.split('\n');

  // Step 1: drop each page header, from the repeated first line down to the opening balance
  const pageMarker = allLines[0].trim();
  let lines: string[] = [];
  let skip = false;
  for (const line of allLines) {
    if (pageMarker === line.toUpperCase()) skip = true;
    else if (line.toUpperCase().includes('BALANCE FROM LAST STATEMENT')) skip = false;
    if (!skip) lines.push(line);
  }

  // Step 2: drop everything from "BALANCE C/F" until the line before "BALANCE B/F"
  let source = lines;
  lines = [];
  skip = false;
  source.forEach((line, i) => {
    const next = i + 1 < source.length ? source[i + 1].trim().toUpperCase() : '';
    if (line.toUpperCase().includes('BALANCE C/F')) skip = true;
    else if (next.includes('BALANCE B/F')) skip = false;
    if (!skip) lines.push(line);
  });

  // Step 3: drop the "BALANCE B/F" line together with its neighbours
  source = lines;
  lines = [];
  skip = false;
  source.forEach((line, i) => {
    const prev = i - 1 >= 0 ? source[i - 1].trim().toUpperCase() : '';
    const next = i + 1 < source.length ? source[i + 1].trim().toUpperCase() : '';
    if (next.includes('BALANCE B/F')) skip = true;
    else if (prev.includes('BALANCE B/F')) {
      skip = false;
      return;
    }
    if (!skip) lines.push(line);
  });

  // Step 4: drop the closing section
  const closingIdx = lines.findIndex((line) => line.toUpperCase().includes('CLOSING BALANCE IN THIS STATEMENT'));
  if (closingIdx >= 0) lines = lines.slice(0, closingIdx);

  // Mark up the line stream: %% starts a date, ## starts a transaction, #@ continues one
  const marked: string[] = [];
  lines.forEach((line, i) => {
    if (isDayMonth(line.trim())) {
      marked.push(`%% ${line}`);
    } else if (i >= 1) {
      const prev = lines[i - 1];
      if (isDayMonth(prev) || (isTwoDecimalNumeric(line) && !isTwoDecimalNumeric(prev))) {
        marked.push(`## ${line}`);
      } else {
        marked.push(`#@ ${line}`);
      }
    }
  });

  const transactions: StatementTransaction[] = [];
  let compareBalance: number | null = null;

  marked
    .join(' ')
    .split('%%')
    .forEach((rawChunk, idx) => {
      const chunk = rawChunk.trim();
      if (!chunk) return;

      // The first chunk is the opening balance
      if (idx === 0) {
        compareBalance = toNumber(chunk.replaceAll('##', '').replaceAll(',', '').trim());
        return;
      }

      const parts = chunk.split('##');
      const date = parts[0].trim() ? words(parts[0])[0] : 'Unknown';

      for (const part of parts.slice(1)) {
        if (!part.trim()) continue;
        const fields = part
          .trim()
          .split('#@')
          .map((p) => p.trim());

        const amount = toNumber(fields[0].replaceAll(',', ''));
        const statementBalance = fields.length > 1 ? toNumber(fields[1].replaceAll(',', '')) : 0;
        const description = fields.length > 2 ? fields[2] : '';
        const descriptionOthers = fields.length > 3 ? fields.slice(3).join(' ') : '';

        // A falling balance is a debit, otherwise a credit
        let debitAmount = 0;
        let creditAmount = 0;
        if (compareBalance !== null) {
          if (statementBalance < compareBalance) debitAmount = amount;
          else creditAmount = amount;
        }

        transactions.push({
          date,
          description,
          descriptionOthers,
          targetName: extractNameBasic(`${description} ${descriptionOthers}`) || '',
          creditAmount,
          debitAmount,
          statementBalance,
        });
        compareBalance = statementBalance;
      }
    });

  return transactions;
}

export const pbbParser: BankParser = { extractInfo, extractTransactions };
