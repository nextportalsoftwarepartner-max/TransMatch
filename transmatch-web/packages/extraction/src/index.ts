export { detectBank, extractStatement, type ExtractOptions } from './extract-statement.js';
export { normalizeStatement, parseStatementDate, resolveTransactionDate, type NormalizedStatement } from './normalize.js';
export {
  BANK_NOT_SUPPORTED,
  BANK_UNDEFINED,
  BANK_TEMPLATES,
  findBankTemplate,
  matchBank,
  supportedBankTemplates,
} from './banks/registry.js';
export { extractName, extractNameBasic, extractNameSmart, isGenericTransactionTerm } from './names/name-extractor.js';
export { createEmbeddingNameExtractor, type Embedder } from './names/embedding-name-extractor.js';
export { createTransformersEmbedder, type TransformersEmbedderOptions } from './names/transformers-embedder.js';
export { shutdownOcr } from './ocr/header-reader.js';
export {
  ExtractionError,
  type BankDetection,
  type EmbeddingNameExtractor,
  type ExtractionErrorCode,
  type ExtractionResult,
  type StatementInfo,
  type StatementTransaction,
  type TextEngine,
} from './types.js';
