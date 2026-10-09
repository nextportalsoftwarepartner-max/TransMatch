import * as mupdf from 'mupdf';

/** A run of characters sharing one font, size and colour within a line. */
export interface TextSpan {
  text: string;
  x0: number;
  y0: number;
  x1: number;
  y1: number;
}

/** A whitespace-delimited word with its position, measured from the page's top-left in points. */
export interface PdfWord {
  text: string;
  x0: number;
  x1: number;
  top: number;
  bottom: number;
}

interface PdfChar {
  c: string;
  x0: number;
  x1: number;
  top: number;
  bottom: number;
}

interface WordOptions {
  xTolerance?: number;
  yTolerance?: number;
}

// The same extraction flags the desktop app's text engine used by default.
const STEXT_OPTIONS = 'preserve-whitespace,preserve-ligatures';

// Descender depth, as a fraction of font size, used to place word boxes. The
// coordinate-based templates (RHB Reflex) are set in Helvetica, whose descent
// is 207/1000; the column and row boundaries in those templates were measured
// against boxes built this way.
const WORD_BOX_DESCENT = 0.207;

/**
 * Thin wrapper over MuPDF that exposes the three views of a page the bank
 * parsers were written against: reading-order text, positioned spans and
 * positioned words.
 */
export class PdfDocument {
  private constructor(private readonly doc: mupdf.Document) {}

  static open(data: Uint8Array): PdfDocument {
    return new PdfDocument(mupdf.Document.openDocument(data, 'application/pdf'));
  }

  get pageCount(): number {
    return this.doc.countPages();
  }

  /** Text of one page: one output line per text line, in content order. */
  pageText(pageIndex: number): string {
    let out = '';
    let line = '';
    this.walk(pageIndex, {
      beginLine: () => {
        line = '';
      },
      onChar: (c) => {
        line += c;
      },
      endLine: () => {
        if (line.length > 0) {
          out += line.endsWith('\n') ? line : line + '\n';
        }
      },
    });
    return out;
  }

  /** Text of the whole document, pages joined by a newline. */
  text(): string {
    const pages: string[] = [];
    for (let i = 0; i < this.pageCount; i++) pages.push(this.pageText(i));
    return pages.join('\n');
  }

  /** Spans of one page in content order, grouped by the text line they sit on. */
  pageSpanLines(pageIndex: number): TextSpan[][] {
    const lines: TextSpan[][] = [];
    let spans: TextSpan[] = [];
    let current: (TextSpan & { key: string }) | null = null;
    const flush = () => {
      if (current) {
        const { key: _key, ...span } = current;
        spans.push(span);
        current = null;
      }
    };
    this.walk(pageIndex, {
      beginLine: () => {
        spans = [];
      },
      endLine: () => {
        flush();
        if (spans.length > 0) lines.push(spans);
      },
      onChar: (c, _origin, font, size, quad, color) => {
        const key = `${font.getName()}|${size}|${color.join(',')}`;
        const xs = [quad[0], quad[2], quad[4], quad[6]];
        const ys = [quad[1], quad[3], quad[5], quad[7]];
        const x0 = Math.min(...xs);
        const x1 = Math.max(...xs);
        const y0 = Math.min(...ys);
        const y1 = Math.max(...ys);
        if (current && current.key === key) {
          current.text += c;
          current.x0 = Math.min(current.x0, x0);
          current.x1 = Math.max(current.x1, x1);
          current.y0 = Math.min(current.y0, y0);
          current.y1 = Math.max(current.y1, y1);
        } else {
          flush();
          current = { key, text: c, x0, y0, x1, y1 };
        }
      },
    });
    return lines;
  }

  /**
   * Words of one page, grouped the way the desktop app's coordinate-based
   * engine grouped them: characters are clustered into lines by their top
   * edge, ordered left to right, and split on blanks or horizontal gaps.
   */
  pageWords(pageIndex: number, options: WordOptions = {}): PdfWord[] {
    const xTolerance = options.xTolerance ?? 3;
    const yTolerance = options.yTolerance ?? 3;

    const chars: PdfChar[] = [];
    this.walk(pageIndex, {
      onChar: (c, origin, _font, size, quad) => {
        const xs = [quad[0], quad[2], quad[4], quad[6]];
        // Character boxes are one font-size tall, sitting on the descender line.
        const bottom = origin[1] + WORD_BOX_DESCENT * size;
        chars.push({ c, x0: Math.min(...xs), x1: Math.max(...xs), top: bottom - size, bottom });
      },
    });

    const words: PdfWord[] = [];
    for (const lineChars of clusterByTop(chars, yTolerance)) {
      lineChars.sort((a, b) => a.x0 - b.x0);
      let word: PdfChar[] = [];
      const emit = () => {
        if (word.length === 0) return;
        words.push({
          text: word.map((ch) => ch.c).join(''),
          x0: Math.min(...word.map((ch) => ch.x0)),
          x1: Math.max(...word.map((ch) => ch.x1)),
          top: Math.min(...word.map((ch) => ch.top)),
          bottom: Math.max(...word.map((ch) => ch.bottom)),
        });
        word = [];
      };
      for (const ch of lineChars) {
        if (ch.c.trim() === '') {
          emit();
          continue;
        }
        const prev = word[word.length - 1];
        if (
          prev &&
          (ch.x0 < prev.x0 || ch.x0 > prev.x1 + xTolerance || Math.abs(ch.top - prev.top) > yTolerance)
        ) {
          emit();
        }
        word.push(ch);
      }
      emit();
    }
    return words;
  }

  /** Renders the top `fraction` of a page to PNG at the given resolution. */
  renderPageTopPng(pageIndex: number, dpi: number, fraction: number): Uint8Array {
    const page = this.doc.loadPage(pageIndex);
    try {
      const scale = dpi / 72;
      const [x0, y0, x1, y1] = page.getBounds();
      const width = Math.round((x1 - x0) * scale);
      const height = Math.floor(Math.round((y1 - y0) * scale) * fraction);
      const pixmap = new mupdf.Pixmap(mupdf.ColorSpace.DeviceRGB, [0, 0, width, height], false);
      try {
        pixmap.clear(255);
        const device = new mupdf.DrawDevice(mupdf.Matrix.scale(scale, scale), pixmap);
        try {
          page.run(device, mupdf.Matrix.identity);
          device.close();
        } finally {
          device.destroy();
        }
        return pixmap.asPNG();
      } finally {
        pixmap.destroy();
      }
    } finally {
      page.destroy();
    }
  }

  close(): void {
    this.doc.destroy();
  }

  private walk(pageIndex: number, walker: Parameters<mupdf.StructuredText['walk']>[0]): void {
    const page = this.doc.loadPage(pageIndex);
    try {
      const stext = page.toStructuredText(STEXT_OPTIONS);
      try {
        stext.walk(walker);
      } finally {
        stext.destroy();
      }
    } finally {
      page.destroy();
    }
  }
}

/** Groups characters into lines: tops within `tolerance` of the previous distinct top chain together. */
function clusterByTop(chars: PdfChar[], tolerance: number): PdfChar[][] {
  const tops = [...new Set(chars.map((ch) => ch.top))].sort((a, b) => a - b);
  const clusterOf = new Map<number, number>();
  let cluster = -1;
  let last: number | null = null;
  for (const top of tops) {
    if (last === null || top > last + tolerance) cluster += 1;
    clusterOf.set(top, cluster);
    last = top;
  }
  const lines: PdfChar[][] = Array.from({ length: cluster + 1 }, () => []);
  for (const ch of chars) lines[clusterOf.get(ch.top)!].push(ch);
  return lines;
}
