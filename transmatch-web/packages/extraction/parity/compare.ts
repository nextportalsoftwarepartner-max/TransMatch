/**
 * Parity check against the original Python extraction.
 *
 *   pnpm --filter @transmatch/extraction parity <reference-dir> <pdf-dir> [--ml]
 *
 * <reference-dir> holds the JSON files written by make_groundtruth.py (one per
 * PDF). For every PDF this compares the detected bank, the header details and
 * each transaction row, and prints the differences.
 */
import { readFileSync, readdirSync } from 'node:fs';
import { join } from 'node:path';
import {
  createEmbeddingNameExtractor,
  createTransformersEmbedder,
  detectBank,
  extractStatement,
  ExtractionError,
  shutdownOcr,
  type EmbeddingNameExtractor,
  type StatementInfo,
  type StatementTransaction,
} from '../src/index.js';

const [referenceDir, pdfDir] = process.argv.slice(2).filter((a) => !a.startsWith('--'));
const useMl = process.argv.includes('--ml');
if (!referenceDir || !pdfDir) {
  console.error('usage: parity <reference-dir> <pdf-dir> [--ml]');
  process.exit(2);
}

const INFO_KEYS: Array<[string, keyof StatementInfo]> = [
  ['Bank Name', 'bankName'],
  ['Bank Registration No', 'bankRegistrationNo'],
  ['Bank Address', 'bankAddress'],
  ['Customer Name', 'customerName'],
  ['Customer Address', 'customerAddress'],
  ['Statement Date', 'statementDate'],
  ['Account Number', 'accountNumber'],
];
const TRX_KEYS: Array<[string, keyof StatementTransaction]> = [
  ['trn_pdf_date', 'date'],
  ['trn_pdf_description', 'description'],
  ['trn_pdf_description_others', 'descriptionOthers'],
  ['trn_pdf_ner', 'targetName'],
  ['trn_pdf_CR_Amount', 'creditAmount'],
  ['trn_pdf_DR_Amount', 'debitAmount'],
  ['trn_pdf_statementBalance', 'statementBalance'],
];

let embeddingNameExtractor: EmbeddingNameExtractor | null = null;
if (useMl) embeddingNameExtractor = createEmbeddingNameExtractor(await createTransformersEmbedder());

let filesOk = 0;
let filesDiff = 0;

for (const file of readdirSync(referenceDir).filter((f) => f.endsWith('.json'))) {
  const ref = JSON.parse(readFileSync(join(referenceDir, file), 'utf8'));
  const pdf = readFileSync(join(pdfDir, ref.file));
  const problems: string[] = [];

  const detection = await detectBank(pdf);
  if (detection.bankId !== ref.bank_id) {
    problems.push(`bank id ${detection.bankId} != ${ref.bank_id} (header: ${JSON.stringify(detection.headerText.slice(0, 80))})`);
  }

  const refHasData = ref.doc && !ref.doc.error && Array.isArray(ref.trx);
  let rows = 0;
  try {
    // Use the reference bank id so a detection difference does not hide parser differences
    const result = await extractStatement(pdf, { bankId: ref.bank_id, embeddingNameExtractor });
    rows = result.transactions.length;
    if (!refHasData) {
      problems.push(`extracted ${rows} rows where the reference had an error`);
    } else {
      for (const [refKey, key] of INFO_KEYS) {
        if (result.info[key] !== ref.doc[refKey]) {
          problems.push(`info.${key}: ${JSON.stringify(result.info[key])} != ${JSON.stringify(ref.doc[refKey])}`);
        }
      }
      if (rows !== ref.trx.length) problems.push(`row count ${rows} != ${ref.trx.length}`);
      const perKey = new Map<string, number>();
      for (let i = 0; i < Math.min(rows, ref.trx.length); i++) {
        for (const [refKey, key] of TRX_KEYS) {
          if (result.transactions[i][key] !== ref.trx[i][refKey]) {
            const n = (perKey.get(key) ?? 0) + 1;
            perKey.set(key, n);
            if (n <= 3) {
              problems.push(
                `row ${i} ${key}: ${JSON.stringify(result.transactions[i][key])} != ${JSON.stringify(ref.trx[i][refKey])}`,
              );
            }
          }
        }
      }
      for (const [key, n] of perKey) if (n > 3) problems.push(`... ${key}: ${n} rows differ in total`);
    }
  } catch (err) {
    if (!(err instanceof ExtractionError)) throw err;
    if (refHasData) problems.push(`${err.code}: ${err.message}`);
  }

  if (problems.length === 0) {
    filesOk++;
    console.log(`OK    ${ref.file}  bank ${ref.bank_id}  rows ${rows}`);
  } else {
    filesDiff++;
    console.log(`DIFF  ${ref.file}  bank ${ref.bank_id}`);
    for (const p of problems) console.log(`        ${p}`);
  }
}

console.log(`\n${filesOk} file(s) match, ${filesDiff} differ`);
await shutdownOcr();
process.exit(filesDiff === 0 ? 0 : 1);
