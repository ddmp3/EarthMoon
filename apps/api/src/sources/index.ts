import { access } from "node:fs/promises";
import path from "node:path";
import type { Connector } from "../analyze/analyze.js";
import { createFixtureConnector, loadFixtures } from "../analyze/fixtures.js";
import { withCache } from "./cache.js";
import { coordinatesConnector } from "./coordinates.js";
import { createGvpConnector } from "./gvp.js";
import { createPowerConnector } from "./power.js";
import { createPrecomputedConnector, loadPrecomputed, PRECOMPUTED_FILE, PRECOMPUTED_PARAMS } from "./precomputed.js";
import { createUsgsConnector } from "./usgs.js";

export type SourceSet = { connectors: Connector[]; names: string[]; notes: string[] };

const exists = (p: string): Promise<boolean> =>
  access(p).then(
    () => true,
    () => false,
  );

/**
 * Assembles the connectors.
 * - Normal mode: NASA POWER + USGS (cached), plus precomputed Copernicus DEM and MODIS if
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
  const connectors: Connector[] = [
    coordinatesConnector,
    withCache(createPowerConnector()),
    withCache(createUsgsConnector()),
    withCache(createGvpConnector()),
  ];
  const names = ["coordinates", "NASA POWER", "USGS Earthquake Catalog", "Smithsonian GVP"];
  const notes: string[] = [];
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
