import type { Connector } from "../analyze/analyze.js";
import type { ParamValues } from "../scoring/index.js";

export type CacheOptions = {
  ttlMs?: number;
  maxEntries?: number;
  now?: () => number;
};

/**
 * Cache mémoire d'un connecteur (aucune base de données, voir docs/architecture.md).
 * Clé : coordonnées arrondies à ~100 m. Les requêtes identiques simultanées partagent un seul appel.
 * Un échec n'est jamais mis en cache : la prochaine requête réessaie.
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

/** Précharge le cache avant la démo (docs/plan-projet.md, « cache préchauffé »). */
export async function warmUp(connectors: Connector[], sites: { lat: number; lon: number }[]): Promise<void> {
  await Promise.allSettled(sites.flatMap((site) => connectors.map((c) => c(site))));
}
