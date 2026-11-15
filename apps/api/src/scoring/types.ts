/**
 * Types partagés du moteur de score (docs/contrats.md §3 et §4).
 * Le moteur ne connaît que le catalogue des paramètres, jamais les sources.
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

/** Valeurs d'un site ; `null` = source indisponible. */
export type ParamValues = Partial<Record<ParamId, number | null>>;

export type Criterion = {
  param: ParamId;
  min?: number;
  max?: number;
  tolerance: number;
  weight: number;
  /** Instrument (mode 2) ou besoin (mode 3), pour filtrer et grouper dans l'interface. */
  group?: string;
};

export type Verdict = "match" | "partial" | "mismatch" | "missing";

export type CriterionScore = {
  param: ParamId;
  value: number | null;
  /** Entre 0 et 1. */
  score: number;
  verdict: Verdict;
};

export type SiteScore = {
  /** Sur 100, arrondi à l'entier. */
  total: number;
  criteria: CriterionScore[];
};
