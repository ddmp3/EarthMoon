import { PARAM_IDS } from "../scoring/index.js";
import type { ParamId } from "../scoring/index.js";

/** Lunar reference value of a parameter (data/reference/moon-south-pole.json). */
export type MoonValue = { min?: number; max?: number; unit?: string; source?: string };

const isObject = (v: unknown): v is Record<string, unknown> => typeof v === "object" && v !== null && !Array.isArray(v);
const num = (v: unknown): number | undefined => (typeof v === "number" && Number.isFinite(v) ? v : undefined);
const str = (v: unknown): string | undefined => (typeof v === "string" ? v : undefined);

/**
 * Lunar values of the requested parameters, to show next to the Earth values.
 * A parameter without a sourced lunar reference is absent (never invented).
 */
export function moonValues(reference: unknown, params: readonly ParamId[]): Partial<Record<ParamId, MoonValue>> {
  const table = isObject(reference) && isObject(reference.params) ? reference.params : {};
  const out: Partial<Record<ParamId, MoonValue>> = {};
  for (const param of params) {
    const entry = table[param];
    if (!PARAM_IDS.includes(param) || !isObject(entry)) continue;
    const value: MoonValue = {};
    const min = num(entry.min);
    const max = num(entry.max);
    if (min === undefined && max === undefined) continue;
    if (min !== undefined) value.min = min;
    if (max !== undefined) value.max = max;
    const unit = str(entry.unit);
    if (unit !== undefined) value.unit = unit;
    const source = str(entry.source);
    if (source !== undefined) value.source = source;
    out[param] = value;
  }
  return out;
}
