import { access } from "node:fs/promises";
import path from "node:path";
import type { Connector } from "../analyze/analyze.js";
import { createFixtureConnector, loadFixtures } from "../analyze/fixtures.js";
import { withCache } from "./cache.js";
import { coordinatesConnector } from "./coordinates.js";
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
 * Assemble les connecteurs.
 * - Mode normal : NASA POWER + USGS (avec cache), plus Copernicus DEM et MODIS précalculés si
 *   data/candidates-precomputed.json existe (produit par tools/precompute/).
 * - useFixtures : uniquement data/fixtures/site-values.json (valeurs surtout fictives, jamais pour la démo).
 * Source pas encore branchée (listée dans `notes`) : Smithsonian GVP (volcano_distance).
 */
export async function buildSources(dataDir: string, useFixtures: boolean): Promise<SourceSet> {
  if (useFixtures) {
    const fixtures = await loadFixtures(path.join(dataDir, "fixtures", "site-values.json"));
    return {
      connectors: [coordinatesConnector, createFixtureConnector(fixtures)],
      names: ["coordonnées", "fixtures (valeurs d'exemple)"],
      notes: ["USE_FIXTURES actif : valeurs d'exemple, pas pour la démo"],
    };
  }
  const connectors: Connector[] = [coordinatesConnector, withCache(createPowerConnector()), withCache(createUsgsConnector())];
  const names = ["coordonnées", "NASA POWER", "USGS Earthquake Catalog"];
  const notes = ["Smithsonian GVP (volcano_distance) : pas encore branché, ce critère sera « missing »"];
  const precomputedFile = path.join(dataDir, PRECOMPUTED_FILE);
  if (await exists(precomputedFile)) {
    const sites = await loadPrecomputed(precomputedFile);
    connectors.push(createPrecomputedConnector(sites));
    const has = (keys: readonly string[]): boolean => sites.some((s) => keys.some((k) => typeof s.precomputed?.[k] === "number"));
    const parts = [has(PRECOMPUTED_PARAMS.slice(0, 4)) ? "Copernicus DEM" : null, has(PRECOMPUTED_PARAMS.slice(4)) ? "MODIS" : null].filter(Boolean);
    names.push(`${parts.length ? parts.join(" + ") : "valeurs"} (précalculé)`);
    if (!parts.includes("MODIS")) notes.push(`${PRECOMPUTED_FILE} sans MODIS : ndvi et lst_* seront « missing », le filtre « sol nu » n'écarte rien`);
  } else {
    notes.push(`${precomputedFile} absent : pente, rugosité, altitude, ndvi et lst_* seront « missing » (lancer tools/precompute/)`);
  }
  return { connectors, names, notes };
}
