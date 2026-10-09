import type { Embedder } from './embedding-name-extractor.js';

export interface TransformersEmbedderOptions {
  /** Hugging Face model id (ONNX build). */
  model?: string;
  /** Where downloaded model files are kept. */
  cacheDir?: string;
  /** Set false to use only files already in the cache. */
  allowDownload?: boolean;
}

// ONNX build of the sentence-transformers model the desktop application used
const DEFAULT_MODEL = 'Xenova/all-MiniLM-L6-v2';

/**
 * Loads a sentence-embedding model through transformers.js. The model is
 * downloaded on first use and cached; the package is an optional dependency,
 * so this rejects when it is not installed.
 */
export async function createTransformersEmbedder(options: TransformersEmbedderOptions = {}): Promise<Embedder> {
  const { pipeline, env } = await import('@huggingface/transformers');
  if (options.cacheDir) env.cacheDir = options.cacheDir;
  if (options.allowDownload === false) env.allowRemoteModels = false;

  const extractor = await pipeline('feature-extraction', options.model ?? DEFAULT_MODEL, { dtype: 'fp32' });

  return async (texts: string[]) => {
    if (texts.length === 0) return [];
    const output = await extractor(texts, { pooling: 'mean', normalize: true });
    return output.tolist() as number[][];
  };
}
