import { access, readFile, stat } from "node:fs/promises";
import path from "node:path";

/**
 * Read-only access to the static releases written by tools/discovery/release.py (ADR-003, ADR-004).
 *
 * File paths are built only from values found in the release itself (release ids from index.json, scenario and
 * target ids from scenarios.json, tau and min_cells from the release grid), never from raw user input.
 */

export type ReleaseEntry = { id: string; run: string; methodology_version: string; protocol: string; commit: string; created: string };
export type ReleaseIndex = { current: string; current_by_body?: Record<string, string>; releases: (ReleaseEntry & { body?: string })[] };
/** Written by the refresher (tools/discovery/refresher.py, ADR-009): live state of each watched source. */
export type Freshness = {
  refresher: boolean;
  written_at?: string;
  sources: Record<string, { state: string; last_check?: string | null; last_success?: string | null; interval_hours?: number | null; reason?: string | null; detected_on?: string | null }>;
  progress?: unknown;
  held?: { id: string; body?: string; reasons?: string[] }[];
  new_products?: { source: string; found: string; detected_on: string; status: string; url: string }[];
  impact?: Record<string, unknown>[];
};
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

export type AnnotatedZone = { target: string; slope_median: number | null; lat: number; lon: number; typicality: number | null; place?: { en: string | null; fr: string | null } };
export type TargetWindows = { lat: number[]; lon: number[]; slope: number[]; name: string[] };
export type Annotations = {
  release: string; body: string; band: number; rule: string; sources: Record<string, string>;
  targets: Record<string, { ref_quantiles?: number[]; n_windows?: number; windows: TargetWindows | null; why?: string }>;
  zones: Record<string, AnnotatedZone>;
};

/** Percentile of a slope in a target's distribution, from its 1,001 quantiles (linear between them). */
export function percentileOf(q: number[], slope: number): number {
  if (slope <= q[0]) return 0;
  if (slope >= q[q.length - 1]) return 1;
  let lo = 0;
  let hi = q.length - 1;
  while (hi - lo > 1) {
    const mid = (lo + hi) >> 1;
    if (q[mid] <= slope) lo = mid;
    else hi = mid;
  }
  const f = q[hi] > q[lo] ? (slope - q[lo]) / (q[hi] - q[lo]) : 0;
  return (lo + f) / (q.length - 1);
}

export class NotFound extends Error {}
export class BadRequest extends Error {}

const MAX_CACHED = 32;

export class ReleaseStore {
  private readonly cache = new Map<string, unknown>();
  private checkedAt = Date.now();
  private indexMtime = 0;

  private constructor(
    private readonly root: string,
    public index: ReleaseIndex,
    private readonly reloadMs: number,
  ) {}

  private static async readIndex(root: string): Promise<ReleaseIndex> {
    const index = JSON.parse(await readFile(path.join(root, "index.json"), "utf8")) as ReleaseIndex;
    if (!index.current || !Array.isArray(index.releases) || !index.releases.some((r) => r.id === index.current)) {
      throw new Error(`invalid releases index in ${root}`);
    }
    return index;
  }

  /** `reloadMs`: how often the index is looked at again, so a release switched by the refresher is served without a restart. */
  static async open(root: string, opts: { reloadMs?: number } = {}): Promise<ReleaseStore> {
    const store = new ReleaseStore(path.resolve(root), await ReleaseStore.readIndex(root), opts.reloadMs ?? 10_000);
    store.indexMtime = (await stat(path.join(root, "index.json"))).mtimeMs;
    return store;
  }

  /** Reread index.json when it changed (atomic switch by the refresher). A broken index keeps the previous one. */
  async refresh(): Promise<void> {
    if (Date.now() - this.checkedAt < this.reloadMs) return;
    this.checkedAt = Date.now();
    try {
      const m = (await stat(path.join(this.root, "index.json"))).mtimeMs;
      if (m !== this.indexMtime) {
        this.index = await ReleaseStore.readIndex(this.root);
        this.indexMtime = m;
      }
    } catch {
      // keep serving the index already loaded
    }
  }

  /** Live freshness written by the refresher, or undefined when it never ran. */
  async freshness(): Promise<Freshness | undefined> {
    try {
      return JSON.parse(await readFile(path.join(this.root, "freshness.json"), "utf8")) as Freshness;
    } catch {
      return undefined;
    }
  }

  /** The current release of the body of `release`, when it is not `release` itself. */
  newerRelease(release: string): string | undefined {
    const entry = this.index.releases.find((r) => r.id === release);
    const body = entry?.body ?? "moon";
    const current = (this.index.current_by_body ?? {})[body] ?? (body === "moon" ? this.index.current : undefined);
    return current && current !== release ? current : undefined;
  }

  /** The release id to read: the current one, the current one of a body ("mars"), or a listed one. */
  releaseId(requested?: unknown): string {
    if (requested === undefined) return this.index.current;
    const byBody = this.index.current_by_body ?? {};
    const alias = typeof requested === "string" && Object.hasOwn(byBody, requested) ? byBody[requested] : requested;
    const hit = this.index.releases.find((r) => r.id === alias);
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

  doc(release: string, name: "profiles" | "scenarios" | "method" | "coverage" | "status" | "changes"): Promise<Doc> {
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

  /** Provenance of one Earth tile "lat,lon" (T52): its source files with version and date, computation date, code. */
  async tileProvenance(release: string, key: string): Promise<Doc> {
    type Prov = { release: string; items: Record<string, unknown>[]; tiles: Record<string, Record<string, [string | null, string, string, string, number[]]>>; last_changed_in: Record<string, string> };
    const p = await this.read<Prov>(release, "provenance.json");
    const sc = Object.hasOwn(p.tiles, key) ? p.tiles[key] : undefined;
    if (!sc) throw new NotFound(`No Earth tile ${key} in release ${release}`);
    const dates: string[] = [];
    const scales: Record<string, unknown> = {};
    for (const [scale, [computed, code, commit, outputs, ids]] of Object.entries(sc)) {
      const inputs = ids.map((i) => p.items[i]);
      for (const i of inputs) if (typeof i.last_modified === "string") dates.push(i.last_modified);
      scales[scale] = { computed_at: computed, ...(computed ? {} : { computed_at_note: "not recorded (computed before T52)" }), code, commit, outputs, inputs };
    }
    dates.sort();
    const { methodology_version } = await this.release(release);
    return { release, methodology_version, tile: key, last_changed_in: p.last_changed_in[key], data_date: dates.length ? dates[dates.length - 1].slice(0, 10) : null, scales };
  }

  /** Names and same-slope links of a release (tools/discovery/analogs.py, T45c), or undefined when not built. */
  async annotations(release: string): Promise<Annotations | undefined> {
    const file = path.join(this.root, "annotations", `${release}.json`);
    const cached = this.cache.get(file);
    if (cached !== undefined) return cached as Annotations;
    try {
      const a = JSON.parse(await readFile(file, "utf8")) as Annotations;
      if (this.cache.size >= MAX_CACHED) this.cache.delete(this.cache.keys().next().value as string);
      this.cache.set(file, a);
      return a;
    } catch {
      return undefined;
    }
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
