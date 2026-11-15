import { readFile } from "node:fs/promises";
import type { Connector } from "../analyze/analyze.js";
import type { ParamValues } from "../scoring/index.js";

/**
 * Values precomputed offline by tools/precompute/ (Python):
 * - enrich_candidates.py : Copernicus DEM geometry (slope_mean, slope_max, roughness, elevation) ;
 * - modis_values.py      : MODIS via Planetary Computer (ndvi, lst_day, lst_night, lst_amplitude).
 * The file is the candidate site list with a `precomputed` block (catalog identifiers).
 * The connector finds the site by its coordinates, like the fixtures connector.
 */
export const PRECOMPUTED_FILE = "candidates-precomputed.json";

export const PRECOMPUTED_PARAMS = [
  "slope_mean",
  "slope_max",
  "roughness",
  "elevation",
  "ndvi",
  "lst_day",
  "lst_night",
  "lst_amplitude",
] as const;

type PrecomputedSite = { id?: string; lat: number; lon: number; precomputed?: Record<string, unknown> };

const COORD_EPSILON = 1e-6;

export async function loadPrecomputed(path: string): Promise<PrecomputedSite[]> {
  const parsed: unknown = JSON.parse(await readFile(path, "utf8"));
  const list = Array.isArray(parsed) ? parsed : (parsed as { sites?: unknown } | null)?.sites;
  if (!Array.isArray(list)) throw new Error(`Invalid precomputed values file : ${path}`);
  return list as PrecomputedSite[];
}

/** Only returns the parameters present in the block; a non-numeric value becomes null (criterion "missing"). */
export function createPrecomputedConnector(sites: PrecomputedSite[]): Connector {
  return async ({ lat, lon }) => {
    const site = sites.find((s) => Math.abs(s.lat - lat) < COORD_EPSILON && Math.abs(s.lon - lon) < COORD_EPSILON);
    const out: ParamValues = {};
    if (!site?.precomputed) return out;
    for (const param of PRECOMPUTED_PARAMS) {
      if (!(param in site.precomputed)) continue;
      const value = site.precomputed[param];
      out[param] = typeof value === "number" && Number.isFinite(value) ? value : null;
    }
    return out;
  };
}
