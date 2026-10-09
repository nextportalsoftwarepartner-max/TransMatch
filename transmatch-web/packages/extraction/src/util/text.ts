// Small helpers that keep the bank parsers' string handling identical to the
// original implementation they were ported from.

/** Splits on runs of whitespace, dropping empty pieces. */
export function words(s: string): string[] {
  const t = s.trim();
  return t === '' ? [] : t.split(/\s+/);
}

/** Collapses every run of whitespace to a single space. */
export function collapseSpaces(s: string): string {
  return words(s).join(' ');
}

/** "JERRY DISTRIBUTORS SDN BHD" -> "Jerry Distributors Sdn Bhd". */
export function titleCase(s: string): string {
  let out = '';
  let prevIsLetter = false;
  for (const ch of s) {
    const isLetter = ch.toLowerCase() !== ch.toUpperCase();
    out += isLetter ? (prevIsLetter ? ch.toLowerCase() : ch.toUpperCase()) : ch;
    prevIsLetter = isLetter;
  }
  return out;
}

/** Strict number parse: throws on anything that is not a plain decimal. */
export function toNumber(s: string): number {
  const t = s.trim();
  if (!/^[+-]?(\d+\.?\d*|\.\d+)$/.test(t)) {
    throw new Error(`could not convert string to number: '${s}'`);
  }
  return Number(t);
}

/** True for strings made only of digits (and at least one). */
export function isDigits(s: string): boolean {
  return /^\d+$/.test(s);
}

/** Removes the given characters from both ends, like a character-set trim. */
export function stripChars(s: string, chars: string): string {
  let start = 0;
  let end = s.length;
  while (start < end && chars.includes(s[start])) start++;
  while (end > start && chars.includes(s[end - 1])) end--;
  return s.slice(start, end);
}
