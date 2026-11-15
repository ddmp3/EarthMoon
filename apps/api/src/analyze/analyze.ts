import { isVegetated, scoreSite } from "../scoring/index.js";
import type { CriterionScore, ParamValues } from "../scoring/index.js";
import { resolveRequest } from "./validate.js";

/** Candidate site. */
export type Site = {
  id: string;
  name: string;
  lat: number;
  lon: number;
  terrain?: string;
  role: "validation" | "negative" | "candidate";
};

/** Source connector. */
export type Connector = (site: { lat: number; lon: number }) => Promise<ParamValues>;

export type AnalyzedSite = Pick<Site, "id" | "name" | "lat" | "lon" | "role"> & {
  total: number;
  criteria: CriterionScore[];
  /** Present if the site is excluded by the "bare soil" filter (total forced to 0). */
  excluded?: "vegetation";
};

export type AnalyzeResponse = {
  mode: string;
  sites: AnalyzedSite[];
};

export type AnalyzeDeps = {
  sites: Site[];
  connectors: Connector[];
  /** Maximum number of sites queried in parallel. */
  concurrency?: number;
  onConnectorError?: (error: unknown, site: Site) => void;
};

/**
 * Queries all connectors and merges their values.
 * A failing connector contributes nothing: its parameters will be "missing", with no global error.
 */
export async function collectValues(
  site: Site,
  connectors: Connector[],
  onError?: (error: unknown, site: Site) => void,
): Promise<ParamValues> {
  const results = await Promise.allSettled(connectors.map((c) => c({ lat: site.lat, lon: site.lon })));
  const merged: ParamValues = {};
  for (const result of results) {
    if (result.status === "fulfilled") Object.assign(merged, result.value);
    else onError?.(result.reason, site);
  }
  return merged;
}

async function mapWithConcurrency<T, R>(items: T[], limit: number, fn: (item: T) => Promise<R>): Promise<R[]> {
  const out: R[] = new Array<R>(items.length);
  let next = 0;
  const worker = async (): Promise<void> => {
    while (next < items.length) {
      const i = next++;
      out[i] = await fn(items[i]);
    }
  };
  await Promise.all(Array.from({ length: Math.min(limit, items.length) }, worker));
  return out;
}

/** Core of POST /api/analyze: validates the request, collects values, scores and sorts the sites. */
export async function analyze(body: unknown, deps: AnalyzeDeps): Promise<AnalyzeResponse> {
  const request = resolveRequest(body);
  const analyzed = await mapWithConcurrency(deps.sites, deps.concurrency ?? 8, async (site): Promise<AnalyzedSite> => {
    const values = await collectValues(site, deps.connectors, deps.onConnectorError);
    const { total, criteria } = scoreSite(values, request.criteria);
    const base = { id: site.id, name: site.name, lat: site.lat, lon: site.lon, role: site.role, criteria };
    if (request.bareSoilOnly && isVegetated(values)) {
      return { ...base, total: 0, excluded: "vegetation" };
    }
    return { ...base, total };
  });
  analyzed.sort((a, b) => Number(a.excluded !== undefined) - Number(b.excluded !== undefined) || b.total - a.total);
  return { mode: request.mode, sites: analyzed };
}
