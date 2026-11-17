import { assess } from "./score.js";
import type { Criterion, ParamId, ParamSigmas, ParamValues } from "./types.js";

/**
 * Rank and score uncertainty by Monte Carlo simulation (methodology v2).
 *
 * Two sources of uncertainty are propagated together, with one draw per scenario:
 * 1. the expert choices: weights, tolerances and interval bounds, none of which is calibrated;
 * 2. the data: every value that has a quantified 1-sigma uncertainty is redrawn from a normal distribution
 *    around its value, clipped to its physical range. Values without a quantified uncertainty are not
 *    perturbed, so the result is a lower bound of the real uncertainty.
 *
 * Deterministic (seeded) so a given request always gives the same answer.
 */

/** Relative spread applied to every weight (uniform, ±50%). */
export const WEIGHT_SPREAD = 0.5;
/** Relative spread applied to every tolerance (uniform, ±25%). */
export const TOLERANCE_SPREAD = 0.25;
/** Shift of the interval bounds, as a fraction of the tolerance (uniform, ±10%). */
export const BOUND_SHIFT = 0.1;
export const DEFAULT_RUNS = 500;
export const DEFAULT_SEED = 20261115;

/** Physical range of the parameters that have one; a perturbed value is clipped to it. */
export const PHYSICAL_RANGE: Partial<Record<ParamId, [number, number]>> = {
  slope_mean: [0, 90],
  slope_max: [0, 90],
  slope_p95: [0, 90],
  roughness: [0, Infinity],
  roughness_detrended: [0, Infinity],
  traversable_15: [0, 1],
  traversable_20: [0, 1],
  traversable_25: [0, 1],
  quake_count: [0, Infinity],
  quake_m45_count: [0, Infinity],
  wind: [0, Infinity],
  precipitation: [0, Infinity],
  humidity: [0, 100],
  specific_humidity: [0, Infinity],
  solar: [0, Infinity],
  latitude_abs: [0, 90],
  ndvi: [-1, 1],
};

export type SensitivityEntry = {
  id: string;
  values: ParamValues;
  /** Vegetation multiplier between 0 and 1 (1 if the filter is off). */
  factor: number;
  /** 1-sigma uncertainty of the values, when quantified. */
  sigmas?: ParamSigmas;
};

export type Stability = {
  /** 10th percentile of the rank over the scenarios (best case). */
  rankP10: number;
  rankMedian: number;
  /** 90th percentile of the rank (worst case). */
  rankP90: number;
  /** Share of scenarios (0 to 1) where the site stays in the top half of the ranked sites. */
  topHalfShare: number;
  /** 10th percentile of the total (0 to 100) over the scenarios. */
  totalP10: number;
  /** 90th percentile of the total (0 to 100) over the scenarios. */
  totalP90: number;
  /** Share of scenarios (0 to 1) where the site meets every hard requirement. */
  requirementsShare: number;
};

export type SensitivityMethod = {
  runs: number;
  seed: number;
  /** Plain-language description of what was varied. */
  perturbation: string;
};

/** Small seeded generator (mulberry32): same seed, same sequence. */
export function makeRandom(seed: number): () => number {
  let a = seed >>> 0;
  return () => {
    a = (a + 0x6d2b79f5) >>> 0;
    let t = a;
    t = Math.imul(t ^ (t >>> 15), t | 1);
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

/** Standard normal draw (Box-Muller) from a uniform generator. */
export function normal(random: () => number): number {
  const u = Math.max(random(), Number.MIN_VALUE);
  return Math.sqrt(-2 * Math.log(u)) * Math.cos(2 * Math.PI * random());
}

function perturb(criteria: Criterion[], random: () => number): Criterion[] {
  const around = (center: number, spread: number): number => center * (1 + spread * (2 * random() - 1));
  return criteria.map((c) => {
    const scale = 1 + TOLERANCE_SPREAD * (2 * random() - 1);
    const shift = BOUND_SHIFT * c.tolerance * (2 * random() - 1);
    const out: Criterion = { ...c, weight: around(c.weight, WEIGHT_SPREAD), tolerance: c.tolerance * scale };
    if (c.toleranceBelow !== undefined) out.toleranceBelow = c.toleranceBelow * scale;
    if (c.toleranceAbove !== undefined) out.toleranceAbove = c.toleranceAbove * scale;
    if (c.min !== undefined) out.min = c.min + shift;
    if (c.max !== undefined) out.max = c.max + shift;
    return out;
  });
}

/** Redraws the values that have a quantified uncertainty, for the parameters used by the criteria. */
export function perturbValues(
  values: ParamValues,
  sigmas: ParamSigmas | undefined,
  params: readonly ParamId[],
  random: () => number,
): ParamValues {
  if (!sigmas) return values;
  const out: ParamValues = { ...values };
  for (const param of params) {
    const value = values[param];
    const sigma = sigmas[param];
    if (typeof value !== "number" || typeof sigma !== "number" || !(sigma > 0)) continue;
    const [low, high] = PHYSICAL_RANGE[param] ?? [-Infinity, Infinity];
    out[param] = Math.min(high, Math.max(low, value + sigma * normal(random)));
  }
  return out;
}

function percentile(sorted: number[], p: number): number {
  return sorted[Math.min(sorted.length - 1, Math.max(0, Math.ceil(p * sorted.length) - 1))];
}

export function describeMethod(runs = DEFAULT_RUNS, seed = DEFAULT_SEED): SensitivityMethod {
  return {
    runs,
    seed,
    perturbation:
      `weights ±${WEIGHT_SPREAD * 100}%, tolerances ±${TOLERANCE_SPREAD * 100}%, interval bounds shifted by ±${BOUND_SHIFT * 100}% of the tolerance; ` +
      "site values with a quantified uncertainty redrawn from a normal distribution (1 sigma), clipped to their physical range",
  };
}

/**
 * Ranks the sites in each scenario (same perturbed criteria for all sites; independent data draws per site)
 * and summarizes, per site, where its rank and total fall. In a scenario, sites failing a hard requirement
 * rank after the others. Sites with factor 0 (excluded) are left out and always come last.
 */
export function rankStability(
  entries: SensitivityEntry[],
  criteria: Criterion[],
  runs = DEFAULT_RUNS,
  seed = DEFAULT_SEED,
): Map<string, Stability> {
  const ranked = entries.filter((e) => e.factor > 0);
  const n = ranked.length;
  const params = criteria.map((c) => c.param);
  const ranks = new Map<string, number[]>(ranked.map((e) => [e.id, []]));
  const totals = new Map<string, number[]>(ranked.map((e) => [e.id, []]));
  const passes = new Map<string, number>(ranked.map((e) => [e.id, 0]));
  const random = makeRandom(seed);
  for (let r = 0; r < runs; r++) {
    const scenario = perturb(criteria, random);
    ranked
      .map((e) => {
        const a = assess(perturbValues(e.values, e.sigmas, params, random), scenario);
        return { id: e.id, total: a.total * e.factor, failed: a.requirements === "failed" };
      })
      .sort((a, b) => Number(a.failed) - Number(b.failed) || b.total - a.total || (a.id < b.id ? -1 : 1))
      .forEach((e, i) => {
        ranks.get(e.id)?.push(i + 1);
        totals.get(e.id)?.push(e.total);
        if (!e.failed) passes.set(e.id, (passes.get(e.id) ?? 0) + 1);
      });
  }
  const half = Math.ceil(n / 2);
  const out = new Map<string, Stability>();
  for (const [id, list] of ranks) {
    const sorted = [...list].sort((a, b) => a - b);
    const sortedTotals = [...(totals.get(id) ?? [])].sort((a, b) => a - b);
    out.set(id, {
      rankP10: percentile(sorted, 0.1),
      rankMedian: percentile(sorted, 0.5),
      rankP90: percentile(sorted, 0.9),
      topHalfShare: Math.round((100 * sorted.filter((x) => x <= half).length) / sorted.length) / 100,
      totalP10: Math.round(percentile(sortedTotals, 0.1) * 10) / 10,
      totalP90: Math.round(percentile(sortedTotals, 0.9) * 10) / 10,
      requirementsShare: Math.round((100 * (passes.get(id) ?? 0)) / sorted.length) / 100,
    });
  }
  return out;
}
