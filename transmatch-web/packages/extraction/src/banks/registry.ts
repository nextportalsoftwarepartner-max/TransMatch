import type { TextEngine } from '../types.js';
import { hlbParser } from './hlb.js';
import { mbbParser } from './mbb.js';
import type { BankParser } from './parser.js';
import { pbbParser } from './pbb.js';
import { rhbParser } from './rhb.js';
import { uobParser } from './uob.js';

export const BANK_UNDEFINED = 98;
export const BANK_NOT_SUPPORTED = 99;

export interface BankTemplate {
  id: number;
  name: string;
  /** Statement parser; null where the bank is recognised but no template has been built yet. */
  parser: BankParser | null;
}

export const BANK_TEMPLATES: BankTemplate[] = [
  { id: 1, name: 'Public Islamic Bank', parser: pbbParser },
  { id: 2, name: 'Public Bank', parser: pbbParser },
  { id: 3, name: 'Maybank Islamic', parser: mbbParser },
  { id: 4, name: 'Maybank', parser: mbbParser },
  { id: 5, name: 'CIMB Islamic', parser: null },
  { id: 6, name: 'CIMB Bank', parser: null },
  { id: 7, name: 'RHB Islamic', parser: rhbParser },
  { id: 8, name: 'RHB Reflex', parser: rhbParser },
  { id: 9, name: 'RHB Bank', parser: rhbParser },
  { id: 10, name: 'Hong Leong Islamic', parser: hlbParser },
  { id: 11, name: 'Hong Leong Bank', parser: hlbParser },
  { id: 12, name: 'AmBank Islamic', parser: null },
  { id: 13, name: 'AmBank', parser: null },
  { id: 14, name: 'UOB Islamic', parser: uobParser },
  { id: 15, name: 'UOB Bank', parser: uobParser },
  { id: 16, name: 'AEON Bank Islamic', parser: null },
  { id: 17, name: 'AEON Bank', parser: null },
  { id: 18, name: 'Affin Bank Islamic', parser: null },
  { id: 19, name: 'Affin Bank', parser: null },
  { id: 20, name: 'BSN Islamic', parser: null },
  { id: 21, name: 'BSN', parser: null },
  { id: 22, name: 'Bank Muamalat', parser: null },
];

export function findBankTemplate(bankId: number): BankTemplate | undefined {
  return BANK_TEMPLATES.find((t) => t.id === bankId);
}

/** Templates a statement can actually be extracted with. */
export function supportedBankTemplates(): Array<{ id: number; name: string }> {
  return BANK_TEMPLATES.filter((t) => t.parser !== null).map(({ id, name }) => ({ id, name }));
}

/** RHB Reflex statements have a fixed layout and are read by coordinates; everything else by text flow. */
export function engineForBank(bankId: number): TextEngine {
  return bankId === 8 ? 'pdfplumberxy_rhb' : 'fitz';
}

/**
 * Works out the bank from the text read off the top strip of the first page
 * (the letterhead). Order matters: Islamic variants are tested before the
 * conventional bank of the same group. Several keys are spelled the way the
 * logo is read by OCR ("cimb cdcks", "hongleong"). Logo lettering is read a
 * little differently from one renderer to the next ("PUBLIC BAN K", "ttt UOB",
 * "RHBS"), so those three are matched loosely.
 */
export function matchBank(headerText: string): number {
  const t = headerText.toLowerCase();
  const compact = t.replace(/\s+/g, '');

  if (t.includes('public islamic bank') || compact.includes('publicislamicbank')) return 1;
  if (t.includes('public bank') || compact.includes('publicbank')) return 2;

  if (t.includes('maybank islamic berhad')) return 3;
  if (t.includes('malayan banking berhad')) return 4;

  if (t.includes('cimb islamic bank berhad')) return 5;
  if (t.includes('cimb cdcks')) return 6;

  if (t.includes('rhb islamic bank berhad')) return 7;
  if ((t.includes('rbs') || t.includes('rhb')) && t.includes('reflex')) return 8;
  if (t.includes('rhb bank berhad')) return 9;

  if (t.includes('hongleong islamic bank')) return 10;
  if (t.includes('hongleong bank')) return 11;

  if (t.includes('ambank islamic berhad')) return 12;
  if (t.includes('ambank')) return 13;

  if (/\buob islamic berhad/.test(t)) return 14;
  if (/\buob\b/.test(t)) return 15;

  if (t.includes('aeon islamic berhad bank')) return 16;
  if (t.includes('aeon bank')) return 17;

  if (t.includes('affin islamic berhad bank')) return 18;
  if (t.includes('affin bank')) return 19;

  if (t.includes('bsn islamic')) return 20;
  if (t.includes('bsn')) return 21;

  if (t.includes('bank muamalat')) return 22;

  return BANK_NOT_SUPPORTED;
}
