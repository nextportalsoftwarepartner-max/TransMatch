import type { ParserContext } from './banks/parser.js';
import {
  BANK_NOT_SUPPORTED,
  BANK_UNDEFINED,
  engineForBank,
  findBankTemplate,
  matchBank,
} from './banks/registry.js';
import { readHeaderText } from './ocr/header-reader.js';
import { PdfDocument } from './pdf/pdf-document.js';
import {
  ExtractionError,
  type BankDetection,
  type EmbeddingNameExtractor,
  type ExtractionResult,
} from './types.js';

export interface ExtractOptions {
  /** Skip detection and read the statement with this bank template. */
  bankId?: number;
  /** Optional embedding-based name extractor (used by the UOB template). */
  embeddingNameExtractor?: EmbeddingNameExtractor | null;
}

// Header details are read from the leading part of the text: the first tenth
// of the document, and never less than 3000 characters.
const HEAD_MIN_CHARS = 3000;
const HEAD_FRACTION = 0.1;

/** Identifies the bank that issued a statement from its letterhead. */
export async function detectBank(pdfData: Uint8Array): Promise<BankDetection> {
  const pdf = PdfDocument.open(pdfData);
  try {
    return await detect(pdf);
  } finally {
    pdf.close();
  }
}

async function detect(pdf: PdfDocument): Promise<BankDetection> {
  const headerText = await readHeaderText(pdf);
  if (headerText === null) return { bankId: BANK_UNDEFINED, engine: null, headerText: '' };
  const bankId = matchBank(headerText);
  return { bankId, engine: bankId === BANK_NOT_SUPPORTED ? null : engineForBank(bankId), headerText };
}

/**
 * Extracts the header details and all transactions from a bank statement PDF.
 * Throws ExtractionError when the bank is unknown, has no template, or the
 * statement does not follow the template.
 */
export async function extractStatement(pdfData: Uint8Array, options: ExtractOptions = {}): Promise<ExtractionResult> {
  const pdf = PdfDocument.open(pdfData);
  try {
    const bankId = options.bankId ?? (await detect(pdf)).bankId;

    if (bankId === BANK_UNDEFINED) {
      throw new ExtractionError(
        'BANK_UNDEFINED',
        'The uploaded PDF could not be identified as a known bank statement.',
        bankId,
      );
    }
    const template = findBankTemplate(bankId);
    if (!template) {
      throw new ExtractionError(
        'BANK_NOT_SUPPORTED',
        'The uploaded bank statement is currently not supported.',
        bankId,
      );
    }
    if (!template.parser) {
      throw new ExtractionError(
        'TEMPLATE_NOT_AVAILABLE',
        `${template.name} statements are recognised, but no extraction template is available for them yet.`,
        bankId,
      );
    }

    const fullText = pdf.text();
    const ctx: ParserContext = {
      bankId,
      fullText,
      headText: fullText.slice(0, Math.max(HEAD_MIN_CHARS, Math.floor(fullText.length * HEAD_FRACTION))),
      pdf,
      embeddingNameExtractor: options.embeddingNameExtractor,
    };

    try {
      return {
        bankId,
        bankTemplate: template.name,
        engine: engineForBank(bankId),
        info: template.parser.extractInfo(ctx),
        transactions: await template.parser.extractTransactions(ctx),
      };
    } catch (err) {
      if (err instanceof ExtractionError) throw err;
      throw new ExtractionError(
        'PARSE_FAILED',
        `The statement does not match the ${template.name} template: ${(err as Error).message}`,
        bankId,
      );
    }
  } finally {
    pdf.close();
  }
}
