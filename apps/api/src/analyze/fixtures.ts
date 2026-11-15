import { readFile } from "node:fs/promises";
import type { ParamValues } from "../scoring/index.js";
import type { Connector, Site } from "./analyze.js";

/**
 * Connecteur factice qui lit data/fixtures/site-values.json, pour brancher /api/analyze
 * avant l'arrivée des vrais connecteurs. À retirer source par source.
 * Les valeurs sont surtout fictives : ne jamais l'utiliser pour la démo.
 */

export type FixtureSite = Site & { values: ParamValues };
export type FixtureFile = { sites: FixtureSite[] };

const COORD_EPSILON = 1e-6;

export async function loadFixtures(path: string): Promise<FixtureFile> {
  const parsed: unknown = JSON.parse(await readFile(path, "utf8"));
  if (typeof parsed !== "object" || parsed === null || !Array.isArray((parsed as FixtureFile).sites)) {
    throw new Error(`Fichier de fixtures invalide : ${path}`);
  }
  return parsed as FixtureFile;
}

export function createFixtureConnector(fixtures: FixtureFile): Connector {
  return async ({ lat, lon }) => {
    const site = fixtures.sites.find(
      (s) => Math.abs(s.lat - lat) < COORD_EPSILON && Math.abs(s.lon - lon) < COORD_EPSILON,
    );
    return site ? { ...site.values } : {};
  };
}
