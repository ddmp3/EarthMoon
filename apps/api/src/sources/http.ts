export type FetchLike = (url: string, init?: { signal?: AbortSignal; headers?: Record<string, string> }) => Promise<{
  ok: boolean;
  status: number;
  json(): Promise<unknown>;
}>;

export type FetchJsonOptions = {
  fetchImpl?: FetchLike;
  /** Nouvelles tentatives après le premier essai (502 de Planetary Computer, coupures réseau). */
  retries?: number;
  timeoutMs?: number;
  /** Pause avant la tentative n : backoffMs * n. Mettre 0 dans les tests. */
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

/** GET JSON avec délai maximal et nouvelles tentatives sur erreur réseau ou 5xx. Une erreur 4xx n'est pas retentée. */
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
      lastError = new HttpError(`HTTP ${response.status} pour ${new URL(url).host}`, response.status);
      if (response.status < 500) throw lastError;
    } catch (error) {
      if (error instanceof HttpError && error.status < 500) throw error;
      lastError = error;
    } finally {
      clearTimeout(timer);
    }
  }
  throw lastError instanceof Error ? lastError : new Error("Échec de la requête");
}
