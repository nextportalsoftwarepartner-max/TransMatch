import { describe, expect, it } from 'vitest';
import { matchBank } from '../src/banks/registry.js';
import { cleanCompanyName, generateCandidates } from '../src/names/embedding-name-extractor.js';
import { extractName, extractNameBasic, isGenericTransactionTerm } from '../src/names/name-extractor.js';
import { parseStatementDate, resolveTransactionDate } from '../src/normalize.js';
import { formatShort, parseDate } from '../src/util/dates.js';
import { titleCase } from '../src/util/text.js';

describe('matchBank', () => {
  it('recognises letterheads as OCR reads them', () => {
    expect(matchBank('~ PUBLIC BAN K SUNGAI BULOH BRANCH')).toBe(2);
    expect(matchBank('PUBLIC ISLAMIC BANK Tred nan')).toBe(1);
    expect(matchBank('Maybank Islamic Berhad (787435-M) 15th Floor')).toBe(3);
    expect(matchBank('Malayan Banking Berhad (3813-K)')).toBe(4);
    expect(matchBank('RHBS © Reflex Cash Management')).toBe(8);
    expect(matchBank('Statement Period RHB Bank Berhad 196501000373')).toBe(9);
    expect(matchBank('> HongLeong Islamic Bank')).toBe(10);
    expect(matchBank('ttt UOB')).toBe(15);
    expect(matchBank('Amanah PERSONAL FINANCIAL UPDATE')).toBe(99);
  });
});

describe('name extraction', () => {
  it('pulls the counterparty out of common transfer descriptions', () => {
    expect(extractNameBasic('TRANSFER FR A/C LOY HEONG HARDWARE *    Rawang lake    MBB CT')).toBe('LOY HEONG HARDWARE');
    expect(extractNameBasic('PAYMENT VIA MYDEBIT PUBLIC BANK BERHAD *    RAWANG, MYS')).toBe('PUBLIC BANK BERHAD');
    expect(extractNameBasic('TSFR FUND DR-ATM/EFT 122585 6384XXXXXX WAH OON')).toBe('WAH OON');
  });

  it('rejects generic transaction terms', () => {
    expect(isGenericTransactionTerm('CDM CASH DEPOSIT')).toBe(true);
    expect(isGenericTransactionTerm('DR 252BA103127')).toBe(true);
    expect(isGenericTransactionTerm('252BA103127')).toBe(true);
    expect(isGenericTransactionTerm('JERRY DISTRIBUTORS SDN. BHD.')).toBe(false);
  });

  it('matches the desktop application on Hong Leong descriptions', () => {
    expect(
      extractName('HLConnect DuitNow-previously Inst Fund transfer LOH SEONG CHEE 20250201HLBBMYKL010ORM90961237'),
    ).toBe('HLCONNECT DUITNOW-PREVIOUSLY INST FUND TRANSFER LOH SEONG CHEE');
    // Inherited rule: a result made only of letters, digits and spaces (8+ characters)
    // is treated as a reference number, so plain names like this one are dropped.
    expect(extractName('DuitNow QR QR Payment CHAN LAI KUAN 20250114HLBBMYKLA40OQR21215699')).toBeNull();
  });

  it('cleans repeated and noisy company names', () => {
    expect(cleanCompanyName('AMBG GURUVAYURAPA ENTERPRISE AMBG GURUVAYURAPA ENTERPRISE')).toBe('GURUVAYURAPA ENTERPRISE');
    expect(cleanCompanyName('DUITNOW/INSTANT')).toBe('');
  });

  it('never offers pure noise as a candidate', () => {
    const candidates = generateCandidates('DuitNow/Instant Trf Goods Payment Guruvayurapa Enterprise 1234567890');
    expect(candidates.length).toBeGreaterThan(0);
    expect(candidates).not.toContain('GOODS PAYMENT');
    expect(candidates.some((c) => c.toUpperCase().includes('GURUVAYURAPA ENTERPRISE'))).toBe(true);
  });
});

describe('dates', () => {
  it('parses the formats printed on statements', () => {
    expect(parseDate('31 Aug 2024', '%d %b %Y')).toEqual({ year: 2024, month: 8, day: 31 });
    expect(parseDate('1 jul 24', '%d %b %y')).toEqual({ year: 2024, month: 7, day: 1 });
    expect(parseDate('31 Feb 2024', '%d %b %Y')).toBeNull();
    expect(parseDate('31 August 2024', '%d %b %Y')).toBeNull();
    expect(formatShort({ year: 2024, month: 8, day: 3 })).toBe('03/08/24');
  });

  it('reads statement dates day-first', () => {
    expect(parseStatementDate('05/06/24')).toEqual({ year: 2024, month: 6, day: 5 });
    expect(parseStatementDate('13/02/2025')).toEqual({ year: 2025, month: 2, day: 13 });
    expect(parseStatementDate('Invalid Date')).toBeNull();
  });

  it('gives day/month transaction dates the statement year, or the year before across the new year', () => {
    const january = { year: 2025, month: 1, day: 13 };
    expect(resolveTransactionDate('02/01', january)).toEqual({ year: 2025, month: 1, day: 2 });
    expect(resolveTransactionDate('28/12', january)).toEqual({ year: 2024, month: 12, day: 28 });
    expect(resolveTransactionDate('02/11/24', null)).toEqual({ year: 2024, month: 11, day: 2 });
    expect(resolveTransactionDate('06-06-2024', null)).toEqual({ year: 2024, month: 6, day: 6 });
    expect(resolveTransactionDate('02/11', null)).toBeNull();
    expect(resolveTransactionDate('2nd Nov', january)).toBeNull();
  });
});

describe('titleCase', () => {
  it('capitalises each word', () => {
    expect(titleCase('JERRY DISTRIBUTORS SDN. BHD.')).toBe('Jerry Distributors Sdn. Bhd.');
  });
});
