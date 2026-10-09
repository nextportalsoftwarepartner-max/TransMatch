import { extractName } from '../names/name-extractor.js';
import type { StatementInfo, StatementTransaction } from '../types.js';
import { titleCase } from '../util/text.js';
import type { BankParser, ParserContext } from './parser.js';

// ===================== Hong Leong Bank & Hong Leong Islamic Bank =====================
// Islamic statements are read with the same rules and bank name as
// conventional ones, as the desktop application did.

// Amount column x-position ranges, in points from the left page edge
const CREDIT_X_RANGE: [number, number] = [350, 400];
const DEBIT_X_RANGE: [number, number] = [450, 500];
const BALANCE_X_MIN = 501; // the statement balance is the right-most column

const PAGE_FOOTER_KEY = 'HONG LEONG BANK BERHAD';
const TABLE_START_KEY = 'BAKI';

function extractInfo({ headText: text }: ParserContext): StatementInfo {
  const regMatch = /Hong\s+Leong\s+Bank\s+Berhad\s*\(([\d\-Xx]+)\)/i.exec(text);

  const branchMatch = /Branch\s*\/\s*Cawangan\s*:\s*(.+)/.exec(text);
  const telMatch = /Tel No\s*\/\s*No Tel\s*:\s*(.+)/.exec(text);
  const bankAddress =
    branchMatch && telMatch ? `${branchMatch[1].trim()} (${telMatch[1].trim()})` : 'Not Found';

  const nameMatch = /(?<=\n)([A-Z][A-Z\s]+)\nDate\s*\/\s*Tarikh/.exec(text);

  const addressMatch = /Date\s*\/\s*Tarikh\s*:\s*[^\n]+\n(.+?)\nA\/C No/s.exec(text);
  const customerAddress = addressMatch
    ? addressMatch[1]
        .split('\n')
        .map((line) => line.trim())
        .filter(Boolean)
        .join(' ')
    : 'Not Found';

  const dateMatch = /Date\s*\/\s*Tarikh\s*:\s*(\d{2}-\d{2}-\d{4})/.exec(text);
  const accountMatch = /A\/C No\s*\/\s*No Akaun\s*:\s*([\d-]+)/.exec(text);

  return {
    bankName: 'Hong Leong Bank Berhad',
    bankRegistrationNo: regMatch ? regMatch[1] : 'Not Found',
    bankAddress,
    customerName: nameMatch ? titleCase(nameMatch[1].trim()) : 'Unknown Customer',
    customerAddress,
    statementDate: dateMatch ? dateMatch[1].replaceAll('-', '/') : 'Unknown',
    accountNumber: accountMatch ? accountMatch[1].replaceAll('-', '') : 'Unknown',
  };
}

const isDate = (s: string) => /^\d{2}-\d{2}-\d{4}$/.test(s.trim());
const isAmount = (s: string) => /^\d{1,3}(,\d{3})*(\.\d{2})$/.test(s.trim());

/**
 * Reads the positioned text spans page by page. A date starts a transaction;
 * amounts are assigned to credit, debit or balance by the column they sit in.
 */
function extractTransactions({ pdf }: ParserContext): StatementTransaction[] {
  const transactions: StatementTransaction[] = [];
  let currentDate: string | null = null;
  let currentBlock: string[] = [];
  let currentAmounts: Array<[number, number]> = [];

  const finishBlock = () => {
    if (!currentDate || currentBlock.length === 0) return;
    let creditAmount = 0;
    let debitAmount = 0;
    let statementBalance = 0;
    for (const [value, x0] of currentAmounts) {
      if (CREDIT_X_RANGE[0] <= x0 && x0 < CREDIT_X_RANGE[1]) creditAmount = value;
      else if (DEBIT_X_RANGE[0] <= x0 && x0 < DEBIT_X_RANGE[1]) debitAmount = value;
      else if (x0 >= BALANCE_X_MIN) statementBalance = value;
    }
    const description = currentBlock[0];
    const descriptionOthers = currentBlock.slice(1).join(' ');
    transactions.push({
      date: currentDate.replaceAll('-', '/'),
      description,
      descriptionOthers,
      targetName: extractName(`${description} ${descriptionOthers}`) || '',
      creditAmount,
      debitAmount,
      statementBalance,
    });
  };

  // Everything from the bank name in the page footer to the next table
  // heading ("Baki") is page furniture, not transactions.
  let skipping = false;

  for (let pageIndex = 0; pageIndex < pdf.pageCount; pageIndex++) {
    for (const line of pdf.pageSpanLines(pageIndex)) {
      for (const span of line) {
        const text = span.text.trim();
        if (!text) continue;

        if (text.toUpperCase().includes(PAGE_FOOTER_KEY)) skipping = true;
        if (text.toUpperCase() === TABLE_START_KEY) {
          skipping = false;
          break;
        }
        if (skipping) break;

        if (isDate(text)) {
          finishBlock();
          currentDate = text;
          currentBlock = [];
          currentAmounts = [];
          continue;
        }

        if (isAmount(text)) {
          currentAmounts.push([Number(text.replaceAll(',', '')), span.x0]);
        } else {
          currentBlock.push(text);
        }
      }
    }
  }
  finishBlock();

  return transactions;
}

export const hlbParser: BankParser = { extractInfo, extractTransactions };
