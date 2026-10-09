export interface DateParts {
  year: number;
  month: number;
  day: number;
}

const MONTHS_SHORT = ['jan', 'feb', 'mar', 'apr', 'may', 'jun', 'jul', 'aug', 'sep', 'oct', 'nov', 'dec'];
const MONTHS_LONG = [
  'january',
  'february',
  'march',
  'april',
  'may',
  'june',
  'july',
  'august',
  'september',
  'october',
  'november',
  'december',
];

const DIRECTIVES: Record<string, string> = {
  d: '(?<d>3[01]|[12]\\d|0[1-9]|[1-9])',
  m: '(?<m>1[0-2]|0[1-9]|[1-9])',
  Y: '(?<Y>\\d{4})',
  y: '(?<y>\\d{2})',
  b: `(?<b>${MONTHS_SHORT.join('|')})`,
  B: `(?<B>${MONTHS_LONG.join('|')})`,
};

/**
 * Parses `value` against a strptime-style format (%d %m %Y %y %b %B).
 * Returns null when the text does not match the format or is not a real date.
 */
export function parseDate(value: string, format: string): DateParts | null {
  let pattern = '';
  for (let i = 0; i < format.length; i++) {
    const ch = format[i];
    if (ch === '%') {
      const directive = DIRECTIVES[format[++i]];
      if (!directive) throw new Error(`Unsupported date directive %${format[i]}`);
      pattern += directive;
    } else if (/\s/.test(ch)) {
      pattern += '\\s+';
    } else {
      pattern += ch.replace(/[.*+?^${}()|[\]\\/-]/g, '\\$&');
    }
  }
  const match = new RegExp(`^${pattern}$`, 'i').exec(value);
  if (!match?.groups) return null;
  const g = match.groups;

  let year: number;
  if (g.Y !== undefined) year = Number(g.Y);
  else if (g.y !== undefined) year = Number(g.y) + (Number(g.y) >= 69 ? 1900 : 2000);
  else year = 1900;

  let month = 1;
  if (g.m !== undefined) month = Number(g.m);
  else if (g.b !== undefined) month = MONTHS_SHORT.indexOf(g.b.toLowerCase()) + 1;
  else if (g.B !== undefined) month = MONTHS_LONG.indexOf(g.B.toLowerCase()) + 1;

  const day = g.d !== undefined ? Number(g.d) : 1;
  return isRealDate(year, month, day) ? { year, month, day } : null;
}

/** Tries each format in turn. */
export function parseDateAny(value: string, formats: string[]): DateParts | null {
  for (const format of formats) {
    const parsed = parseDate(value, format);
    if (parsed) return parsed;
  }
  return null;
}

export function isRealDate(year: number, month: number, day: number): boolean {
  if (month < 1 || month > 12 || day < 1) return false;
  return day <= new Date(Date.UTC(year, month, 0)).getUTCDate();
}

const pad2 = (n: number) => String(n).padStart(2, '0');

/** dd/mm/yy */
export function formatShort(d: DateParts): string {
  return `${pad2(d.day)}/${pad2(d.month)}/${pad2(d.year % 100)}`;
}

/** yyyy-mm-dd */
export function formatIso(d: DateParts): string {
  return `${String(d.year).padStart(4, '0')}-${pad2(d.month)}-${pad2(d.day)}`;
}
