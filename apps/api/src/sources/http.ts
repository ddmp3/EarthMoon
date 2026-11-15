export type FetchLike = (url: string, init?: { signal?: AbortSignal; headers?: Record<string, string> }) => Promise<{
  ok: boolean;
  status: number;
  json(): Promise<unknown>;
}>;

export type FetchJsonOptions = {
  fetchImpl?: FetchLike;
  /** Retries after the first attempt (Planetary Computer 502s, network drops). */
  retries?: number;
  timeoutMs?: number;
  /** Pause before attempt n: backoffMs * n. Use 0 in tests. */
  backoffMs?: number;
  headers?: Record<string, string>;
};

export class HttpError extends Error {
  constructor(
    message: string,
    readonly status: number,
  ) {
    super(message);
    this.name = "HttpError";
  }
}

const sleep = (ms: number): Promise<void> => new Promise((resolve) => setTimeout(resolve, ms));

/** GET JSON with a timeout and retries on network errors or 5xx. A 4xx error is not retried. */
export async function fetchJson(url: string, options: FetchJsonOptions = {}): Promise<unknown> {
  const { retries = 2, timeoutMs = 15_000, backoffMs = 800 } = options;
  const doFetch: FetchLike = options.fetchImpl ?? ((u, init) => fetch(u, init));
  let lastError: unknown;
  for (let attempt = 0; attempt <= retries; attempt++) {
    if (attempt > 0) await sleep(backoffMs * attempt);
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), timeoutMs);
    try {
      const response = await doFetch(url, { signal: controller.signal, headers: options.headers });
      if (response.ok) return await response.json();
      lastError = new HttpError(`HTTP ${response.status} for ${new URL(url).host}`, response.status);
      if (response.status < 500) throw lastError;
    } catch (error) {
      if (error instanceof HttpError && error.status < 500) throw error;
      lastError = error;
    } finally {
      clearTimeout(timer);
    }
  }
  throw lastError instanceof Error ? lastError : new Error("Request failed");
}
