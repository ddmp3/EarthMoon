import { isModeId, MODES, PARAM_IDS } from "../scoring/index.js";
import type { Criterion, ModeId, ParamId } from "../scoring/index.js";

/** POST /api/analyze request (see openapi.yaml). */
export type AnalyzeRequest = {
  mode?: ModeId;
  criteria?: Criterion[];
  /** "Bare soil" filter (NDVI ≤ 0.2); on by default, can be disabled in mode 4. */
  bareSoilOnly?: boolean;
};

export type ResolvedRequest = {
  mode: ModeId | "custom";
  criteria: Criterion[];
  bareSoilOnly: boolean;
};

export class ValidationError extends Error {
  constructor(message: string) {
    super(message);
    this.name = "ValidationError";
  }
}

const MAX_CRITERIA = PARAM_IDS.length;

function isParamId(value: unknown): value is ParamId {
  return typeof value === "string" && (PARAM_IDS as readonly string[]).includes(value);
}

function optionalFinite(value: unknown, field: string): number | undefined {
  if (value === undefined || value === null) return undefined;
  if (typeof value !== "number" || !Number.isFinite(value)) {
    throw new ValidationError(`${field} must be a number`);
  }
  return value;
}

function parseCriterion(raw: unknown, index: number): Criterion {
  if (typeof raw !== "object" || raw === null) {
    throw new ValidationError(`criteria[${index}] must be an object`);
  }
  const c = raw as Record<string, unknown>;
  const at = `criteria[${index}]`;
  if (!isParamId(c.param)) throw new ValidationError(`${at}.param is unknown: ${String(c.param)}`);
  const min = optionalFinite(c.min, `${at}.min`);
  const max = optionalFinite(c.max, `${at}.max`);
  const tolerance = optionalFinite(c.tolerance, `${at}.tolerance`);
  const weight = optionalFinite(c.weight, `${at}.weight`);
  if (min === undefined && max === undefined) {
    throw new ValidationError(`${at} must have min, max or both`);
  }
  if (min !== undefined && max !== undefined && min > max) {
    throw new ValidationError(`${at}.min must be less than or equal to max`);
  }
  if (tolerance === undefined || tolerance < 0) {
    throw new ValidationError(`${at}.tolerance must be a non-negative number`);
  }
  if (weight === undefined || weight <= 0) {
    throw new ValidationError(`${at}.weight must be a strictly positive number`);
  }
  const criterion: Criterion = { param: c.param, tolerance, weight };
  if (min !== undefined) criterion.min = min;
  if (max !== undefined) criterion.max = max;
  return criterion;
}

/** Validates the request body and turns it into the criteria to apply. */
export function resolveRequest(body: unknown): ResolvedRequest {
  if (typeof body !== "object" || body === null) {
    throw new ValidationError("The body must be a JSON object");
  }
  const b = body as Record<string, unknown>;
  if (b.bareSoilOnly !== undefined && typeof b.bareSoilOnly !== "boolean") {
    throw new ValidationError("bareSoilOnly must be a boolean");
  }
  const bareSoilOnly = b.bareSoilOnly !== false;
  const hasMode = b.mode !== undefined;
  const hasCriteria = b.criteria !== undefined;
  if (hasMode === hasCriteria) {
    throw new ValidationError("Provide either mode or criteria");
  }
  if (hasMode) {
    if (!isModeId(b.mode)) throw new ValidationError(`Unknown mode: ${String(b.mode)}`);
    return { mode: b.mode, criteria: MODES[b.mode].criteria, bareSoilOnly };
  }
  if (!Array.isArray(b.criteria) || b.criteria.length === 0 || b.criteria.length > MAX_CRITERIA) {
    throw new ValidationError(`criteria must contain between 1 and ${MAX_CRITERIA} criteria`);
  }
  const criteria = b.criteria.map(parseCriterion);
  const params = new Set(criteria.map((c) => c.param));
  if (params.size !== criteria.length) {
    throw new ValidationError("A parameter can only appear once in criteria");
  }
  return { mode: "custom", criteria, bareSoilOnly };
}
