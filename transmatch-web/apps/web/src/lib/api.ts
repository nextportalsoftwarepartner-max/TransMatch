import type { ApiErrorBody } from "@transmatch/shared";

export class ApiError extends Error {
  constructor(
    readonly status: number,
    message: string,
    readonly code?: string,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

type Query = Record<string, string | number | boolean | null | undefined>;

interface RequestOptions {
  method?: "GET" | "POST" | "PUT" | "PATCH" | "DELETE";
  query?: Query;
  /** JSON body */
  body?: unknown;
  /** Multipart body (file uploads) */
  form?: FormData;
}

function buildUrl(path: string, query?: Query): string {
  const params = new URLSearchParams();
  for (const [key, value] of Object.entries(query ?? {})) {
    if (value !== undefined && value !== null && value !== "") params.set(key, String(value));
  }
  const qs = params.toString();
  return `/api${path}${qs ? `?${qs}` : ""}`;
}

async function send(path: string, options: RequestOptions): Promise<Response> {
  let response: Response;
  try {
    response = await fetch(buildUrl(path, options.query), {
      method: options.method ?? "GET",
      credentials: "same-origin",
      headers: options.body !== undefined ? { "content-type": "application/json" } : undefined,
      body: options.form ?? (options.body !== undefined ? JSON.stringify(options.body) : undefined),
    });
  } catch {
    throw new ApiError(0, "The server could not be reached. Please check your connection and try again.");
  }
  if (!response.ok) {
    const error = (await response.json().catch(() => null)) as ApiErrorBody | null;
    throw new ApiError(response.status, error?.message ?? `Request failed (${response.status}).`, error?.code);
  }
  return response;
}

/** Calls the API and returns the JSON response (undefined for empty responses). */
export async function api<T = void>(path: string, options: RequestOptions = {}): Promise<T> {
  const response = await send(path, options);
  if (response.status === 204) return undefined as T;
  const text = await response.text();
  return (text ? JSON.parse(text) : undefined) as T;
}

/** Calls the API and saves the response as a file. */
export async function download(path: string, fallbackName: string, options: RequestOptions = {}): Promise<void> {
  const response = await send(path, options);
  const fileName = /filename="([^"]+)"/.exec(response.headers.get("content-disposition") ?? "")?.[1] ?? fallbackName;
  const url = URL.createObjectURL(await response.blob());
  const link = document.createElement("a");
  link.href = url;
  link.download = fileName;
  link.click();
  URL.revokeObjectURL(url);
}

export const errorMessage = (error: unknown) => (error instanceof Error ? error.message : "Something went wrong.");
