import type { PdfDocument } from '../pdf/pdf-document.js';
import type { EmbeddingNameExtractor, StatementInfo, StatementTransaction } from '../types.js';

export interface ParserContext {
  bankId: number;
  /** Leading portion of the document text, used for header details. */
  headText: string;
  /** Text of the whole document. */
  fullText: string;
  pdf: PdfDocument;
  embeddingNameExtractor?: EmbeddingNameExtractor | null;
}

export interface BankParser {
  extractInfo(ctx: ParserContext): StatementInfo;
  extractTransactions(ctx: ParserContext): Promise<StatementTransaction[]> | StatementTransaction[];
}
