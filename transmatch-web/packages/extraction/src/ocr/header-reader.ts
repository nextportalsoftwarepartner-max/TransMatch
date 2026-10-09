import { fileURLToPath } from 'node:url';
import { createWorker, PSM, type Worker } from 'tesseract.js';
import type { PdfDocument } from '../pdf/pdf-document.js';

// Letterheads are mostly logos, so the bank is identified by OCR of the top
// strip of the first page rather than from the text layer.
const RENDER_DPI = 200;
const HEADER_FRACTION = 0.1;

const BUNDLED_TESSDATA = fileURLToPath(new URL('../../tessdata', import.meta.url));

let workerPromise: Promise<Worker> | null = null;

function getWorker(): Promise<Worker> {
  workerPromise ??= (async () => {
    const worker = await createWorker('eng', undefined, {
      langPath: process.env.TESSDATA_DIR || BUNDLED_TESSDATA,
      gzip: false,
      cacheMethod: 'none',
    });
    await worker.setParameters({ tessedit_pageseg_mode: PSM.SINGLE_BLOCK });
    return worker;
  })();
  workerPromise.catch(() => {
    workerPromise = null;
  });
  return workerPromise;
}

/** Reads the text in the top strip of the first page. Returns null when the page cannot be rendered. */
export async function readHeaderText(pdf: PdfDocument): Promise<string | null> {
  if (pdf.pageCount === 0) return null;

  let png: Uint8Array;
  try {
    png = pdf.renderPageTopPng(0, RENDER_DPI, HEADER_FRACTION);
  } catch {
    return null;
  }

  const worker = await getWorker();
  const { data } = await worker.recognize(Buffer.from(png));
  return data.text;
}

/** Releases the OCR worker; call on application shutdown. */
export async function shutdownOcr(): Promise<void> {
  const pending = workerPromise;
  workerPromise = null;
  if (pending) await (await pending).terminate();
}
