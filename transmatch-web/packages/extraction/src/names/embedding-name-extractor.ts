/**
 * Embedding-based extraction of the merchant / beneficiary name from a
 * transaction description.
 *
 * - Strong rule-based shortcuts run first (multi-line company names, repeated
 *   company blocks, Malay person-name markers, simple person names).
 * - Otherwise candidate phrases are generated, pre-scored heuristically, and
 *   the best one is chosen by similarity to "organisation" / "person"
 *   prototypes versus "noise" prototypes.
 */
import type { EmbeddingNameExtractor } from '../types.js';
import { isDigits, stripChars, words } from '../util/text.js';

/** Returns one L2-normalised embedding per input text. */
export type Embedder = (texts: string[]) => Promise<number[][]>;

// ---- Prototypes ----

const ORG_PROTOTYPES = [
  'TNG DIGITAL SDN BHD',
  'JAYA GROCER SDN BHD',
  'MR DIY SDN BHD',
  'STARBUCKS COFFEE',
  'TESCO EXTRA',
  'JERRY DISTRIBUTORS SDN BHD',
  'GURUVAYURAPA ENTERPRISE',
  'LAZADA MALAYSIA',
  'SHOPEE PAY',
  'AEON BIG SDN BHD',
  'PET BOSS CENTRE',
  'MBB PET BOSS CENTRE CASH AND CARRY SDN BHD',
  'PASARAYA SEJATI TANJUNG GADING SDN BHD',
  'EB VENTRA CAPITAL PRIVATE P/L',
  'VENTRA CAPITAL PRIVATE LIMITED',
  'ABC CAPITAL PRIVATE P/L',
  'XYZ VENTURE CAPITAL PRIVATE LIMITED',
  'DEF GROUP PRIVATE P/L',
];

const PERSON_PROTOTYPES = [
  // Malay names with markers
  'AHMAD BIN ALI',
  'SITI NURHALIZA BINTI TARUDIN',
  'FAUZIAH BINTI KAMARU',
  'MOHAMAD BIN HASSAN',
  'NOR AZIZAH BINTI ABDULLAH',
  'KESAVAN A/L GUNASEKAREN',
  'RAJESWARI A/P RAMASAMY',
  // Chinese names
  'CHIAN WEILON',
  'TAN AH QIONG',
  'LEE CHONG WEI',
  'LIM SIEW HONG',
  'WONG KAH MING',
  'CHEN WEI LING',
  // Indian names
  'KUMAR A/L MURUGAN',
  'PRIYA A/P DEVI',
  // Simple person names (2-3 words, no markers)
  'JOHN SMITH',
  'MARY TAN',
  'DAVID LEE',
  'SARAH LIM',
  'MICHAEL WONG',
  'LISA CHEN',
];

const NOISE_PROTOTYPES = [
  'ONLINE TRANSFER 1234567890',
  'DUITNOW INSTANT TRF 1234567890123456',
  'DuitNow/Instant Trf',
  'DuitNow/Instant',
  'FPX PAYMENT REF 1234567890123456',
  'CARD NO 123456XXXXXX9876',
  'REFERENCE 1029384756',
  'REF 998877665544332211',
  'PAYMENT VIA MYDEBIT 123456',
  'FUND TRANSFER TO A/C 123456789012',
  'IBG 1234567890',
  'BALANCE FROM LAST STATEMENT',
  'CLOSING BALANCE IN THIS STATEMENT',
];

// ---- Keyword sets ----

const ORG_KEYWORDS = new Set([
  'SDN BHD', 'SDN', 'BHD', 'BERHAD', 'TRADING', 'ENTERPRISE', 'RESOURCES',
  'MARKETING', 'SERVICES', 'SERVICE', 'HOLDINGS', 'MANAGEMENT',
  'DISTRIBUTOR', 'DISTRIBUTORS', 'GLOBAL', 'INDUSTRIES', 'PLT',
  'SDN.', 'BHD.', 'BHD,', 'SDN,', 'CO.,LTD', 'SUPPLIES',
  'PRIVATE', 'P/L', 'PRIVATE P/L', 'PRIVATE LIMITED', 'LTD', 'LIMITED',
  'CAPITAL', 'VENTURE', 'GROUP', 'CORPORATION', 'CORP',
]);

// Person-name markers (Malay style etc.)
const PERSON_MARKERS = new Set(['BIN', 'BINTI', 'BT', 'BTE', 'A/L', 'A/P']);

const EXCLUDE_KEYWORDS = new Set([
  'DUITNOW', 'INSTANT', 'TRF', 'TRANSFER', 'PAYMENT', 'GOODS', 'QR',
  'ONLINE', 'IBG', 'FPX', 'DEBIT', 'CREDIT', 'CARD', 'VIA', 'CASH',
  'REF', 'REFERENCE', 'NO', 'NO.', 'A/C', 'ACCOUNT', 'BALANCE',
  'STATEMENT', 'DATE', 'FROM', 'TO', 'MBB', 'PBB', 'CIMB', 'OCBC',
  'UOB', 'AFFIN', 'RHB', 'HLB', 'BSN', 'AMBANK', 'AMBG', 'AGRO',
  // Generic transaction terms
  'MISC', 'DR', 'CR', 'CDM', 'CHEQUE', 'DEPOSIT', 'WITHDRAWAL',
  'MAY', 'JUN', 'JUL', 'AUG', 'SEP', 'OCT', 'NOV', 'DEC', 'JAN', 'FEB', 'MAR', 'APR',
  'BULAN', 'YEAR', '2024', '2023', '2025',
  'INV', 'INVOICE', 'BILL', 'TRADE', 'BILL TRANSFER',
  'DEP',
]);

// Complete phrases that are never a name
const EXCLUDE_PHRASES = [
  'DUITNOW/INSTANT', 'DUITNOW/INSTANT TRF', 'DUITNOW INSTANT', 'DUITNOW INSTANT TRF',
  'INSTANT TRF', 'INSTANT TRANSFER', 'GOODS PAYMENT',
  'TRADE BILL', 'TRADE BILL TRANSFER', 'CASH DEPOSIT', 'CASH DEP',
  'CHEQUE DEPOSIT', 'CDM CASH DEPOSIT',
];
const EXCLUDE_PHRASE_SET = new Set(EXCLUDE_PHRASES);

// Bank codes that are stripped from company names
const BANK_CODES = new Set([
  'AMBG', 'MBB', 'PBB', 'CIMB', 'OCBC', 'UOB', 'AFFIN', 'RHB', 'HLB', 'BSN', 'AMBANK', 'AGRO',
]);

const GENERIC_TERMS = new Set([
  'DR', 'CR', 'CDM', 'CASH', 'DEPOSIT', 'DEP', 'CHEQUE',
  'DUITNOW', 'INSTANT', 'TRF', 'TRANSFER', 'TRADE', 'BILL',
  'MISC', 'PAYMENT', 'GOODS',
]);

// ---- Small predicates ----

function isMostlyDigits(input: string): boolean {
  const s = input.replaceAll(' ', '').replaceAll('-', '').replaceAll('/', '');
  return isDigits(s) || /^[0-9X]+$/.test(s);
}

function looksLikeAmountOrDate(input: string): boolean {
  const s = input.trim();
  // Amount like 1,234.56
  if (/^[\d,]+\.\d{2}$/.test(s)) return true;
  // Date like 01/06/2024 or 06-06-2024
  return /^\d{1,2}[-/]\d{1,2}([-/]\d{2,4})?$/.test(s);
}

/**
 * Rough heuristic for romanised person names such as "TAN AH QIONG":
 * 2-4 purely alphabetic tokens, none of them an organisation or noise word.
 */
export function looksLikePersonName(upper: string): boolean {
  const tokens = words(upper);
  if (tokens.length < 2 || tokens.length > 4) return false;
  if (tokens.some((t) => ORG_KEYWORDS.has(t) || EXCLUDE_KEYWORDS.has(t))) return false;
  if (tokens.some(isMostlyDigits)) return false;
  return tokens.every((t) => /^[A-Z]{2,}$/.test(t));
}

const ORG_FRAGMENTS_WIDE = ['SDN', 'BHD', 'PRIVATE', 'P/L', 'LTD', 'CAPITAL', 'VENTURE', 'GROUP', 'ENTERPRISE'];
const ORG_FRAGMENTS = ['SDN', 'BHD', 'PRIVATE', 'P/L', 'LTD', 'CAPITAL'];
const ORG_FRAGMENTS_NARROW = ['PRIVATE', 'P/L', 'LTD', 'ENTERPRISE'];

const containsAny = (word: string, fragments: string[]) => fragments.some((f) => word.includes(f));
const sameTokens = (a: string[], b: string[]) => a.length === b.length && a.every((t, i) => t === b[i]);
const nonEmptyLines = (text: string) =>
  text
    .split('\n')
    .map((ln) => ln.trim())
    .filter(Boolean);

function dropTrailingReferences(parts: string[]): string[] {
  const out = [...parts];
  while (out.length > 0 && isMostlyDigits(out[out.length - 1])) out.pop();
  return out;
}

// ---- Rule-based shortcuts ----

/**
 * Company names that span several lines, e.g.
 *   MAY 2024 PAYMENT | YOR406070377C01 | EB VENTRA CAPITAL | PRIVATE P/L
 * -> "EB VENTRA CAPITAL PRIVATE P/L"
 */
function extractMultilineCompanyName(input: string): string | null {
  if (!input) return null;
  const lines = nonEmptyLines(input.replaceAll('|', '\n'));
  if (lines.length < 2) return null;

  const companyLines: Array<[number, string]> = [];
  lines.forEach((line, i) => {
    const lineUpper = line.toUpperCase();
    const tokens = words(lineUpper);

    // Lines that are only noise words or numbers
    if (tokens.every((w) => EXCLUDE_KEYWORDS.has(w) || isMostlyDigits(w))) return;
    // Lines that start with a noise word (e.g. "DUITNOW/INSTANT TRF GOODS PAYMENT")
    if (tokens.length > 0 && EXCLUDE_KEYWORDS.has(tokens[0])) return;

    const hasOrgKeyword = tokens.some((w) => ORG_KEYWORDS.has(w));
    const hasOrgPattern = tokens.some((w) => containsAny(w, ORG_FRAGMENTS_WIDE));
    const looksLikeCompanyPart =
      tokens.length >= 2 &&
      tokens.length <= 6 &&
      !tokens.some((w) => EXCLUDE_KEYWORDS.has(w)) &&
      !isMostlyDigits(lineUpper);

    if (hasOrgKeyword || hasOrgPattern || looksLikeCompanyPart) {
      const filtered = tokens.filter((w) => !EXCLUDE_KEYWORDS.has(w) && !isMostlyDigits(w));
      if (filtered.length > 0) companyLines.push([i, filtered.join(' ')]);
    }
  });

  if (companyLines.length < 1) return null;

  if (companyLines.length >= 2) {
    const indices = companyLines.map(([idx]) => idx);
    if (Math.max(...indices) - Math.min(...indices) <= 3) {
      let parts = words(companyLines.map(([, line]) => line).join(' '));
      parts = parts.filter((p) => !BANK_CODES.has(p));
      parts = dropTrailingReferences(parts);
      parts = parts.filter((p) => !EXCLUDE_KEYWORDS.has(p));

      // Cut at the first repeated phrase (e.g. "X ENTERPRISE X ENTERPRISE")
      if (parts.length >= 4) {
        const deduplicated: string[] = [];
        const seenPhrases = new Set<string>();
        for (let i = 0; i < parts.length; i++) {
          let isRepeat = false;
          for (let len = 2; len < Math.min(6, parts.length - i + 1); len++) {
            const phrase = parts.slice(i, i + len).join(' ');
            if (seenPhrases.has(phrase)) {
              isRepeat = true;
              break;
            }
            if (i + len < parts.length && phrase === parts.slice(i + len, i + len * 2).join(' ')) {
              isRepeat = true;
              seenPhrases.add(phrase);
              break;
            }
          }
          if (isRepeat) break;
          deduplicated.push(parts[i]);
        }
        parts = deduplicated;
      }

      const result = parts.join(' ').trim();
      const resultWords = words(result);
      const excludedCount = resultWords.filter((w) => EXCLUDE_KEYWORDS.has(w)).length;
      if (excludedCount >= resultWords.length * 0.3) return null;
      if (result.length >= 5) return result;
    }
  }

  // A single company line followed by a line carrying a company keyword
  if (companyLines.length === 1) {
    const [idx, line] = companyLines[0];
    if (idx + 1 < lines.length) {
      const nextWords = words(lines[idx + 1].trim().toUpperCase()).filter(
        (w) => !EXCLUDE_KEYWORDS.has(w) && !isMostlyDigits(w),
      );
      if (
        nextWords.length > 0 &&
        (nextWords.some((w) => ORG_KEYWORDS.has(w)) || nextWords.some((w) => containsAny(w, ORG_FRAGMENTS_NARROW)))
      ) {
        let parts = words(`${line} ${nextWords.join(' ')}`.trim());
        parts = parts.filter((p) => !BANK_CODES.has(p));
        parts = dropTrailingReferences(parts);
        const result = parts.join(' ').trim();
        if (result.length >= 5) return result;
      }
    }
  }

  return null;
}

/**
 * Cleans up a company name: drops bank codes and noise words and removes
 * repeated halves. Returns "" when nothing meaningful is left.
 *
 *   "AMBG GURUVAYURAPA ENTERPRISE AMBG GURUVAYURAPA ENTERPRISE" -> "GURUVAYURAPA ENTERPRISE"
 *   "DUITNOW/INSTANT" -> ""
 */
export function cleanCompanyName(name: string): string {
  if (!name) return name;
  const upper = name.toUpperCase().trim();

  if (EXCLUDE_PHRASE_SET.has(upper)) return '';
  for (const phrase of EXCLUDE_PHRASES) {
    if (upper.startsWith(phrase)) return '';
    // Mostly just the excluded phrase
    if (upper.includes(phrase) && upper.length <= phrase.length + 5) return '';
  }

  let tokens = words(upper).filter((w) => !BANK_CODES.has(w) && !EXCLUDE_KEYWORDS.has(w));

  // Drop token runs that spell out an excluded phrase
  const filtered: string[] = [];
  let i = 0;
  while (i < tokens.length) {
    let matched = false;
    for (const phrase of EXCLUDE_PHRASES) {
      const phraseWords = words(phrase.replaceAll('/', ' '));
      if (
        i + phraseWords.length <= tokens.length &&
        sameTokens(tokens.slice(i, i + phraseWords.length), phraseWords)
      ) {
        i += phraseWords.length;
        matched = true;
        break;
      }
    }
    if (matched) continue;
    if (tokens[i].includes('/') && ['DUITNOW/INSTANT', 'DUITNOW/INSTANT/TRF'].includes(tokens[i])) {
      i += 1;
      continue;
    }
    filtered.push(tokens[i]);
    i += 1;
  }
  tokens = filtered;
  if (tokens.length === 0) return '';

  if (tokens.length >= 4) {
    // "X Y X Y" or "X Y Z X Y Z": keep the first occurrence
    for (let len = Math.min(4, Math.floor(tokens.length / 2)); len > 0; len--) {
      if (len * 2 > tokens.length) continue;
      if (sameTokens(tokens.slice(0, len), tokens.slice(len, len * 2))) {
        return tokens.slice(0, len).join(' ');
      }
    }
    // A trailing run that already appeared earlier is a duplicate
    for (let suffixLen = 1; suffixLen < Math.min(5, Math.floor(tokens.length / 2)); suffixLen++) {
      const suffix = tokens.slice(-suffixLen);
      for (let j = 0; j < tokens.length - suffixLen * 2; j++) {
        if (sameTokens(tokens.slice(j, j + suffixLen), suffix)) {
          return tokens.slice(0, -suffixLen).join(' ');
        }
      }
    }
  }

  const result = tokens.join(' ').trim();
  if (result.length < 3) return '';
  if (EXCLUDE_PHRASE_SET.has(result.toUpperCase())) return '';
  return result;
}

/**
 * Company name repeated twice, where the first block may be truncated:
 *   PBB PET BOSS CENTRE CASH AND CARRY / PBB PET BOSS CENTRE CASH AND CARRY SDN BHD
 * -> "PET BOSS CENTRE CASH AND CARRY SDN BHD"
 */
function extractRepeatedOrgName(input: string): string | null {
  if (!input) return null;
  const upper = words(input.toUpperCase().replaceAll('|', ' ')).join(' ');
  const rawTokens = words(upper)
    .map((t) => stripChars(t, ',.'))
    .filter(Boolean);
  if (rawTokens.length === 0) return null;

  // Remove noise: transfer words, bank codes, anything carrying digits
  const cleaned = rawTokens.filter((t) => !EXCLUDE_KEYWORDS.has(t) && !BANK_CODES.has(t) && !/\d/.test(t));
  if (cleaned.length < 4) return null;

  const n = cleaned.length;
  // [block][block][tail...]: take the second block, which is the more complete one
  for (let k = Math.floor(n / 2); k > 1; k--) {
    if (2 * k > n) continue;
    const block2 = cleaned.slice(k, 2 * k);
    if (!sameTokens(cleaned.slice(0, k), block2)) continue;

    const base = [...block2];
    const tail = cleaned.slice(2 * k);
    if (tail.includes('SDN') && tail.includes('BHD')) base.push('SDN', 'BHD');

    if (base.length >= 3) {
      const resultWords = base.filter((w) => !BANK_CODES.has(w));
      if (resultWords.length >= 3) return resultWords.join(' ');
    }
  }
  return null;
}

/** Malay-style person names: "... FAUZIAH BINTI KAMARU ..." -> "FAUZIAH BINTI KAMARU". */
function extractPersonMarkerName(input: string): string | null {
  if (!input) return null;
  const tokens = words(input.toUpperCase().replaceAll('|', ' '));

  for (let idx = 0; idx < tokens.length; idx++) {
    const tok = tokens[idx];
    if (!PERSON_MARKERS.has(tok)) continue;
    // Need a token before and after the marker
    if (idx === 0 || idx + 1 >= tokens.length) continue;

    let before = tokens[idx - 1];
    const after = tokens[idx + 1];

    // "AGRO FAUZIAH BINTI KAMARU": step past a leading noise word
    if (EXCLUDE_KEYWORDS.has(before) && idx - 2 >= 0 && !EXCLUDE_KEYWORDS.has(tokens[idx - 2])) {
      before = tokens[idx - 2];
    }

    if (isMostlyDigits(before) || isMostlyDigits(after)) continue;

    const name = `${before} ${tok} ${after}`.trim();
    if (name.length >= 5) return name;
  }
  return null;
}

/** Plain 2-4 word person names in a clean context: "PAYMENT TO MARY TAN" -> "MARY TAN". */
function extractSimplePersonName(input: string): string | null {
  if (!input) return null;
  const tokens = words(input.toUpperCase().replaceAll('|', ' '));

  for (let i = 0; i < tokens.length - 1; i++) {
    for (const length of [2, 3, 4]) {
      if (i + length > tokens.length) continue;
      const candidate = tokens.slice(i, i + length).join(' ');
      if (!looksLikePersonName(candidate)) continue;

      const before = i > 0 ? tokens[i - 1] : '';
      const after = i + length < tokens.length ? tokens[i + length] : '';

      if (EXCLUDE_KEYWORDS.has(before) || EXCLUDE_KEYWORDS.has(after)) continue;

      if (
        (!before || isMostlyDigits(before) || ['TO', 'FROM', 'A/C', 'A/', 'FR'].includes(before)) &&
        (!after || isMostlyDigits(after) || after.length > 10)
      ) {
        return candidate;
      }
    }
  }
  return null;
}

// ---- Candidate generation ----

const LEADING_NOISE = ['DUITNOW', 'INSTANT', 'TRF', 'TRANSFER', 'PAYMENT', 'GOODS', 'ONLINE', 'IBG', 'FPX'];

/**
 * Generates candidate phrases from a raw description and returns the ten best
 * by a heuristic pre-score, ready to be ranked by the embedding model.
 */
export function generateCandidates(input: string): string[] {
  if (!input) return [];

  const text = input.replaceAll('|', '\n');
  const lines = nonEmptyLines(text);
  const candidates = new Set<string>();

  // 1) Whole lines
  for (const line of lines) {
    if (line.length < 3) continue;
    if (isMostlyDigits(line)) continue;
    if (looksLikeAmountOrDate(line)) continue;
    if (EXCLUDE_PHRASE_SET.has(line.toUpperCase().trim())) continue;

    const wordsUpper = words(line).map((w) => stripChars(w, ',.()').toUpperCase());
    if (wordsUpper.length > 0 && wordsUpper.every((w) => EXCLUDE_KEYWORDS.has(w))) continue;

    const cleanedLine = dropTrailingReferences(words(line)).join(' ').trim();
    if (EXCLUDE_PHRASE_SET.has(cleanedLine.toUpperCase())) continue;
    if (cleanedLine.length >= 3) candidates.add(cleanedLine);
  }

  // 1B) Consecutive lines that together look like a company name
  const hasOrgHint = (ws: string[]) =>
    ws.some((w) => ORG_KEYWORDS.has(w)) || ws.some((w) => containsAny(w, ORG_FRAGMENTS));
  const onlyNoise = (ws: string[]) => ws.every((w) => EXCLUDE_KEYWORDS.has(w) || isMostlyDigits(w));
  const addJoined = (joined: string) => {
    const combined = dropTrailingReferences(words(joined.trim())).join(' ').trim();
    if (combined.length >= 5) candidates.add(combined);
  };

  for (let i = 0; i < lines.length - 1; i++) {
    const line1 = lines[i].trim().toUpperCase();
    const line2 = lines[i + 1].trim().toUpperCase();
    if (line1.length < 3 || line2.length < 3) continue;

    const words1 = words(line1);
    const words2 = words(line2);
    const hasOrgKeyword = hasOrgHint(words1) || hasOrgHint(words2);
    const notOnlyNoise = !onlyNoise(words1) && !onlyNoise(words2);

    if (hasOrgKeyword && notOnlyNoise) addJoined(`${line1} ${line2}`);

    if (i + 2 < lines.length) {
      const line3 = lines[i + 2].trim().toUpperCase();
      if (line3.length >= 3) {
        const words3 = words(line3);
        if ((hasOrgKeyword || hasOrgHint(words3)) && notOnlyNoise && !onlyNoise(words3)) {
          addJoined(`${line1} ${line2} ${line3}`);
        }
      }
    }
  }

  // 2) Sliding windows of 2-6 tokens over the noise-free token stream
  const upperText = words(text).join(' ').toUpperCase();
  const tokens = words(upperText).filter((t) => !isMostlyDigits(t) && !EXCLUDE_KEYWORDS.has(t));
  for (let i = 0; i < tokens.length; i++) {
    for (let size = 2; size <= 6; size++) {
      if (i + size > tokens.length) break;
      const chunk = tokens.slice(i, i + size).join(' ');
      if (chunk.length < 3) continue;
      if (looksLikeAmountOrDate(chunk)) continue;
      candidates.add(chunk);
    }
  }

  // 3) Malay person names: one word before the marker, three after
  for (const line of lines) {
    const lineTokens = words(line.trim().toUpperCase());
    lineTokens.forEach((tok, idx) => {
      if (!PERSON_MARKERS.has(tok)) return;
      const personTokens = lineTokens.slice(Math.max(0, idx - 1), Math.min(lineTokens.length, idx + 4));
      if (personTokens.length >= 2) candidates.add(personTokens.join(' '));
    });
  }

  // 4) Uppercase spans, with leading transfer words peeled off
  for (const match of upperText.matchAll(/([A-Z][A-Z0-9&.\-/ ]{3,60})/g)) {
    let chunk = match[1].trim();
    if (EXCLUDE_PHRASE_SET.has(chunk.toUpperCase())) continue;

    let changed = true;
    while (changed) {
      changed = false;
      for (const kw of LEADING_NOISE) {
        if (chunk.startsWith(kw + ' ') || chunk.startsWith(kw + '/')) {
          chunk = chunk.slice(kw.length + 1).trim();
          changed = true;
          break;
        }
        if (chunk.includes('/') && chunk.toUpperCase().includes('DUITNOW') && chunk.toUpperCase().includes('INSTANT')) {
          const parts = chunk.split(/DUITNOW[/\s]*INSTANT[/\s]*/i);
          if (parts.length > 1) {
            chunk = parts[parts.length - 1].trim();
            changed = true;
            break;
          }
        }
      }
    }

    if (chunk.length >= 3 && !isMostlyDigits(chunk) && !EXCLUDE_PHRASE_SET.has(chunk.toUpperCase())) {
      candidates.add(chunk);
    }
  }

  // 5) De-duplicate case-insensitively and drop excluded phrases
  const seen = new Set<string>();
  const pruned: string[] = [];
  for (const cand of candidates) {
    const upper = cand.toUpperCase().trim();
    if (seen.has(upper)) continue;
    seen.add(upper);
    if (EXCLUDE_PHRASES.some((phrase) => upper.startsWith(phrase))) continue;
    pruned.push(cand);
  }

  // 6) Heuristic pre-score; keep the ten best non-negative candidates
  const scored = pruned.map((cand) => {
    const upper = cand.toUpperCase();
    const ws = words(upper);
    let score = 0;

    // Starts with generic transaction terms ("MISC", "DR", "MAY", ...)
    if (ws.length > 0 && EXCLUDE_KEYWORDS.has(ws[0])) score -= 15;
    if (ws.length >= 2 && EXCLUDE_KEYWORDS.has(ws[0]) && EXCLUDE_KEYWORDS.has(ws[1])) score -= 20;

    // Single word, unless it clearly looks like a company
    if (ws.length === 1) score -= 3;

    // Company indicators
    const orgCount = ws.filter((w) => ORG_KEYWORDS.has(w)).length;
    if (orgCount > 0) score += 5;
    if (orgCount >= 2) score += 3;

    // Person indicators
    if (ws.some((w) => PERSON_MARKERS.has(w))) score += 4;
    if (looksLikePersonName(upper)) score += 3;

    // Generic transaction terms
    const excludedCount = ws.filter((w) => EXCLUDE_KEYWORDS.has(w)).length;
    if (excludedCount > 0) score -= excludedCount * 3;
    if (excludedCount >= ws.length / 2) score -= 10;

    // Medium length (2-6 words) is ideal; very long is slightly penalised
    if (ws.length >= 2 && ws.length <= 6) score += 2;
    if (ws.length > 8) score -= 1;

    // At least one vowel: looks like a real name word
    if (/[AEIOU]/.test(upper)) score += 1;

    return { score, cand };
  });

  // Array.prototype.sort is stable, so ties keep generation order
  scored.sort((a, b) => b.score - a.score);
  return scored
    .filter((s) => s.score >= 0)
    .slice(0, 10)
    .map((s) => s.cand);
}

// ---- Main entry point ----

function dot(a: number[], b: number[]): number {
  let sum = 0;
  for (let i = 0; i < a.length; i++) sum += a[i] * b[i];
  return sum;
}

function cosineSimilarity(a: number[], b: number[]): number {
  if (a.length !== b.length) return 0;
  const normA = Math.sqrt(dot(a, a));
  const normB = Math.sqrt(dot(b, b));
  if (normA === 0 || normB === 0) return 0;
  return dot(a, b) / (normA * normB);
}

const meanSimilarity = (emb: number[], prototypes: number[][]) =>
  prototypes.length > 0 ? prototypes.reduce((sum, p) => sum + cosineSimilarity(emb, p), 0) / prototypes.length : 0;

/**
 * Builds a name extractor on top of an embedding model. Prototype embeddings
 * are computed once, on first use.
 */
export function createEmbeddingNameExtractor(embed: Embedder): EmbeddingNameExtractor {
  let prototypes: Promise<{ org: number[][]; person: number[][]; noise: number[][] }> | null = null;
  const loadPrototypes = () =>
    (prototypes ??= (async () => ({
      org: await embed(ORG_PROTOTYPES),
      person: await embed(PERSON_PROTOTYPES),
      noise: await embed(NOISE_PROTOTYPES),
    }))());

  return async (input: string): Promise<string | null> => {
    const text = (input ?? '').trim();
    if (!text) return null;

    // Rule-based shortcuts, strongest first
    const multiline = extractMultilineCompanyName(text);
    if (multiline) {
      const cleaned = cleanCompanyName(multiline);
      if (cleaned) return cleaned;
    }

    const repeated = extractRepeatedOrgName(text);
    if (repeated) {
      const cleaned = cleanCompanyName(repeated);
      if (cleaned) return cleaned;
    }

    const personMarker = extractPersonMarkerName(text);
    if (personMarker) return personMarker;

    const simplePerson = extractSimplePersonName(text);
    if (simplePerson) return simplePerson;

    // Embedding-based ranking
    const candidates = generateCandidates(text);
    if (candidates.length === 0) return null;

    const { org, person, noise } = await loadPrototypes();
    const embeddings = await embed(candidates);

    let best: string | null = null;
    let bestScore = -999;
    let bestIsPerson = false;

    for (let i = 0; i < candidates.length; i++) {
      const cand = candidates[i];
      const upper = cand.toUpperCase();
      const ws = words(upper);
      const isPerson =
        ws.some((w) => PERSON_MARKERS.has(w)) ||
        looksLikePersonName(upper) ||
        (ws.length >= 2 &&
          ws.length <= 4 &&
          ws.every((w) => /^[A-Z]{2,}$/.test(w)) &&
          !ws.some((w) => ORG_KEYWORDS.has(w) || EXCLUDE_KEYWORDS.has(w)));

      const simNoise = meanSimilarity(embeddings[i], noise);
      const score = (isPerson ? meanSimilarity(embeddings[i], person) : meanSimilarity(embeddings[i], org)) - simNoise;

      if (score > bestScore) {
        bestScore = score;
        best = cand;
        bestIsPerson = isPerson;
      }
    }

    // Person names match their prototypes less tightly, so the bar is lower
    const threshold = bestIsPerson ? 0.01 : 0.02;
    if (best === null || bestScore <= threshold) return null;

    const bestUpper = best.toUpperCase().trim();
    if (EXCLUDE_PHRASES.some((phrase) => bestUpper.startsWith(phrase))) return null;

    const bestWords = words(bestUpper);
    if (bestWords.length > 0 && GENERIC_TERMS.has(bestWords[0])) return null;
    const genericCount = bestWords.filter((w) => GENERIC_TERMS.has(w)).length;
    if (bestWords.length > 0 && genericCount >= bestWords.length * 0.5) return null;

    const cleaned = cleanCompanyName(best);
    return cleaned ? cleaned.trim() : null;
  };
}
