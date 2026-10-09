import { extractNameBasic } from '../names/name-extractor.js';
import type { StatementInfo, StatementTransaction } from '../types.js';
import { toNumber } from '../util/text.js';
import type { BankParser, ParserContext } from './parser.js';

// ===================== Maybank & Maybank Islamic =====================

function extractInfo({ headText: text }: ParserContext): StatementInfo {
  // Bank name, registration line and address
  const bankNameMatch = /((?:\b[A-Za-z]+\s+)?(?:Bank|Berhad|Islamic)[A-Za-z\s]*)/.exec(text);
  const bankName = bankNameMatch ? bankNameMatch[1].trim() : 'Unknown Bank';

  let headerLines: string[] = [];
  let bankRegistrationNo = 'Not Found';
  let bankAddress = 'Not Found';
  if (bankNameMatch) {
    headerLines = text.slice(text.indexOf(bankNameMatch[1])).split(/\n\s*/);
    bankRegistrationNo = headerLines[0].trim();
    if (headerLines.length > 1) bankAddress = headerLines[1].trim();
  }

  // Customer name: personal accounts print "MR / ENCIK ..."; otherwise it is
  // the third line after the bank name
  const customerMatch = /(MR \/ ENCIK [^\n]+)/.exec(text);
  let customerName = 'Unknown Customer';
  if (customerMatch) {
    customerName = customerMatch[1].trim();
  } else {
    const idx = headerLines.findIndex((line) => line.includes('Maybank Islamic Berhad'));
    if (idx >= 0 && idx + 3 < headerLines.length) {
      const candidate = headerLines[idx + 3].trim();
      if (candidate) customerName = candidate;
    }
  }

  // Customer address
  let addressParts: string[];
  if (customerMatch) {
    addressParts = text
      .slice(text.indexOf(customerMatch[1]))
      .split('\n')
      .slice(1, 5)
      .map((line) => line.trim())
      .filter(Boolean);
  } else {
    // From the fourth line after the bank name up to the page marker ("MUKA")
    const lines = text.split('\n');
    const bankIdx = lines.findIndex((line) => line.includes('Maybank Islamic Berhad'));
    const start = bankIdx >= 0 ? bankIdx + 4 : -1;
    const end = start >= 0 ? lines.findIndex((line, j) => j >= start && line.toUpperCase().includes('MUKA')) : -1;
    if (start >= 0 && start < end) {
      addressParts = lines
        .slice(start, end)
        .map((line) => line.trim())
        .filter(Boolean);
    } else {
      addressParts = ['Not Found', 'Not Found', 'Not Found', 'Not Found'];
    }
  }

  const statementDateMatch = /STATEMENT DATE\s*:\s*(\d{2}\/\d{2}\/\d{2})/.exec(text);
  const accountMatch = /ACCOUNT\s*NUMBER\s*:\s*([\d-]+)/.exec(text);

  return {
    bankName,
    bankRegistrationNo,
    bankAddress,
    customerName,
    customerAddress: addressParts.join(' '),
    statementDate: statementDateMatch ? statementDateMatch[1] : 'Unknown',
    accountNumber: accountMatch ? accountMatch[1].replaceAll('-', '') : 'Unknown',
  };
}

/** Removes every block that starts at a `from` line and runs through the next `until` line. */
function dropBlocks(lines: string[], from: string, until: string): string[] {
  const kept: string[] = [];
  let skip = false;
  for (const line of lines) {
    const upper = line.toUpperCase();
    if (upper.includes(from)) skip = true;
    else if (upper.includes(until)) {
      skip = false;
      continue;
    }
    if (!skip) kept.push(line);
  }
  return kept;
}

const FULL_ROW =
  /^\s*(\d{2}\/\d{2}(?:\/\d{2})?)\s+(.+?)\s+([\d,]+(?:\.\d{2})?)([-+]?)\s+([\d,]+(?:\.\d{2})?)\s+(.+)/;
// Row without trailing description lines
const SHORT_ROW = /^\s*(\d{2}\/\d{2}(?:\/\d{2})?)\s+(.+?)\s+([\d,]+(?:\.\d{2})?)([-+]?)\s+([\d,]+(?:\.\d{2})?)/;

function extractTransactions({ fullText }: ParserContext): StatementTransaction[] {
  // Strip page headers, the column heading block and the closing section
  let lines = dropBlocks(fullText.split('\n'), 'MAYBANK ISLAMIC BERHAD', 'URUSNIAGA AKAUN');
  lines = dropBlocks(lines, 'TARIKH MASUK', 'STATEMENT BALANCE');
  const endingIdx = lines.findIndex((line) => line.toUpperCase().includes('ENDING BALANCE :'));
  if (endingIdx >= 0) lines = lines.slice(0, endingIdx);

  // Each line starting with a date (DD/MM) begins a new transaction
  const rows = lines
    .map((line) => (/^\d{2}\/\d{2}/.test(line) ? `%% ${line}` : line))
    .join(' ')
    .split('%%')
    .filter((item) => /^\s*\d{2}\/\d{2}(\/\d{2})?\s/.test(item));

  const transactions: StatementTransaction[] = [];
  for (const row of rows) {
    const match = FULL_ROW.exec(row) ?? SHORT_ROW.exec(row);
    if (!match) continue;

    const description = match[2].trim();
    // The sign printed after the amount tells credit (+) from debit (-)
    const sign = match[4];
    const amount = sign ? toNumber(match[3].replaceAll(',', '')) : 0;
    const descriptionOthers = (match[6] ?? '').trim();

    transactions.push({
      date: match[1],
      description,
      descriptionOthers,
      targetName: extractNameBasic(`${description} ${descriptionOthers}`) || '',
      creditAmount: sign === '+' ? amount : 0,
      debitAmount: sign === '-' ? amount : 0,
      statementBalance: toNumber(match[5].replaceAll(',', '')),
    });
  }
  return transactions;
}

export const mbbParser: BankParser = { extractInfo, extractTransactions };
