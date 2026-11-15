import type { Criterion, CriterionScore, ParamValues, SiteScore, Verdict } from "./types.js";

export const MATCH_THRESHOLD = 0.7;
export const PARTIAL_THRESHOLD = 0.4;

/** Threshold of the common "bare soil" filter (docs/scenarios.md). */
export const NDVI_BARE_SOIL_MAX = 0.2;

/**
 * Score of a value for a criterion: 1 inside the [min, max] interval,
 * then a linear decrease down to 0 at `tolerance` distance.
 */
export function scoreValue(value: number, criterion: Criterion): number {
  const { min, max, tolerance } = criterion;
  let distance = 0;
  if (min !== undefined && value < min) distance = min - value;
  else if (max !== undefined && value > max) distance = value - max;
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
    return { param: criterion.param, value: null, score: 0, verdict: "missing" };
  }
  const score = scoreValue(raw, criterion);
  return { param: criterion.param, value: raw, score, verdict: verdictFor(score) };
}

/**
 * Overall site score: weighted mean of the criteria, out of 100.
 * A criterion with no value (source down) is excluded from the total so as not to
 * penalize the site because of a source; it stays visible with the "missing" verdict.
 */
export function scoreSite(values: ParamValues, criteria: Criterion[]): SiteScore {
  const scored = criteria.map((c) => scoreCriterion(values, c));
  let weighted = 0;
  let weights = 0;
  scored.forEach((s, i) => {
    if (s.verdict === "missing") return;
    weighted += criteria[i].weight * s.score;
    weights += criteria[i].weight;
  });
  const total = weights > 0 ? Math.round((100 * weighted) / weights) : 0;
  return { total, criteria: scored };
}

/** Common filter: true if the site is vegetated (NDVI known and > 0.2). */
export function isVegetated(values: ParamValues): boolean {
  const ndvi = values.ndvi;
  return typeof ndvi === "number" && ndvi > NDVI_BARE_SOIL_MAX;
}
