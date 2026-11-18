import type { Connector } from "../analyze/analyze.js";
import type { ParamValues } from "../scoring/index.js";

export type CacheOptions = {
  ttlMs?: number;
  maxEntries?: number;
  now?: () => number;
};

/**
 * In-memory cache for a connector (no database, see docs/ARCHITECTURE.md).
 * Key: coordinates rounded to ~100 m. Identical concurrent requests share a single call.
 * A failure is never cached: the next request retries.
 */
export function withCache(connector: Connector, options: CacheOptions = {}): Connector {
  const { ttlMs = 6 * 60 * 60 * 1000, maxEntries = 1000, now = Date.now } = options;
  const done = new Map<string, { expires: number; values: ParamValues }>();
  const pending = new Map<string, Promise<ParamValues>>();

  return async (site) => {
    const key = `${site.lat.toFixed(3)},${site.lon.toFixed(3)}`;
    const hit = done.get(key);
    if (hit && hit.expires > now()) return { ...hit.values };
    const running = pending.get(key);
    if (running) return { ...(await running) };

    const promise = connector(site);
    pending.set(key, promise);
    try {
      const values = await promise;
      if (done.size >= maxEntries) done.delete(done.keys().next().value as string);
      done.set(key, { expires: now() + ttlMs, values });
      return { ...values };
    } finally {
      pending.delete(key);
    }
  };
}

/** Warms the cache before the demo. */
export async function warmUp(connectors: Connector[], sites: { lat: number; lon: number }[]): Promise<void> {
  await Promise.allSettled(sites.flatMap((site) => connectors.map((c) => c(site))));
}
