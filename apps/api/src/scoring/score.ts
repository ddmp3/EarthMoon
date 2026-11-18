import type {
  Assessment,
  Criterion,
  CriterionScore,
  ParamFlags,
  ParamId,
  ParamSigmas,
  ParamValues,
  SiteScore,
  Verdict,
} from "./types.js";

export const MATCH_THRESHOLD = 0.7;
export const PARTIAL_THRESHOLD = 0.4;

/** Threshold of the common "bare soil" filter (docs/METHOD.md): up to here, no penalty. */
export const NDVI_BARE_SOIL_MAX = 0.2;

/**
 * NDVI at which the penalty reaches 100%: dense vegetation by the usual remote-sensing convention
 * (sparse vegetation ~0.2-0.5, dense > 0.6). Between the two the penalty is linear, like any tolerance.
 */
export const NDVI_DENSE_VEGETATION = 0.6;

/**
 * Score of a value for a criterion: 1 inside the [min, max] interval, then a linear decrease down to 0 at
 * the tolerance distance. The tolerance can differ below and above the interval (toleranceBelow /
 * toleranceAbove), which lets a criterion follow an asymmetric lunar distribution.
 */
export function scoreValue(value: number, criterion: Criterion): number {
  const { min, max } = criterion;
  let distance = 0;
  let tolerance = criterion.tolerance;
  if (min !== undefined && value < min) {
    distance = min - value;
    tolerance = criterion.toleranceBelow ?? criterion.tolerance;
  } else if (max !== undefined && value > max) {
    distance = value - max;
    tolerance = criterion.toleranceAbove ?? criterion.tolerance;
  }
  if (distance === 0) return 1;
  if (tolerance <= 0) return 0;
  return Math.max(0, 1 - distance / tolerance);
}

export function verdictFor(score: number): Exclude<Verdict, "missing"> {
  if (score >= MATCH_THRESHOLD) return "match";
  if (score >= PARTIAL_THRESHOLD) return "partial";
  return "mismatch";
}

export function scoreCriterion(values: ParamValues, criterion: Criterion): CriterionScore {
  const raw = values[criterion.param];
  if (raw === undefined || raw === null || !Number.isFinite(raw)) {
    return { param: criterion.param, value: null, score: 0, verdict: "missing", contribution: 0, maxContribution: 0 };
  }
  const score = scoreValue(raw, criterion);
  return { param: criterion.param, value: raw, score, verdict: verdictFor(score), contribution: 0, maxContribution: 0 };
}

/**
 * Full assessment of a site for a set of criteria (methodology v2):
 * - total: weighted mean of the criteria that have data (a missing value is neither good nor bad);
 * - coverage and bounds: how much of the weight has data, and what the total would be if every missing
 *   criterion scored 0 (totalMin) or 1 (totalMax), so that a poorly documented site is visible as such;
 * - requirements: a required criterion scoring 0 fails the scenario; with no data the outcome is unknown;
 * - contribution: points each criterion adds to the total, to explain the result.
 */
export function assess(
  values: ParamValues,
  criteria: Criterion[],
  sigmas: ParamSigmas = {},
  flags: ParamFlags = {},
): Assessment {
  const scored = criteria.map((c) => scoreCriterion(values, c));
  let weighted = 0;
  let known = 0;
  let all = 0;
  const failed: ParamId[] = [];
  const missing: ParamId[] = [];
  let requiredUnknown = false;
  criteria.forEach((c, i) => {
    all += c.weight;
    const s = scored[i];
    if (c.required) s.required = true;
    if (s.verdict === "missing") {
      missing.push(c.param);
      if (c.required) requiredUnknown = true;
      return;
    }
    known += c.weight;
    weighted += c.weight * s.score;
    if (c.required && s.score === 0) failed.push(c.param);
    const sigma = sigmas[c.param];
    if (typeof sigma === "number" && Number.isFinite(sigma)) s.sigma = sigma;
    const f = flags[c.param];
    if (f && f.length > 0) s.flags = f;
  });
  criteria.forEach((c, i) => {
    const s = scored[i];
    if (s.verdict === "missing" || known === 0) return;
    s.maxContribution = (100 * c.weight) / known;
    s.contribution = s.maxContribution * s.score;
  });
  return {
    total: known > 0 ? (100 * weighted) / known : 0,
    coverage: all > 0 ? known / all : 0,
    totalMin: all > 0 ? (100 * weighted) / all : 0,
    totalMax: all > 0 ? (100 * (weighted + (all - known))) / all : 0,
    requirements: failed.length > 0 ? "failed" : requiredUnknown ? "unknown" : "met",
    failed,
    missing,
    criteria: scored,
  };
}

/**
 * Unrounded weighted mean of the criteria, between 0 and 100.
 * A criterion with no value is excluded from the mean so as not to penalize (or favour) the site because
 * of a source; it stays visible with the "missing" verdict, and `assess` reports the coverage.
 */
export function weightedTotal(values: ParamValues, criteria: Criterion[]): number {
  return assess(values, criteria).total;
}

/** Overall site score: weighted mean of the criteria, out of 100, rounded. */
export function scoreSite(values: ParamValues, criteria: Criterion[]): SiteScore {
  const a = assess(values, criteria);
  return { total: Math.round(a.total), criteria: a.criteria };
}

/** Common filter: true if the site is vegetated (NDVI known and > 0.2). */
export function isVegetated(values: ParamValues): boolean {
  const ndvi = values.ndvi;
  return typeof ndvi === "number" && ndvi > NDVI_BARE_SOIL_MAX;
}

/**
 * Multiplier applied to the total of a vegetated site: 1 up to NDVI 0.2, linear decrease to 0 at NDVI 0.6.
 * A single-point NDVI can misrepresent a large site (ring lake, forested rim), so the filter degrades the score
 * gradually instead of dropping the site; only dense vegetation (factor 0) is excluded.
 */
export function vegetationFactor(values: ParamValues): number {
  const ndvi = values.ndvi;
  if (typeof ndvi !== "number" || !Number.isFinite(ndvi)) return 1;
  return scoreValue(ndvi, { param: "ndvi", max: NDVI_BARE_SOIL_MAX, tolerance: NDVI_DENSE_VEGETATION - NDVI_BARE_SOIL_MAX, weight: 1 });
}
