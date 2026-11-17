import { access } from "node:fs/promises";
import path from "node:path";
import type { Connector, SiteQuality } from "../analyze/analyze.js";
import { createDatasetConnector, createDatasetQuality, DATASET_FILE, loadDataset } from "./dataset.js";
import { createFixtureConnector, loadFixtures } from "../analyze/fixtures.js";
import { withCache } from "./cache.js";
import { coordinatesConnector } from "./coordinates.js";
import { createGvpConnector } from "./gvp.js";
import { createPowerConnector } from "./power.js";
import { createPrecomputedConnector, loadPrecomputed, PRECOMPUTED_FILE, PRECOMPUTED_PARAMS } from "./precomputed.js";
import { createUsgsConnector } from "./usgs.js";

export type SourceSet = {
  connectors: Connector[];
  names: string[];
  notes: string[];
  /** Uncertainties and flags of the values (frozen data set only). */
  quality?: (site: { lat: number; lon: number }) => SiteQuality | undefined;
  datasetVersion?: string;
};

const exists = (p: string): Promise<boolean> =>
  access(p).then(
    () => true,
    () => false,
  );

/**
 * Assembles the connectors.
 * - Frozen data set (data/dataset-v2.json present, the normal case): every value comes from the versioned
 *   file, nothing is read live, results are reproducible.
 * - Live fallback (no data set file): NASA POWER + USGS (cached), plus precomputed Copernicus DEM and MODIS if
 *   data/candidates-precomputed.json exists (produced by tools/precompute/).
 * - useFixtures: only data/fixtures/site-values.json (mostly fictional values, never for the demo).
 * Smithsonian GVP (volcano_distance): volcano list loaded once, distance computed locally.
 */
export async function buildSources(dataDir: string, useFixtures: boolean): Promise<SourceSet> {
  if (useFixtures) {
    const fixtures = await loadFixtures(path.join(dataDir, "fixtures", "site-values.json"));
    return {
      connectors: [coordinatesConnector, createFixtureConnector(fixtures)],
      names: ["coordinates", "fixtures (sample values)"],
      notes: ["USE_FIXTURES is on: sample values, not for the demo"],
    };
  }
  const datasetFile = path.join(dataDir, DATASET_FILE);
  if (await exists(datasetFile)) {
    const dataset = await loadDataset(datasetFile);
    return {
      connectors: [coordinatesConnector, createDatasetConnector(dataset)],
      names: ["coordinates", `frozen data set v${dataset.version} (NASA POWER, USGS, Smithsonian GVP, Copernicus DEM, MODIS)`],
      notes: [],
      quality: createDatasetQuality(dataset),
      datasetVersion: dataset.version,
    };
  }
  const connectors: Connector[] = [
    coordinatesConnector,
    withCache(createPowerConnector()),
    withCache(createUsgsConnector()),
    withCache(createGvpConnector()),
  ];
  const names = ["coordinates", "NASA POWER", "USGS Earthquake Catalog", "Smithsonian GVP"];
  const notes: string[] = [`${DATASET_FILE} is missing: sources are read live, results are not reproducible and v2 parameters will be "missing" (run tools/precompute/build_dataset.py)`];
  const precomputedFile = path.join(dataDir, PRECOMPUTED_FILE);
  if (await exists(precomputedFile)) {
    const sites = await loadPrecomputed(precomputedFile);
    connectors.push(createPrecomputedConnector(sites));
    const has = (keys: readonly string[]): boolean => sites.some((s) => keys.some((k) => typeof s.precomputed?.[k] === "number"));
    const parts = [has(PRECOMPUTED_PARAMS.slice(0, 4)) ? "Copernicus DEM" : null, has(PRECOMPUTED_PARAMS.slice(4)) ? "MODIS" : null].filter(Boolean);
    names.push(`${parts.length ? parts.join(" + ") : "values"} (precomputed)`);
    if (!parts.includes("MODIS")) notes.push(`${PRECOMPUTED_FILE} has no MODIS: ndvi and lst_* will be "missing", the "bare soil" filter excludes nothing`);
  } else {
    notes.push(`${precomputedFile} is missing: slope, roughness, elevation, ndvi and lst_* will be "missing" (run tools/precompute/)`);
  }
  return { connectors, names, notes };
}
