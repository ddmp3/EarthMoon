import { assess, describeMethod, rankStability, vegetationFactor } from "../scoring/index.js";
import type {
  CriterionScore,
  ParamFlags,
  ParamId,
  ParamSigmas,
  ParamValues,
  Requirements,
  SensitivityMethod,
  Stability,
} from "../scoring/index.js";
import { resolveRequest } from "./validate.js";

/** Version of the scoring method (docs/METHOD.md). Bump on any change that can move a score. */
export const METHODOLOGY_VERSION = "2.0.0";

/** Coverage under which an assessment is labelled "low" confidence. */
export const LOW_COVERAGE = 0.6;
/** Coverage from which an assessment can be labelled "high" confidence. */
export const HIGH_COVERAGE = 0.9;
/** Width of the 10th to 90th percentile interval of the total above which confidence is "low". */
export const WIDE_INTERVAL = 30;
/** Width of that interval up to which confidence can be "high". */
export const NARROW_INTERVAL = 15;

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

/** Uncertainties and data-quality flags of the values of a site, when the data set provides them. */
export type SiteQuality = { sigmas: ParamSigmas; flags: ParamFlags };

/**
 * How much the assessment itself can be trusted, kept separate from the score:
 * a site can score high with low confidence (few data, wide interval) or low with high confidence.
 */
export type Confidence = "high" | "medium" | "low";

export type AnalyzedSite = Pick<Site, "id" | "name" | "lat" | "lon" | "role"> & {
  total: number;
  criteria: CriterionScore[];
  /** Present if the site is excluded by the "bare soil" filter (dense vegetation: total forced to 0). */
  excluded?: "vegetation";
  /** Present if the filter reduced the total (NDVI between 0.2 and 0.6): multiplier between 0 and 1. */
  vegetationFactor?: number;
  /** Rank and total under perturbed expert choices and data (absent for excluded sites). */
  stability?: Stability;
  /** Share of the criteria weight that has data (0 to 1). */
  coverage: number;
  /** Total if every missing criterion scored 0, and if it scored 1 (vegetation factor applied). */
  totalRange: { min: number; max: number };
  /** Hard requirements of the scenario: met, failed, or unknown (a required criterion has no data). */
  requirements: Requirements;
  /** Required criteria the site fails. */
  failedRequirements?: ParamId[];
  /** Criteria with no data for this site. */
  missing?: ParamId[];
  /** Confidence in the assessment (absent for excluded sites). */
  confidence?: Confidence;
};

export type AnalyzeResponse = {
  mode: string;
  sites: AnalyzedSite[];
  /** How `stability` was computed. */
  sensitivity: SensitivityMethod;
  /** Versions needed to reproduce the result. */
  methodology: { version: string; dataset?: string };
};

export type AnalyzeDeps = {
  sites: Site[];
  connectors: Connector[];
  /** Maximum number of sites queried in parallel. */
  concurrency?: number;
  onConnectorError?: (error: unknown, site: Site) => void;
  /** Uncertainties and flags of a site's values (frozen data set); absent in live or fixtures mode. */
  quality?: (site: { lat: number; lon: number }) => SiteQuality | undefined;
  /** Version of the frozen data set, reported with every result. */
  datasetVersion?: string;
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

/** Confidence label from coverage, requirements and the width of the total's 10th to 90th percentile interval. */
export function confidenceOf(coverage: number, requirements: Requirements, intervalWidth: number): Confidence {
  if (coverage < LOW_COVERAGE || requirements === "unknown" || intervalWidth > WIDE_INTERVAL) return "low";
  if (coverage >= HIGH_COVERAGE && intervalWidth <= NARROW_INTERVAL) return "high";
  return "medium";
}

/** Sort order of a requirement outcome: sites that fail a hard requirement come after the others. */
const requirementOrder = (site: AnalyzedSite): number => (site.requirements === "failed" ? 1 : 0);

/** Core of POST /api/analyze: validates the request, collects values, scores and sorts the sites. */
export async function analyze(body: unknown, deps: AnalyzeDeps): Promise<AnalyzeResponse> {
  const request = resolveRequest(body);
  const collected = await mapWithConcurrency(deps.sites, deps.concurrency ?? 8, async (site) => {
    const values = await collectValues(site, deps.connectors, deps.onConnectorError);
    const quality = deps.quality?.(site);
    const factor = request.bareSoilOnly ? vegetationFactor(values) : 1;
    const a = assess(values, request.criteria, quality?.sigmas, quality?.flags);
    const analyzed: AnalyzedSite = {
      id: site.id,
      name: site.name,
      lat: site.lat,
      lon: site.lon,
      role: site.role,
      criteria: a.criteria,
      total: factor === 0 ? 0 : Math.round(a.total * factor),
      ...(factor === 0 ? { excluded: "vegetation" as const } : {}),
      ...(factor > 0 && factor < 1 ? { vegetationFactor: Math.round(factor * 100) / 100 } : {}),
      coverage: Math.round(a.coverage * 100) / 100,
      totalRange: { min: Math.round(a.totalMin * factor), max: Math.round(a.totalMax * factor) },
      requirements: a.requirements,
      ...(a.failed.length > 0 ? { failedRequirements: a.failed } : {}),
      ...(a.missing.length > 0 ? { missing: a.missing } : {}),
    };
    return { analyzed, values, factor, sigmas: quality?.sigmas };
  });
  const stability = rankStability(
    collected.map(({ analyzed, values, factor, sigmas }) => ({ id: analyzed.id, values, factor, ...(sigmas ? { sigmas } : {}) })),
    request.criteria,
  );
  const analyzed = collected.map(({ analyzed: a }) => {
    const s = stability.get(a.id);
    if (!s) return a;
    return { ...a, stability: s, confidence: confidenceOf(a.coverage, a.requirements, s.totalP90 - s.totalP10) };
  });
  analyzed.sort(
    (a, b) =>
      Number(a.excluded !== undefined) - Number(b.excluded !== undefined) ||
      requirementOrder(a) - requirementOrder(b) ||
      b.total - a.total,
  );
  return {
    mode: request.mode,
    sites: analyzed,
    sensitivity: describeMethod(),
    methodology: { version: METHODOLOGY_VERSION, ...(deps.datasetVersion ? { dataset: deps.datasetVersion } : {}) },
  };
}
