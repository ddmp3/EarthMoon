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
  // Methodology v2 (docs/SCIENTIFIC_METHODOLOGY.md)
  "slope_p95",
  "roughness_detrended",
  "traversable_15",
  "traversable_20",
  "traversable_25",
  "specific_humidity",
  "quake_m45_count",
  "lava_tube_evidence",
] as const;

export type ParamId = (typeof PARAM_IDS)[number];

/** Values of a site; `null` = no measurement (never a default value). */
export type ParamValues = Partial<Record<ParamId, number | null>>;

/** 1-sigma uncertainty of the values of a site; a parameter absent from the map has no quantified uncertainty. */
export type ParamSigmas = Partial<Record<ParamId, number>>;

/** Data-quality flags of the values of a site (e.g. "large_elevation_correction"). */
export type ParamFlags = Partial<Record<ParamId, string[]>>;

/**
 * What a criterion is for:
 * - similarity: the Earth value is compared with a measured lunar distribution;
 * - requirement: an operational need of the vehicle, instrument or mission (not a property of the Moon);
 * - proxy: an indirect Earth indicator of a lunar condition that cannot be reproduced or measured directly.
 */
export type CriterionRole = "similarity" | "requirement" | "proxy";

/** Where the interval and tolerance come from. Anything not measured or documented is an expert judgement. */
export type CriterionBasis = "lunar_measurement" | "mission_requirement" | "expert_judgement";

export type Criterion = {
  param: ParamId;
  min?: number;
  max?: number;
  /** Distance from the interval at which the score reaches 0 (both sides unless overridden below). */
  tolerance: number;
  /** Tolerance below `min`, when the two sides differ (e.g. taken from the lunar 5th percentile). */
  toleranceBelow?: number;
  /** Tolerance above `max`, when the two sides differ (e.g. taken from the lunar 95th percentile). */
  toleranceAbove?: number;
  weight: number;
  /**
   * Hard requirement: a site scoring 0 on it fails the scenario and is ranked after every site that passes,
   * whatever its total. It is never averaged away.
   */
  required?: boolean;
  /** Instrument (mode 2) or need (mode 3), to filter and group in the interface. */
  group?: string;
  role?: CriterionRole;
  basis?: CriterionBasis;
  /** Why the criterion is there and where its numbers come from. */
  rationale?: string;
};

export type Verdict = "match" | "partial" | "mismatch" | "missing";

export type CriterionScore = {
  param: ParamId;
  value: number | null;
  /** Between 0 and 1. */
  score: number;
  verdict: Verdict;
  /** Points (out of 100) this criterion adds to the total; 0 when missing. */
  contribution: number;
  /** Points (out of 100) this criterion could add at most, given the criteria that have data. */
  maxContribution: number;
  /** 1-sigma uncertainty of the value, when quantified. */
  sigma?: number;
  /** Data-quality flags of the value. */
  flags?: string[];
  required?: true;
};

/** Outcome of the hard requirements: "unknown" when a required criterion has no data. */
export type Requirements = "met" | "failed" | "unknown";

export type Assessment = {
  /** Unrounded weighted mean of the criteria that have data, 0 to 100. */
  total: number;
  /** Share of the total weight carried by criteria that have data, 0 to 1. */
  coverage: number;
  /** Total if every missing criterion scored 0 (0 to 100). */
  totalMin: number;
  /** Total if every missing criterion scored 1 (0 to 100). */
  totalMax: number;
  requirements: Requirements;
  /** Required criteria scoring 0. */
  failed: ParamId[];
  /** Criteria with no data. */
  missing: ParamId[];
  criteria: CriterionScore[];
};

export type SiteScore = {
  /** Out of 100, rounded to an integer. */
  total: number;
  criteria: CriterionScore[];
};
