import { readFile } from "node:fs/promises";
import path from "node:path";
import { parse } from "yaml";
import type { Site } from "../analyze/analyze.js";
import { loadFixtures } from "../analyze/fixtures.js";
import { API_ROOT } from "./config.js";

const ROLES = ["validation", "negative", "candidate"] as const;

/** Validates a list of sites (see docs/ARCHITECTURE.md, data files). Invalid entries are skipped and reported. */
export function parseSites(raw: unknown, onSkip?: (reason: string) => void): Site[] {
  const list = Array.isArray(raw) ? raw : (raw as { sites?: unknown } | null)?.sites;
  if (!Array.isArray(list)) throw new Error("The site list must be an array (or { sites: [...] })");
  const sites: Site[] = [];
  const seen = new Set<string>();
  list.forEach((entry: unknown, index) => {
    const s = entry as Partial<Site> | null;
    const problem =
      typeof s?.id !== "string" || !/^[a-z0-9-]+$/.test(s.id)
        ? "missing or invalid id"
        : seen.has(s.id)
          ? "duplicate id"
          : typeof s.name !== "string"
            ? "missing name"
            : typeof s.lat !== "number" || s.lat < -90 || s.lat > 90
              ? "invalid lat"
              : typeof s.lon !== "number" || s.lon < -180 || s.lon > 180
                ? "invalid lon"
                : undefined;
    if (problem || !s || typeof s.id !== "string" || typeof s.name !== "string") {
      onSkip?.(`site #${index} skipped: ${problem ?? "invalid"}`);
      return;
    }
    seen.add(s.id);
    sites.push({
      id: s.id,
      name: s.name,
      lat: s.lat as number,
      lon: s.lon as number,
      ...(typeof s.terrain === "string" ? { terrain: s.terrain } : {}),
      role: ROLES.includes(s.role as (typeof ROLES)[number]) ? (s.role as Site["role"]) : "candidate",
    });
  });
  return sites;
}

/**
 * Sites queried: data/candidates.json if it exists, otherwise the sites in data/fixtures/ (coordinates only:
 * values always come from the connectors).
 */
export async function loadSites(dataDir: string, onNote?: (message: string) => void): Promise<Site[]> {
  const candidates = path.join(dataDir, "candidates.json");
  try {
    return parseSites(JSON.parse(await readFile(candidates, "utf8")), onNote);
  } catch (error) {
    if ((error as NodeJS.ErrnoException).code !== "ENOENT") throw error;
  }
  onNote?.("data/candidates.json missing: falling back to the 3 sites in data/fixtures/site-values.json");
  const fixtures = await loadFixtures(path.join(dataDir, "fixtures", "site-values.json"));
  return parseSites(fixtures.sites, onNote);
}

export async function loadOpenApi(file = path.join(API_ROOT, "openapi.yaml")): Promise<Record<string, unknown>> {
  const doc: unknown = parse(await readFile(file, "utf8"));
  if (typeof doc !== "object" || doc === null) throw new Error(`invalid openapi.yaml : ${file}`);
  return doc as Record<string, unknown>;
}

export async function loadMoonReference(dataDir: string): Promise<unknown> {
  try {
    return JSON.parse(await readFile(path.join(dataDir, "reference", "moon-south-pole.json"), "utf8"));
  } catch (error) {
    if ((error as NodeJS.ErrnoException).code === "ENOENT") return undefined;
    throw error;
  }
}
