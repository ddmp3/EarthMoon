import { weightedTotal } from "./score.js";
import type { Criterion, ParamValues } from "./types.js";

/**
 * Rank sensitivity: how much does a site's rank move if the expert choices (weights, tolerances,
 * interval bounds) are slightly wrong? None of them is calibrated against data, so the rank is
 * only as solid as this analysis says. Deterministic (seeded) so a given request always gives the same answer.
 */

/** Relative spread applied to every weight (uniform, ±50%). */
export const WEIGHT_SPREAD = 0.5;
/** Relative spread applied to every tolerance (uniform, ±25%). */
export const TOLERANCE_SPREAD = 0.25;
/** Shift of the interval bounds, as a fraction of the tolerance (uniform, ±10%). */
export const BOUND_SHIFT = 0.1;
export const DEFAULT_RUNS = 500;
export const DEFAULT_SEED = 20261115;

export type SensitivityEntry = {
  id: string;
  values: ParamValues;
  /** Vegetation multiplier between 0 and 1 (1 if the filter is off). */
  factor: number;
};

export type Stability = {
  /** 10th percentile of the rank over the scenarios (best case). */
  rankP10: number;
  rankMedian: number;
  /** 90th percentile of the rank (worst case). */
  rankP90: number;
  /** Share of scenarios (0 to 1) where the site stays in the top half of the ranked sites. */
  topHalfShare: number;
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

function perturb(criteria: Criterion[], random: () => number): Criterion[] {
  const around = (center: number, spread: number): number => center * (1 + spread * (2 * random() - 1));
  return criteria.map((c) => {
    const tolerance = around(c.tolerance, TOLERANCE_SPREAD);
    const shift = BOUND_SHIFT * c.tolerance * (2 * random() - 1);
    const out: Criterion = { ...c, weight: around(c.weight, WEIGHT_SPREAD), tolerance };
    if (c.min !== undefined) out.min = c.min + shift;
    if (c.max !== undefined) out.max = c.max + shift;
    return out;
  });
}

function percentile(sorted: number[], p: number): number {
  return sorted[Math.min(sorted.length - 1, Math.max(0, Math.ceil(p * sorted.length) - 1))];
}

export function describeMethod(runs = DEFAULT_RUNS, seed = DEFAULT_SEED): SensitivityMethod {
  return {
    runs,
    seed,
    perturbation: `weights ±${WEIGHT_SPREAD * 100}%, tolerances ±${TOLERANCE_SPREAD * 100}%, interval bounds shifted by ±${BOUND_SHIFT * 100}% of the tolerance`,
  };
}

/**
 * Ranks the sites in each perturbed scenario (same perturbation for all sites in a scenario) and summarizes,
 * per site, where its rank falls. Sites with factor 0 (excluded) are left out and always come last.
 */
export function rankStability(
  entries: SensitivityEntry[],
  criteria: Criterion[],
  runs = DEFAULT_RUNS,
  seed = DEFAULT_SEED,
): Map<string, Stability> {
  const ranked = entries.filter((e) => e.factor > 0);
  const n = ranked.length;
  const ranks = new Map<string, number[]>(ranked.map((e) => [e.id, []]));
  const random = makeRandom(seed);
  for (let r = 0; r < runs; r++) {
    const scenario = perturb(criteria, random);
    ranked
      .map((e) => ({ id: e.id, total: weightedTotal(e.values, scenario) * e.factor }))
      .sort((a, b) => b.total - a.total || (a.id < b.id ? -1 : 1))
      .forEach((e, i) => ranks.get(e.id)?.push(i + 1));
  }
  const half = Math.ceil(n / 2);
  const out = new Map<string, Stability>();
  for (const [id, list] of ranks) {
    const sorted = [...list].sort((a, b) => a - b);
    out.set(id, {
      rankP10: percentile(sorted, 0.1),
      rankMedian: percentile(sorted, 0.5),
      rankP90: percentile(sorted, 0.9),
      topHalfShare: Math.round((100 * sorted.filter((x) => x <= half).length) / sorted.length) / 100,
    });
  }
  return out;
}
