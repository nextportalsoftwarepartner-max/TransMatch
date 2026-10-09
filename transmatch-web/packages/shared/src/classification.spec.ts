import { describe, expect, it } from 'vitest';
import { classifyTransaction, exportCategory, isKeywordMatched, normalizeNames } from './classification.js';
import { buildRights, can, hasRight, mergeRights } from './permissions.js';

const lists = { blacklisted: normalizeNames(['Acme Trading', ' ']), suspicious: normalizeNames(['Odd Co']) };

describe('classifyTransaction', () => {
  it('flags a full blacklist match, treating * as a separator', () => {
    expect(classifyTransaction('TRANSFER FR A/C ACME*TRADING rental', lists)).toBe('BLACKLISTED');
  });

  it('flags a partial match when one whole word of a blacklisted name appears', () => {
    expect(classifyTransaction('PAYMENT TO ACME HOLDINGS', lists)).toBe('BLACKLISTED_PARTIAL');
    expect(classifyTransaction('PAYMENT TO ACMELAND', lists)).toBe('NONE');
  });

  it('flags suspicious names only when nothing is blacklisted', () => {
    expect(classifyTransaction('DUITNOW ODD CO', lists)).toBe('SUSPICIOUS');
    expect(classifyTransaction('DUITNOW TAN AH KOW', lists)).toBe('NONE');
  });

  it('ignores blank names in the lists', () => {
    expect(lists.blacklisted).toEqual(['acme trading']);
  });
});

describe('isKeywordMatched', () => {
  it('matches the whole phrase', () => {
    expect(isKeywordMatched('acme trading', 'pay acme trading now')).toBe(true);
  });

  it('matches two keyword words that sit close together', () => {
    expect(isKeywordMatched('acme global trading', 'acme sdn trading')).toBe(true);
  });

  it('does not match a single word or words far apart', () => {
    expect(isKeywordMatched('acme trading', 'acme holdings')).toBe(false);
    expect(isKeywordMatched('acme trading', 'acme a b c d trading')).toBe(false);
  });
});

describe('exportCategory', () => {
  it('files a transaction under the matched keyword', () => {
    expect(exportCategory('PAY ACME TRADING', lists)).toEqual({ category: 'Blacklisted', keyword: 'ACME TRADING' });
    expect(exportCategory('PAY ODD CO', lists)).toEqual({ category: 'Suspected', keyword: 'ODD CO' });
    expect(exportCategory('PAY SOMEONE', lists)).toEqual({ category: 'Others', keyword: null });
  });
});

describe('access rights', () => {
  it('reads and combines right flags', () => {
    expect(buildRights(['VIEW', 'UPDATE'])).toBe('10100000');
    expect(hasRight('10100000', 'UPDATE')).toBe(true);
    expect(hasRight('10100000', 'DELETE')).toBe(false);
    expect(mergeRights('10000000', '01000000')).toBe('11000000');
  });

  it('lets super users through and checks everyone else', () => {
    const user = { userId: 'US1', loginId: 'a', userName: 'A', isSuperUser: false, permissions: { ADM_BANK_PROFILE: '10000000' } };
    expect(can(user, 'ADM_BANK_PROFILE')).toBe(true);
    expect(can(user, 'ADM_BANK_PROFILE', 'CREATE')).toBe(false);
    expect(can({ ...user, isSuperUser: true }, 'ADM_USER_GROUP', 'DELETE')).toBe(true);
    expect(can(null, 'ADM_BANK_PROFILE')).toBe(false);
  });
});
