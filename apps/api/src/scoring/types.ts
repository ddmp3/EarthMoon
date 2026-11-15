/**
 * Shared types of the scoring engine.
 * The engine only knows the parameter catalog, never the sources.
 */

export const PARAM_IDS = [
  "slope_mean",
  "slope_max",
  "roughness",
  "elevation",
  "ndvi",
  "lst_day",
  "lst_night",
  "lst_amplitude",
  "t2m_mean",
  "t2m_min",
  "t2m_max",
  "wind",
  "humidity",
  "precipitation",
  "solar",
  "latitude_abs",
  "quake_count",
  "volcano_distance",
] as const;

export type ParamId = (typeof PARAM_IDS)[number];

/** Values of a site; `null` = source unavailable. */
export type ParamValues = Partial<Record<ParamId, number | null>>;

export type Criterion = {
  param: ParamId;
  min?: number;
  max?: number;
  tolerance: number;
  weight: number;
  /** Instrument (mode 2) or need (mode 3), to filter and group in the interface. */
  group?: string;
};

export type Verdict = "match" | "partial" | "mismatch" | "missing";

export type CriterionScore = {
  param: ParamId;
  value: number | null;
  /** Between 0 and 1. */
  score: number;
  verdict: Verdict;
};

export type SiteScore = {
  /** Out of 100, rounded to an integer. */
  total: number;
  criteria: CriterionScore[];
};
