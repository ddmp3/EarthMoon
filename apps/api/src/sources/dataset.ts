import { readFile } from "node:fs/promises";
import type { Connector, SiteQuality } from "../analyze/analyze.js";
import { PARAM_IDS } from "../scoring/index.js";
import type { ParamFlags, ParamId, ParamSigmas, ParamValues } from "../scoring/index.js";

/**
 * Frozen, versioned data set (data/dataset-v2.json, built by tools/precompute/build_dataset.py).
 *
 * Every value of every site comes from this file: terrain on the lunar grid, MODIS, and the NASA POWER,
 * USGS and Smithsonian GVP values frozen on a known date. Nothing is read live, so a given version of the
 * file always gives the same scores. Each value carries its 1-sigma uncertainty (when quantified) and its
 * data-quality flags.
 */
export const DATASET_FILE = "dataset-v2.json";

type Entry = { value?: unknown; sigma?: unknown; flags?: unknown };
type DatasetSite = { lat: number; lon: number; values?: Record<string, Entry> };
export type Dataset = { version: string; sites: DatasetSite[] };

const COORD_EPSILON = 1e-6;
const isFiniteNumber = (v: unknown): v is number => typeof v === "number" && Number.isFinite(v);

export async function loadDataset(path: string): Promise<Dataset> {
  const parsed = JSON.parse(await readFile(path, "utf8")) as { version?: unknown; sites?: unknown } | null;
  if (typeof parsed?.version !== "string" || typeof parsed.sites !== "object" || parsed.sites === null) {
    throw new Error(`Invalid data set file : ${path}`);
  }
  const sites = Object.values(parsed.sites as Record<string, DatasetSite>).filter(
    (s) => isFiniteNumber(s?.lat) && isFiniteNumber(s?.lon),
  );
  return { version: parsed.version, sites };
}

function find(dataset: Dataset, lat: number, lon: number): DatasetSite | undefined {
  return dataset.sites.find((s) => Math.abs(s.lat - lat) < COORD_EPSILON && Math.abs(s.lon - lon) < COORD_EPSILON);
}

/** Values of the site; a parameter with no measurement is null ("missing"), never a default. */
export function createDatasetConnector(dataset: Dataset): Connector {
  return async ({ lat, lon }) => {
    const site = find(dataset, lat, lon);
    const out: ParamValues = {};
    if (!site?.values) return out;
    for (const param of PARAM_IDS) {
      const entry = site.values[param];
      if (entry === undefined) continue;
      out[param] = isFiniteNumber(entry.value) ? entry.value : null;
    }
    return out;
  };
}

/** Uncertainties and flags of the site's values. */
export function createDatasetQuality(dataset: Dataset): (site: { lat: number; lon: number }) => SiteQuality | undefined {
  return ({ lat, lon }) => {
    const site = find(dataset, lat, lon);
    if (!site?.values) return undefined;
    const sigmas: ParamSigmas = {};
    const flags: ParamFlags = {};
    for (const param of PARAM_IDS as readonly ParamId[]) {
      const entry = site.values[param];
      if (entry === undefined) continue;
      if (isFiniteNumber(entry.sigma)) sigmas[param] = entry.sigma;
      if (Array.isArray(entry.flags)) {
        const list = entry.flags.filter((f): f is string => typeof f === "string");
        if (list.length > 0) flags[param] = list;
      }
    }
    return { sigmas, flags };
  };
}
