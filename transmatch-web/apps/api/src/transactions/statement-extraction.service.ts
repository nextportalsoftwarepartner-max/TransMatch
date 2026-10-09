import { Inject, Injectable, Logger, UnprocessableEntityException, type OnApplicationShutdown } from '@nestjs/common';
import {
  createEmbeddingNameExtractor,
  createTransformersEmbedder,
  ExtractionError,
  extractStatement,
  normalizeStatement,
  shutdownOcr,
  supportedBankTemplates,
  type EmbeddingNameExtractor,
  type NormalizedStatement,
} from '@transmatch/extraction';
import type { BankTemplateDto } from '@transmatch/shared';
import { APP_CONFIG, type AppConfig } from '../config/app-config.js';

/** Reads bank statement PDFs. Wraps the extraction package and owns the optional embedding model. */
@Injectable()
export class StatementExtractionService implements OnApplicationShutdown {
  private readonly logger = new Logger('StatementExtraction');
  private nameExtractor: Promise<EmbeddingNameExtractor | null> | null = null;

  constructor(@Inject(APP_CONFIG) private readonly config: AppConfig) {}

  bankTemplates(): BankTemplateDto[] {
    return supportedBankTemplates();
  }

  async extract(pdf: Uint8Array, bankId?: number): Promise<NormalizedStatement> {
    try {
      const result = await extractStatement(pdf, { bankId, embeddingNameExtractor: await this.getNameExtractor() });
      return normalizeStatement(result);
    } catch (err) {
      if (err instanceof ExtractionError) {
        throw new UnprocessableEntityException({ statusCode: 422, message: err.message, code: err.code });
      }
      this.logger.error(err instanceof Error ? (err.stack ?? err.message) : String(err));
      throw new UnprocessableEntityException({
        statusCode: 422,
        message: 'The file could not be read as a PDF bank statement.',
        code: 'UNREADABLE_PDF',
      });
    }
  }

  async onApplicationShutdown(): Promise<void> {
    await shutdownOcr();
  }

  /**
   * The embedding model is loaded on first use (and downloaded once). When it
   * cannot be loaded, names fall back to the pattern-based extraction.
   */
  private getNameExtractor(): Promise<EmbeddingNameExtractor | null> {
    if (!this.config.ner.mlEnabled) return Promise.resolve(null);
    this.nameExtractor ??= createTransformersEmbedder({ cacheDir: this.config.ner.cacheDir })
      .then((embedder) => createEmbeddingNameExtractor(embedder))
      .catch((err: unknown) => {
        this.logger.warn(
          `Embedding model unavailable, using pattern-based name extraction: ${err instanceof Error ? err.message : String(err)}`,
        );
        return null;
      });
    return this.nameExtractor;
  }
}
