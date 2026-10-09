/** Header details read from the first part of a statement, as printed on it. */
export interface StatementInfo {
  bankName: string;
  bankRegistrationNo: string;
  bankAddress: string;
  customerName: string;
  customerAddress: string;
  /** Raw statement date as the bank template yields it, e.g. "31/12/24". */
  statementDate: string;
  accountNumber: string;
}

/** One transaction row as extracted, before dates are normalised. */
export interface StatementTransaction {
  /** Raw date, e.g. "02/11", "02/11/24" or "06-06-2024" depending on the bank. */
  date: string;
  description: string;
  descriptionOthers: string;
  /** Counterparty name picked out of the description ("Target Audience"). */
  targetName: string;
  creditAmount: number;
  debitAmount: number;
  statementBalance: number;
}

export interface BankDetection {
  /** Template id; 98 = page could not be read, 99 = bank not recognised. */
  bankId: number;
  engine: TextEngine | null;
  /** Text read from the top strip of the first page. */
  headerText: string;
}

export type TextEngine = 'fitz' | 'pdfplumberxy_rhb';

export type ExtractionErrorCode =
  | 'BANK_UNDEFINED'
  | 'BANK_NOT_SUPPORTED'
  | 'TEMPLATE_NOT_AVAILABLE'
  | 'PARSE_FAILED';

export class ExtractionError extends Error {
  constructor(
    readonly code: ExtractionErrorCode,
    message: string,
    readonly bankId?: number,
  ) {
    super(message);
    this.name = 'ExtractionError';
  }
}

export interface ExtractionResult {
  bankId: number;
  bankTemplate: string;
  engine: TextEngine;
  info: StatementInfo;
  transactions: StatementTransaction[];
}

/** Picks a counterparty name using sentence embeddings; resolves null when unsure. */
export type EmbeddingNameExtractor = (text: string) => Promise<string | null>;
