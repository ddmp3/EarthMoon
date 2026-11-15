import { access } from "node:fs/promises";
import path from "node:path";
import type { Connector } from "../analyze/analyze.js";
import { createFixtureConnector, loadFixtures } from "../analyze/fixtures.js";
import { withCache } from "./cache.js";
import { coordinatesConnector } from "./coordinates.js";
import { createGeometryConnector, loadGeometry } from "./geometry.js";
import { createPowerConnector } from "./power.js";
import { createUsgsConnector } from "./usgs.js";

export type SourceSet = { connectors: Connector[]; names: string[]; notes: string[] };

const exists = (p: string): Promise<boolean> =>
  access(p).then(
    () => true,
    () => false,
  );

/**
 * Assemble les connecteurs.
 * - Mode normal : NASA POWER + USGS (avec cache), géométrie précalculée si data/candidates-geometry.json existe.
 * - useFixtures : uniquement data/fixtures/site-values.json (valeurs surtout fictives, jamais pour la démo).
 * Sources pas encore branchées (listées dans `notes`) : MODIS (ndvi, lst_*), Smithsonian GVP (volcano_distance).
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
  const notes = ["MODIS (ndvi, lst_*) et Smithsonian GVP (volcano_distance) : pas encore branchés, ces critères seront « missing »"];
  const geometryFile = path.join(dataDir, "candidates-geometry.json");
  if (await exists(geometryFile)) {
    connectors.push(createGeometryConnector(await loadGeometry(geometryFile)));
    names.push("Copernicus DEM (précalculé)");
  } else {
    notes.push(`${geometryFile} absent : pente, rugosité et altitude seront « missing »`);
  }
  return { connectors, names, notes };
}
