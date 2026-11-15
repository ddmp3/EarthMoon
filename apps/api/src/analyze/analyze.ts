import { describeMethod, rankStability, scoreSite, vegetationFactor, weightedTotal } from "../scoring/index.js";
import type { CriterionScore, ParamValues, SensitivityMethod, Stability } from "../scoring/index.js";
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
  /** Present if the site is excluded by the "bare soil" filter (dense vegetation: total forced to 0). */
  excluded?: "vegetation";
  /** Present if the filter reduced the total (NDVI between 0.2 and 0.6): multiplier between 0 and 1. */
  vegetationFactor?: number;
  /** Rank under perturbed weights, tolerances and bounds (absent for excluded sites). */
  stability?: Stability;
};

export type AnalyzeResponse = {
  mode: string;
  sites: AnalyzedSite[];
  /** How `stability` was computed. */
  sensitivity: SensitivityMethod;
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
  const collected = await mapWithConcurrency(deps.sites, deps.concurrency ?? 8, async (site) => {
    const values = await collectValues(site, deps.connectors, deps.onConnectorError);
    const factor = request.bareSoilOnly ? vegetationFactor(values) : 1;
    const { criteria } = scoreSite(values, request.criteria);
    const total = factor === 0 ? 0 : Math.round(weightedTotal(values, request.criteria) * factor);
    const base = { id: site.id, name: site.name, lat: site.lat, lon: site.lon, role: site.role, criteria, total };
    const analyzed: AnalyzedSite = {
      ...base,
      ...(factor === 0 ? { excluded: "vegetation" as const } : {}),
      ...(factor > 0 && factor < 1 ? { vegetationFactor: Math.round(factor * 100) / 100 } : {}),
    };
    return { analyzed, values, factor };
  });
  const stability = rankStability(
    collected.map(({ analyzed, values, factor }) => ({ id: analyzed.id, values, factor })),
    request.criteria,
  );
  const analyzed = collected.map(({ analyzed: a }) => {
    const s = stability.get(a.id);
    return s ? { ...a, stability: s } : a;
  });
  analyzed.sort((a, b) => Number(a.excluded !== undefined) - Number(b.excluded !== undefined) || b.total - a.total);
  return { mode: request.mode, sites: analyzed, sensitivity: describeMethod() };
}
