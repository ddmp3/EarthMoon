import { readFile } from "node:fs/promises";
import type { ParamValues } from "../scoring/index.js";
import type { Connector, Site } from "./analyze.js";

/**
 * Fake connector reading data/fixtures/site-values.json, to wire up /api/analyze
 * before the real connectors existed. To be removed source by source.
 * The values are mostly fictional: never use it for the demo.
 */

export type FixtureSite = Site & { values: ParamValues };
export type FixtureFile = { sites: FixtureSite[] };

const COORD_EPSILON = 1e-6;

export async function loadFixtures(path: string): Promise<FixtureFile> {
  const parsed: unknown = JSON.parse(await readFile(path, "utf8"));
  if (typeof parsed !== "object" || parsed === null || !Array.isArray((parsed as FixtureFile).sites)) {
    throw new Error(`Invalid fixtures file : ${path}`);
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
