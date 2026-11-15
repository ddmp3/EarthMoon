import { readFile } from "node:fs/promises";
import type { Connector } from "../analyze/analyze.js";
import type { ParamValues } from "../scoring/index.js";

/**
 * Géométrie du terrain (Copernicus DEM) précalculée hors ligne par tools/precompute/enrich_candidates.py.
 * Le fichier est la liste des sites candidats avec un bloc `precomputed` (mêmes identifiants que le catalogue).
 * Le connecteur retrouve le site par ses coordonnées, comme le connecteur de fixtures.
 */
export const GEOMETRY_PARAMS = ["slope_mean", "slope_max", "roughness", "elevation"] as const;

type PrecomputedSite = { id?: string; lat: number; lon: number; precomputed?: Record<string, unknown> };

const COORD_EPSILON = 1e-6;

export async function loadGeometry(path: string): Promise<PrecomputedSite[]> {
  const parsed: unknown = JSON.parse(await readFile(path, "utf8"));
  const list = Array.isArray(parsed) ? parsed : (parsed as { sites?: unknown } | null)?.sites;
  if (!Array.isArray(list)) throw new Error(`Fichier de géométrie invalide : ${path}`);
  return list as PrecomputedSite[];
}

export function createGeometryConnector(sites: PrecomputedSite[]): Connector {
  return async ({ lat, lon }) => {
    const site = sites.find((s) => Math.abs(s.lat - lat) < COORD_EPSILON && Math.abs(s.lon - lon) < COORD_EPSILON);
    const out: ParamValues = {};
    if (!site?.precomputed) return out;
    for (const param of GEOMETRY_PARAMS) {
      const value = site.precomputed[param];
      out[param] = typeof value === "number" && Number.isFinite(value) ? value : null;
    }
    return out;
  };
}
