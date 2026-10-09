// Rules that flag a transaction against the blacklisted and suspicious name lists.

export type WatchStatus = 'BLACKLISTED' | 'BLACKLISTED_PARTIAL' | 'SUSPICIOUS' | 'NONE';

export interface WatchLists {
  /** Lower-cased, trimmed blacklisted names. */
  blacklisted: string[];
  /** Lower-cased, trimmed suspicious names. */
  suspicious: string[];
}

export function normalizeNames(names: Array<string | null | undefined>): string[] {
  return names.map((n) => (n ?? '').trim().toLowerCase()).filter(Boolean);
}

const escapeRegExp = (s: string) => s.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');

/**
 * Status shown against a transaction on the enquiry screen:
 *  - BLACKLISTED          a blacklisted name appears in the description
 *  - BLACKLISTED_PARTIAL  any single word of a blacklisted name appears as a whole word
 *  - SUSPICIOUS           a suspicious name appears in the description
 */
export function classifyTransaction(description: string, lists: WatchLists): WatchStatus {
  const desc = description.trim().toLowerCase();
  // Bank descriptions use '*' as a separator
  const cleaned = desc.replaceAll('*', ' ');

  if (lists.blacklisted.some((name) => cleaned.includes(name))) return 'BLACKLISTED';

  for (const name of lists.blacklisted) {
    for (const word of name.split(/\s+/)) {
      if (word.length > 1 && new RegExp(`\\b${escapeRegExp(word)}\\b`).test(desc)) return 'BLACKLISTED_PARTIAL';
    }
  }

  if (lists.suspicious.some((name) => cleaned.includes(name))) return 'SUSPICIOUS';
  return 'NONE';
}

/**
 * Keyword match used when grouping an exported report: the whole phrase
 * appears, or at least `minWords` of its words appear close together (no more
 * than `maxGap` positions apart).
 */
export function isKeywordMatched(keyword: string, description: string, minWords = 2, maxGap = 3): boolean {
  const key = keyword.toLowerCase().trim();
  const desc = description.toLowerCase().trim();
  if (desc.includes(key)) return true;

  const descWords = desc.split(/\s+/).filter(Boolean);
  const positions = key
    .split(/\s+/)
    .filter(Boolean)
    .map((word) => descWords.indexOf(word))
    .filter((pos) => pos >= 0)
    .sort((a, b) => a - b);
  if (positions.length === 0) return false;

  let blockSize = 1;
  for (let i = 1; i < positions.length; i++) {
    blockSize = positions[i] - positions[i - 1] <= maxGap ? blockSize + 1 : 1;
    if (blockSize >= minWords) return true;
  }
  return blockSize >= minWords;
}

export type ExportCategory = 'Blacklisted' | 'Suspected' | 'Others';

/** Category and matched keyword (upper-cased) a transaction is filed under in exports. */
export function exportCategory(
  description: string,
  lists: WatchLists,
): { category: ExportCategory; keyword: string | null } {
  const cleaned = description.toLowerCase().replaceAll('*', ' ');
  for (const name of lists.blacklisted) {
    if (isKeywordMatched(name, cleaned)) return { category: 'Blacklisted', keyword: name.toUpperCase() };
  }
  for (const name of lists.suspicious) {
    if (cleaned.includes(name)) return { category: 'Suspected', keyword: name.toUpperCase() };
  }
  return { category: 'Others', keyword: null };
}
