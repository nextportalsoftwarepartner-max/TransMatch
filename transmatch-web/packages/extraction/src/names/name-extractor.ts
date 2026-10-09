import type { EmbeddingNameExtractor } from '../types.js';
import { titleCase } from '../util/text.js';

// Matches at the very end of the text, or just before a single trailing newline.
const END = '(?=\\n?$)';

function firstGroup(text: string, pattern: RegExp): string | null {
  const match = pattern.exec(text);
  return match ? match[1].trim() : null;
}

/**
 * Single-pass name extraction used by the Public Bank and Maybank templates.
 * Returns the first pattern that matches, without any filtering.
 */
export function extractNameBasic(input: string): string | null {
  const text = input.toUpperCase();
  const patterns: RegExp[] = [
    // DuitNow
    /DR \d+ ([A-Z &.]+) FROM/,
    // A/C pattern
    /A\/C ([A-Z &.]+)/,
    // FR A/ pattern with number+* before name
    /FR\s+A\/\s*\S+\s*\*?\s+([A-Z &.]+)/,
    // FPX PAYMENT FR A/ pattern
    /FPX PAYMENT\s+FR\s+A\/\s*\S+\s*\*?\s+([A-Z][A-Z &.]+(?:\s+[A-Z][A-Z &.]+)*)/,
    // PAYMENT VIA MYDEBIT pattern
    /PAYMENT VIA MYDEBIT\s+([A-Z0-9 ()-]+?)(?=\*|PAYMENT VIA)/,
    // DEBIT ADVICE pattern
    /DEBIT ADVICE\s+([A-Z0-9 &.-]+)\s*\*/,
    // FUND TRANSFER TO A/ pattern
    /FUND TRANSFER TO A\/\s+([A-Z ]+?)\s*\*/,
    // SALE DEBIT pattern
    /SALE DEBIT\s+([A-Z0-9 -]+?)\s*\*/,
    // After masked XXXXXX pattern
    /XXXXXX\s*([A-Z &.]+)/,
    // After card number pattern
    /\d{10,}&*\s*([A-Z &.]+)/,
    // Last fallback: after last number block
    new RegExp(`(?:\\d{4,}\\s+)?([A-Z][A-Z &.]{3,})${END}`),
    // Generic fallback: likely company name before a long reference ID
    /([A-Z0-9 &.()-]{5,})\s+[A-Z0-9]{10,}/,
  ];
  for (const pattern of patterns) {
    const found = firstGroup(text, pattern);
    if (found !== null) return found;
  }
  return null;
}

// ---- Individual extractors, tried in order by extractName() ----

type Extractor = (text: string) => string | null;

const fromDuitNow1: Extractor = (text) => firstGroup(text, /DR\s+\d+\s+([A-Z &.]+)\s+FROM/);

const fromDuitNow2: Extractor = (input) => {
  const text = input.toUpperCase();
  if (!text.includes('DUITNOW QR')) return null;
  return (
    firstGroup(text, /DUITNOW QR QR PAYMENT\s+([A-Z ]{3,40})/) ??
    firstGroup(text, /DUITNOW QR\s+([A-Z ]{3,40})\s+\d{20,}/) ??
    firstGroup(text, /DUITNOW QR\s+([A-Z ]{3,40})/)
  );
};

/**
 * DuitNow instant transfers where the name sits on its own line below the
 * transfer type, e.g. "DuitNow/Instant Trf / Goods Payment / Guruvayurapa Enterprise".
 */
const fromDuitNow3: Extractor = (input) => {
  const text = input.toUpperCase().replaceAll('|', ' ');
  const lines = text
    .split('\n')
    .map((ln) => ln.trim())
    .filter(Boolean);

  for (let i = 0; i < lines.length; i++) {
    if (!/DUITNOW[\s/-]*INSTANT\s*TRF/.test(lines[i])) continue;
    const buffer = lines.slice(i + 1, i + 7).filter((ln) => /^[A-Z0-9 ()./-]+$/.test(ln) && ln.length >= 3);
    const match =
      /([A-Z][A-Z0-9 &.']{2,}?\s+(?:SDN\.?\s*BHD?|ENTERPRISE|TRADING|SERVICES|RESOURCES|PLT))/.exec(
        buffer.join(' '),
      );
    if (match) return titleCase(match[1]);
  }
  return null;
};

const fromAccountFormat: Extractor = (text) => firstGroup(text, /A\/C\s+([A-Z &.]+)/);

const fromFrA: Extractor = (text) => firstGroup(text, /FR\s+A\/\s*\S+\s*\*?\s+([A-Z &.]+)/);

const fromFpx: Extractor = (text) =>
  firstGroup(text, /FPX PAYMENT\s+FR\s+A\/\s*\S+\s*\*?\s+([A-Z][A-Z &.]+(?:\s+[A-Z][A-Z &.]+)*)/);

const fromMyDebit1: Extractor = (text) =>
  firstGroup(text, /PAYMENT VIA MYDEBIT\s+([A-Z0-9 ()-]+?)(?=\*|PAYMENT VIA)/);

// Merchant name appearing after the amount lines for MyDebit
const fromMyDebit2: Extractor = (text) =>
  firstGroup(text, /MYDEBIT.*?(?:\n|\s+)([A-Z0-9\- ]{3,40}\(?[A-Z0-9\- ]*\(?)/) ??
  firstGroup(text, /MYDEBIT\s+[\d,.]+\s+[\d,.]+\s+([A-Z0-9\- ]{3,40})/);

const fromDebitAdvice: Extractor = (text) => firstGroup(text, /DEBIT ADVICE\s+([A-Z0-9 &.-]+)\s*\*/);

const fromFundTransfer: Extractor = (input) => {
  const text = input.toUpperCase();
  if (!text.includes('FUND TRANSFER')) return null;
  return (
    firstGroup(text, /FUND TRANSFER TO A\/\s+([A-Z ]+?)\s*\*/) ??
    firstGroup(text, /FUND TRANSFER\s+([A-Z ]{3,40})\s+\d{8}[A-Z]{8,}/) ??
    firstGroup(text, /FUND TRANSFER\s+([A-Z ]{3,40})\s+[A-Z0-9]{20,}/) ??
    firstGroup(text, /FUND TRANSFER\s+[A-Z0-9]{8,}\s+([A-Z ]{2,})\s*(?=\d{8}[A-Z0-9]{10,})/) ??
    firstGroup(
      text.replaceAll('\n', ' '),
      /FUND TRANSFER\s+([A-Z ]{3,40})\s+(?:[A-Z0-9_ ]{5,40})?\s+([0-9]{8}[A-Z]{8,})/,
    ) ??
    firstGroup(text, /FUND TRANSFER\s+[A-Z0-9]{8,}\s+([A-Z&. ]{5,60})\s+\d{8}[A-Z0-9]{10,}/)
  );
};

const fromSaleDebit: Extractor = (text) => firstGroup(text, /SALE DEBIT\s+([A-Z0-9 -]+?)\s*\*/);

const fromMasked: Extractor = (text) => firstGroup(text, /XXXXXX\s*([A-Z &.]+)/);

const fromCardNumber: Extractor = (text) => firstGroup(text, /\d{10,}&*\s*([A-Z &.]+)/);

const fromInstantTransfer: Extractor = (input) => {
  const text = input.toUpperCase();
  if (!text.includes('INSTANT TRANSFER AT KLM')) return null;
  return (
    firstGroup(
      text,
      /INSTANT TRANSFER AT KLM(?:\s+\d+\.\d{2}){0,2}\s+(?![A-Z0-9]*\d)([A-Z ]{3,60})(?=\d{8}[A-Z0-9]{10,})/,
    ) ??
    firstGroup(text, /\b[A-Z0-9]{8,}\s+([A-Z ]{3,40})\s+\d{8}[A-Z0-9]{10,}/) ??
    firstGroup(text, /DUITNOW QR\s+.+?\s+([A-Z &.]{3,60})(?=\s*\d{8}[A-Z0-9]{10,})/) ??
    firstGroup(
      text,
      /INSTANT TRANSFER AT KLM(?:\s+[A-Z0-9_.]{3,})*?\s+((?:[A-Z]+(?:\s+|$)){2,})(?=\d{8}[A-Z0-9]{10,})/,
    )
  );
};

const fromGeneric: Extractor = (text) =>
  firstGroup(text, new RegExp(`(?:\\d{4,}\\s+)?([A-Z][A-Z &.]{3,})${END}`));

const fromFallback: Extractor = (text) => firstGroup(text, /([A-Z0-9 &.()-]{5,})\s+[A-Z0-9]{10,}/);

const EXTRACTORS: Extractor[] = [
  fromDuitNow1,
  fromDuitNow2,
  fromDuitNow3,
  fromAccountFormat,
  fromFrA,
  fromFpx,
  fromMyDebit1,
  fromMyDebit2,
  fromDebitAdvice,
  fromFundTransfer,
  fromSaleDebit,
  fromMasked,
  fromCardNumber,
  fromInstantTransfer,
  fromGeneric,
  fromFallback,
];

// Generic transaction terms that must never be returned as a name
const GENERIC_TRANSACTION_TERMS = new Set([
  'DR',
  'CR',
  'CDM',
  'CASH DEPOSIT',
  'CASH DEP',
  'CHEQUE DEPOSIT',
  'CHEQUE',
  'DUITNOW',
  'INSTANT TRF',
  'DUITNOW/INSTANT TRF',
  'DUITNOW/INSTANT',
  'TRADE BILL',
  'TRADE BILL TRANSFER',
  'BILL TRANSFER',
  'TRANSFER',
  'PAYMENT',
  'DEPOSIT',
  'WITHDRAWAL',
  'MISC DR',
  'MISC CR',
  'MISC',
  'IBG',
  'FPX',
  'MYDEBIT',
  'ONLINE TRANSFER',
  'GOODS PAYMENT',
  'INSTANT TRANSFER',
]);

const GENERIC_WORDS = new Set(['DR', 'CR', 'TRANSFER', 'BILL', 'TRADE']);

export function isGenericTransactionTerm(result: string | null): boolean {
  if (!result) return true;
  const upper = result.toUpperCase().trim();

  if (GENERIC_TRANSACTION_TERMS.has(upper)) return true;

  for (const term of GENERIC_TRANSACTION_TERMS) {
    if (upper.startsWith(term + ' ') || upper === term) return true;
  }

  // Mostly generic terms, e.g. "DR 252BA103127 TRADE BILL TRANSFER"
  const parts = upper.split(/\s+/).filter(Boolean);
  const genericCount = parts.filter((w) => GENERIC_TRANSACTION_TERMS.has(w) || GENERIC_WORDS.has(w)).length;
  if (parts.length > 0 && genericCount >= parts.length * 0.5) return true;

  // "DR 252BA103127", "CDM CASH DEPOSIT"
  if (/^(DR|CR|CDM|MISC)\s+/.test(upper)) return true;
  if (/\b(TRADE\s+BILL|CASH\s+DEPOSIT|CASH\s+DEP|CHEQUE\s+DEPOSIT)\b/.test(upper)) return true;

  // Just a reference number, e.g. "252BA103127"
  if (/^[A-Z0-9]{8,}$/.test(upper.replaceAll(' ', ''))) return true;

  return false;
}

/** Pattern-based name extraction with generic transaction terms filtered out. */
export function extractName(input: string): string | null {
  const text = input.toUpperCase().trim();
  for (const extractor of EXTRACTORS) {
    const result = extractor(text);
    if (result && !isGenericTransactionTerm(result)) return result;
  }
  return null;
}

/**
 * Embedding-based extraction when an extractor is supplied, otherwise (or when
 * it finds nothing) the pattern-based result.
 */
export async function extractNameSmart(
  text: string,
  embeddingExtractor?: EmbeddingNameExtractor | null,
): Promise<string | null> {
  if (embeddingExtractor) {
    try {
      const found = await embeddingExtractor(text);
      if (found) return found.trim();
    } catch {
      // fall through to the pattern-based extraction
    }
  }
  return extractName(text)?.trim() ?? null;
}
