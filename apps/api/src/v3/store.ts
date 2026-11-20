import { access, readFile } from "node:fs/promises";
import path from "node:path";

/**
 * Read-only access to the static releases written by tools/discovery/release.py (ADR-003, ADR-004).
 *
 * File paths are built only from values found in the release itself (release ids from index.json, scenario and
 * target ids from scenarios.json, tau and min_cells from the release grid), never from raw user input.
 */

export type ReleaseEntry = { id: string; run: string; methodology_version: string; protocol: string; commit: string; created: string };
export type ReleaseIndex = { current: string; releases: ReleaseEntry[] };
export type Grid = { tau: number[]; min_cells: number[]; nominal: { tau: number; min_cells: number } };
export type Scenario = {
  id: string;
  targets: string[];
  assessed_targets: string[];
  not_comparable: Record<string, string>;
  cannot_assess: string[];
  [key: string]: unknown;
};
export type Zone = { id: string; rank: number; [key: string]: unknown };
export type Doc = { release: string; methodology_version: string; [key: string]: unknown };

export class NotFound extends Error {}
export class BadRequest extends Error {}

const MAX_CACHED = 32;

export class ReleaseStore {
  private readonly cache = new Map<string, unknown>();

  private constructor(
    private readonly root: string,
    readonly index: ReleaseIndex,
  ) {}

  static async open(root: string): Promise<ReleaseStore> {
    const index = JSON.parse(await readFile(path.join(root, "index.json"), "utf8")) as ReleaseIndex;
    if (!index.current || !Array.isArray(index.releases) || !index.releases.some((r) => r.id === index.current)) {
      throw new Error(`invalid releases index in ${root}`);
    }
    return new ReleaseStore(path.resolve(root), index);
  }

  /** The release id to read: the current one, or a listed one. */
  releaseId(requested?: unknown): string {
    if (requested === undefined) return this.index.current;
    const hit = this.index.releases.find((r) => r.id === requested);
    if (!hit) throw new NotFound(`Unknown release: ${String(requested).slice(0, 40)}`);
    return hit.id;
  }

  private async read<T>(release: string, ...parts: string[]): Promise<T> {
    const file = path.join(this.root, release, ...parts);
    const cached = this.cache.get(file);
    if (cached !== undefined) return cached as T;
    let value: T;
    try {
      value = JSON.parse(await readFile(file, "utf8")) as T;
    } catch (error) {
      if ((error as NodeJS.ErrnoException).code === "ENOENT") throw new NotFound(`Not exported in release ${release}`);
      throw error;
    }
    if (this.cache.size >= MAX_CACHED) this.cache.delete(this.cache.keys().next().value as string);
    this.cache.set(file, value);
    return value;
  }

  release(id: string): Promise<Doc & { grid: Grid }> {
    return this.read(id, "release.json");
  }

  doc(release: string, name: "profiles" | "scenarios" | "method" | "coverage" | "status"): Promise<Doc> {
    return this.read(release, `${name}.json`);
  }

  async scenario(release: string, id: unknown): Promise<Scenario> {
    const all = (await this.doc(release, "scenarios")).scenarios as Scenario[];
    const hit = all.find((s) => s.id === id);
    if (!hit) throw new NotFound(`Unknown scenario: ${String(id).slice(0, 40)}`);
    return hit;
  }

  /** Scenario and target checked against the release, tau and min_cells against its grid. */
  async selection(release: string, scenario: unknown, env: unknown, tau: unknown, minCells: unknown) {
    if (typeof scenario !== "string" || typeof env !== "string") throw new BadRequest("scenario and env are required");
    const sc = await this.scenario(release, scenario).catch((e: unknown) => {
      throw e instanceof NotFound ? new BadRequest(e.message) : e;
    });
    const target = sc.assessed_targets.find((t) => t === env);
    if (!target) {
      const why = sc.not_comparable[env];
      throw new BadRequest(
        sc.targets.includes(env) ? `Target ${env} is not assessed on Earth in this release${why ? `: ${why}` : ""}` : `Unknown env for scenario ${sc.id}: ${env.slice(0, 40)}`,
      );
    }
    const { grid } = await this.release(release);
    const t = tau === undefined ? grid.nominal.tau : Number(tau);
    const m = minCells === undefined ? grid.nominal.min_cells : Number(minCells);
    if (!grid.tau.includes(t)) throw new BadRequest(`tau must be one of ${grid.tau.join(", ")}`);
    if (!grid.min_cells.includes(m)) throw new BadRequest(`min_cells must be one of ${grid.min_cells.join(", ")}`);
    return { scenario: sc, target, tau: grid.tau[grid.tau.indexOf(t)], minCells: grid.min_cells[grid.min_cells.indexOf(m)] };
  }

  /** Path of one layer tile, or undefined when the release has no tile there (no cell in it). */
  async layerTile(release: string, target: string, parameter: string, z: number, x: number, y: number): Promise<string | undefined> {
    const file = path.join(this.root, release, "layers", target, parameter, String(z), String(x), `${y}.png`);
    try {
      await access(file);
      return file;
    } catch {
      return undefined;
    }
  }

  async zones(release: string, s: { scenario: Scenario; target: string; tau: number; minCells: number }): Promise<Doc & { zones: Zone[] }> {
    return this.read(release, "zones", s.scenario.id, s.target, `t${s.tau}-m${s.minCells}.json`);
  }
}

const ZONE_ID = /^([A-Z])\.([a-z0-9-]{1,60})\.t([0-9.]{1,5})\.m([0-9]{1,3})\.([1-9][0-9]{0,6})$/;

/** Parts of a zone id such as "B.moon-psr.t0.5.m3.12", or undefined. */
export function parseZoneId(id: string): { scenario: string; env: string; tau: string; minCells: string; rank: number } | undefined {
  const m = ZONE_ID.exec(id);
  if (!m) return undefined;
  return { scenario: m[1], env: m[2], tau: m[3], minCells: m[4], rank: Number(m[5]) };
}
