import { readFile } from "node:fs/promises";
import path from "node:path";
import { parse } from "yaml";
import type { Site } from "../analyze/analyze.js";
import { loadFixtures } from "../analyze/fixtures.js";
import { API_ROOT } from "./config.js";

const ROLES = ["validation", "negative", "candidate"] as const;

/** Valide une liste de sites (docs/contrats.md §1). Les entrées invalides sont ignorées et signalées. */
export function parseSites(raw: unknown, onSkip?: (reason: string) => void): Site[] {
  const list = Array.isArray(raw) ? raw : (raw as { sites?: unknown } | null)?.sites;
  if (!Array.isArray(list)) throw new Error("La liste de sites doit être un tableau (ou { sites: [...] })");
  const sites: Site[] = [];
  const seen = new Set<string>();
  list.forEach((entry: unknown, index) => {
    const s = entry as Partial<Site> | null;
    const problem =
      typeof s?.id !== "string" || !/^[a-z0-9-]+$/.test(s.id)
        ? "id manquant ou invalide"
        : seen.has(s.id)
          ? "id en double"
          : typeof s.name !== "string"
            ? "name manquant"
            : typeof s.lat !== "number" || s.lat < -90 || s.lat > 90
              ? "lat invalide"
              : typeof s.lon !== "number" || s.lon < -180 || s.lon > 180
                ? "lon invalide"
                : undefined;
    if (problem || !s || typeof s.id !== "string" || typeof s.name !== "string") {
      onSkip?.(`site #${index} ignoré : ${problem ?? "invalide"}`);
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
 * Sites interrogés : data/candidates.json (Wassim) s'il existe, sinon les sites de data/fixtures/ (coordonnées seulement :
 * les valeurs viennent toujours des connecteurs).
 */
export async function loadSites(dataDir: string, onNote?: (message: string) => void): Promise<Site[]> {
  const candidates = path.join(dataDir, "candidates.json");
  try {
    return parseSites(JSON.parse(await readFile(candidates, "utf8")), onNote);
  } catch (error) {
    if ((error as NodeJS.ErrnoException).code !== "ENOENT") throw error;
  }
  onNote?.("data/candidates.json absent : repli sur les 3 sites de data/fixtures/site-values.json");
  const fixtures = await loadFixtures(path.join(dataDir, "fixtures", "site-values.json"));
  return parseSites(fixtures.sites, onNote);
}

export async function loadOpenApi(file = path.join(API_ROOT, "openapi.yaml")): Promise<Record<string, unknown>> {
  const doc: unknown = parse(await readFile(file, "utf8"));
  if (typeof doc !== "object" || doc === null) throw new Error(`openapi.yaml invalide : ${file}`);
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
