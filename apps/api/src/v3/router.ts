import express from "express";
import type { Request, Response } from "express";
import { BadRequest, NotFound, parseZoneId, percentileOf } from "./store.js";
import type { Annotations, TargetWindows } from "./store.js";
import type { ReleaseStore } from "./store.js";

const DEFAULT_LIMIT = 50;
const MAX_LIMIT = 200;

/** Routes of /api/v3 served from static releases (ADR-004). Every answer carries `release` and `methodology_version`. */
export function v3Router(
  store: ReleaseStore | undefined,
  log: (message: string, error?: unknown) => void,
  discoveryUrl?: string,
  sites: { id: string; lat: number; lon: number }[] = [],
): express.Router {
  const r = express.Router();

  const handle =
    (fn: (req: Request, release: string) => Promise<unknown>) =>
    async (req: Request, res: Response): Promise<void> => {
      if (!store) {
        res.status(503).json({ error: "No v3 release is installed on this server (run tools/discovery/release.py)" });
        return;
      }
      try {
        await store.refresh();
        const release = store.releaseId(req.query.release);
        res.json(await fn(req, release));
      } catch (error) {
        if (error instanceof BadRequest) res.status(400).json({ error: error.message });
        else if (error instanceof NotFound) res.status(404).json({ error: error.message });
        else if (error instanceof Unavailable) res.status(503).json({ error: error.message });
        else if (error instanceof TooLarge) res.status(413).json({ error: error.message });
        else {
          log(`${req.method} ${req.path} failed`, error);
          res.status(500).json({ error: "Internal error" });
        }
      }
    };

  const head = async (release: string) => {
    const doc = await store!.release(release);
    return { release: doc.release, methodology_version: doc.methodology_version };
  };

  r.get("/releases", async (_req, res) => {
    if (!store) {
      res.status(503).json({ error: "No v3 release is installed on this server (run tools/discovery/release.py)" });
      return;
    }
    await store.refresh();
    res.json(store.index);
  });

  r.get("/releases/:id", handle(async (req) => store!.release(store!.releaseId(req.params.id))));

  r.get("/profiles", handle(async (_req, release) => store!.doc(release, "profiles")));
  r.get(
    "/profiles/:id",
    handle(async (req, release) => {
      const doc = await store!.doc(release, "profiles");
      const hit = (doc.profiles as { id: string }[]).find((p) => p.id === req.params.id);
      if (!hit) throw new NotFound(`Unknown profile: ${req.params.id.slice(0, 40)}`);
      return { ...(await head(release)), profile: hit };
    }),
  );

  r.get("/scenarios", handle(async (_req, release) => store!.doc(release, "scenarios")));
  r.get(
    "/scenarios/:id",
    handle(async (req, release) => ({ ...(await head(release)), scenario: await store!.scenario(release, req.params.id) })),
  );

  r.get("/method", handle(async (_req, release) => store!.doc(release, "method")));
  r.get("/status", handle(async (_req, release) => liveStatus(store!, release)));
  r.get("/changes", handle(async (_req, release) => ({ ...(await head(release)), ...(await store!.doc(release, "changes")) })));
  r.get(
    "/tiles/:tile/provenance",
    handle(async (req, release) => {
      const m = /^(-?\d{1,2}),(-?\d{1,3})$/.exec(req.params.tile);
      if (!m || Number(m[1]) < -90 || Number(m[1]) > 89 || Number(m[2]) < -180 || Number(m[2]) > 179) throw new BadRequest("tile must be 'lat,lon' of a 1 degree tile");
      return store!.tileProvenance(release, `${Number(m[1])},${Number(m[2])}`);
    }),
  );

  r.get(
    "/coverage",
    handle(async (req, release) => {
      const s = await store!.selection(release, req.query.scenario, req.query.env, undefined, undefined);
      const doc = await store!.doc(release, "coverage");
      const byScenario = (doc.scenarios as Record<string, Record<string, unknown>>)[s.scenario.id] ?? {};
      const coverage = byScenario[s.target];
      if (!coverage) throw new NotFound(`No coverage exported for ${s.scenario.id} ${s.target}`);
      return { ...(await head(release)), scenario: s.scenario.id, env: s.target, coverage };
    }),
  );

  r.get(
    "/zones",
    handle(async (req, release) => {
      const s = await store!.selection(release, req.query.scenario, req.query.env, req.query.tau, req.query.min_cells);
      const limit = req.query.limit === undefined ? DEFAULT_LIMIT : Number(req.query.limit);
      const offset = req.query.offset === undefined ? 0 : Number(req.query.offset);
      if (!Number.isInteger(limit) || limit < 1 || limit > MAX_LIMIT) throw new BadRequest(`limit must be an integer from 1 to ${MAX_LIMIT}`);
      if (!Number.isInteger(offset) || offset < 0) throw new BadRequest("offset must be a non-negative integer");
      const doc = await store!.zones(release, s);
      const ann = await store!.annotations(release);
      return {
        ...(await head(release)),
        scenario: s.scenario.id, env: s.target, tau: s.tau, min_cells: s.minCells,
        total: doc.zones.length, offset, limit,
        zones: doc.zones.slice(offset, offset + limit).map((z) => annotate(z, ann)),
        ...(ann ? { attribution: ann.sources.earth_names } : {}),
      };
    }),
  );

  r.get(
    "/zones/:id",
    handle(async (req, release) => {
      const p = parseZoneId(req.params.id);
      if (!p) throw new NotFound(`Unknown zone: ${req.params.id.slice(0, 80)}`);
      const s = await store!.selection(release, p.scenario, p.env, p.tau, p.minCells).catch((e: unknown) => {
        throw e instanceof BadRequest ? new NotFound(`Unknown zone: ${req.params.id.slice(0, 80)} (${e.message})`) : e;
      });
      const doc = await store!.zones(release, s);
      const zone = doc.zones[p.rank - 1];
      if (!zone || zone.id !== req.params.id) throw new NotFound(`Unknown zone: ${req.params.id.slice(0, 80)}`);
      const ann = await store!.annotations(release);
      return { ...(await head(release)), zone: annotate(zone, ann), cannot_assess: s.scenario.cannot_assess,
        ...(ann ? { attribution: ann.sources.earth_names } : {}) };
    }),
  );

  // --- analog links between the two globes (T45c part 2): the same slope percentile, never one planetary place ---

  const annotationsOf = async (release: string): Promise<Annotations> => {
    const ann = await store!.annotations(release);
    if (!ann) throw new NotFound(`No names or analog links are built for release ${release}`);
    return ann;
  };
  const targetOf = (ann: Annotations, env: string): { ref_quantiles: number[]; n_windows: number; windows: TargetWindows } => {
    const t = Object.hasOwn(ann.targets, env) ? ann.targets[env] : undefined;
    if (!t || !t.windows || !t.ref_quantiles) throw new NotFound(`No planetary windows stored for ${env}${t?.why ? `: ${t.why}` : ""}`);
    return { ref_quantiles: t.ref_quantiles, n_windows: t.n_windows ?? t.windows.slope.length, windows: t.windows };
  };

  r.get(
    "/analogs/target",
    handle(async (req, release) => {
      const s = await store!.selection(release, req.query.scenario, req.query.env, undefined, undefined);
      const ann = await annotationsOf(release);
      const t = targetOf(ann, s.target);
      return { ...(await head(release)), env: s.target, body: ann.body, n_windows: t.n_windows, windows: t.windows,
        rule: ann.rule, sources: ann.sources };
    }),
  );

  r.get(
    "/analogs/zone/:id",
    handle(async (req, release) => {
      const ann = await annotationsOf(release);
      const z = Object.hasOwn(ann.zones, req.params.id) ? ann.zones[req.params.id] : undefined;
      if (!z) throw new NotFound(`No analog link for zone ${req.params.id.slice(0, 80)} (only the best zones of each target are linked)`);
      if (z.slope_median == null) throw new NotFound(`Zone ${req.params.id.slice(0, 80)} has no unmasked window to compare`);
      const t = targetOf(ann, z.target);
      const p = percentileOf(t.ref_quantiles, z.slope_median);
      const w = t.windows;
      const windows = w.slope.flatMap((sl, k) => (Math.abs(percentileOf(t.ref_quantiles, sl) - p) <= ann.band
        ? [{ lat: w.lat[k], lon: w.lon[k], slope: sl, name: w.name[k] }] : []));
      return { ...(await head(release)), zone: { id: req.params.id, ...z }, env: z.target, percentile: Math.round(p * 1e4) / 1e4,
        windows, n_windows: t.n_windows, rule: ann.rule, sources: ann.sources };
    }),
  );

  r.get(
    "/analogs/point",
    handle(async (req, release) => {
      const s = await store!.selection(release, req.query.scenario, req.query.env, undefined, undefined);
      const lat = Number(req.query.lat);
      const lon = Number(req.query.lon);
      if (!Number.isFinite(lat) || !Number.isFinite(lon) || Math.abs(lat) > 90 || Math.abs(lon) > 360) throw new BadRequest("lat must be within ±90 and lon within ±360");
      const ann = await annotationsOf(release);
      const t = targetOf(ann, s.target);
      const rad = Math.PI / 180;
      let best = 0;
      let bestD = Infinity;
      t.windows.lat.forEach((la, k) => {
        const c = Math.sin(lat * rad) * Math.sin(la * rad) + Math.cos(lat * rad) * Math.cos(la * rad) * Math.cos((lon - t.windows.lon[k]) * rad);
        const dist = Math.acos(Math.min(1, Math.max(-1, c)));
        if (dist < bestD) {
          bestD = dist;
          best = k;
        }
      });
      const slope = t.windows.slope[best];
      const p = percentileOf(t.ref_quantiles, slope);
      const zones = Object.entries(ann.zones)
        .filter(([id, z]) => z.target === s.target && id.startsWith(`${s.scenario.id}.`) && z.slope_median != null
          && Math.abs(percentileOf(t.ref_quantiles, z.slope_median) - p) <= ann.band)
        .sort((a, b) => (b[1].typicality ?? 0) - (a[1].typicality ?? 0))
        .slice(0, 20)
        .map(([id, z]) => ({ id, ...z }));
      return { ...(await head(release)), env: s.target, percentile: Math.round(p * 1e4) / 1e4,
        window: { lat: t.windows.lat[best], lon: t.windows.lon[best], slope, name: t.windows.name[best] },
        zones, rule: ann.rule, sources: ann.sources };
    }),
  );

  // --- on-demand work, forwarded to the internal discovery service (ADR-005) ---

  const forward = async (pathAndQuery: string, init?: { body: unknown }): Promise<unknown> => {
    if (!discoveryUrl) throw new Unavailable("The discovery service is not configured on this server");
    let res: globalThis.Response;
    try {
      res = await fetch(`${discoveryUrl}${pathAndQuery}`, {
        method: init ? "POST" : "GET",
        headers: init ? { "content-type": "application/json" } : {},
        ...(init ? { body: JSON.stringify(init.body) } : {}),
        signal: AbortSignal.timeout(QUERY_TIMEOUT_MS),
      });
    } catch (error) {
      log(`discovery service call failed: ${pathAndQuery.split("?")[0]}`, error);
      throw new Unavailable(
        (error as Error).name === "TimeoutError"
          ? `The discovery service took longer than ${QUERY_TIMEOUT_MS / 1000} s: narrow the request`
          : "The discovery service is unavailable; the preset layers and zones still work",
      );
    }
    const body = (await res.json().catch(() => ({}))) as { detail?: unknown };
    if (res.status === 400 || res.status === 404) {
      const message = typeof body.detail === "string" ? body.detail : "Request refused by the discovery service";
      throw res.status === 400 ? new BadRequest(message) : new NotFound(message);
    }
    if (!res.ok) throw new Unavailable("The discovery service failed on this request");
    return body;
  };

  r.get(
    "/cells",
    handle(async (req, release) => {
      const s = await store!.selection(release, req.query.scenario, req.query.env, undefined, undefined);
      const raw = typeof req.query.bbox === "string" ? req.query.bbox : "";
      const box = raw.split(",").map(Number);
      if (box.length !== 4 || !box.every(Number.isFinite)) throw new BadRequest("bbox must be west,south,east,north in degrees");
      const q = new URLSearchParams({ bbox: box.join(","), env: s.target, release });
      return forward(`/cells?${q.toString()}`);
    }),
  );

  // The known sites of the v2 missions, placed in the v3 grid: one call per scenario, cached per release.
  const siteCache = new Map<string, unknown>();
  r.get(
    "/sites",
    handle(async (req, release) => {
      const s = await store!.scenario(release, req.query.scenario);
      const key = `${release}|${s.id}`;
      if (!siteCache.has(key)) {
        const points = sites.map((x) => ({ id: x.id, lat: x.lat, lon: x.lon }));
        const out = (await forward(`/points?${new URLSearchParams({ release }).toString()}`, { body: { points, envs: s.assessed_targets } })) as Record<string, unknown>;
        siteCache.set(key, { ...out, scenario: s.id });
      }
      return siteCache.get(key);
    }),
  );

  r.post(
    "/query",
    handle(async (req, release) => {
      if (Number(req.headers["content-length"] ?? 0) > QUERY_MAX_BYTES) throw new TooLarge(`The query body is limited to ${QUERY_MAX_BYTES / 1024} KB`);
      const body = req.body as Record<string, unknown> | undefined;
      if (!body || typeof body !== "object" || Array.isArray(body)) throw new BadRequest("The query must be a JSON object");
      const unknown = Object.keys(body).filter((k) => !QUERY_FIELDS.includes(k));
      if (unknown.length > 0) throw new BadRequest(`Unknown field: ${unknown[0].slice(0, 40)}`);
      const s = await store!.selection(release, body.scenario, body.env, undefined, undefined);
      const { scenario: _scenario, ...rest } = body;
      return forward(`/query?${new URLSearchParams({ release }).toString()}`, { body: { ...rest, env: s.target } });
    }),
  );

  r.get(
    "/criteria",
    handle(async (_req, release) => forward(`/criteria?${new URLSearchParams({ release }).toString()}`)),
  );

  r.post(
    "/criteria",
    handle(async (req, release) => {
      if (Number(req.headers["content-length"] ?? 0) > QUERY_MAX_BYTES) throw new TooLarge(`The criteria body is limited to ${QUERY_MAX_BYTES / 1024} KB`);
      const body = req.body as Record<string, unknown> | undefined;
      if (!body || typeof body !== "object" || Array.isArray(body)) throw new BadRequest("The criteria request must be a JSON object");
      const unknown = Object.keys(body).filter((k) => !CRITERIA_FIELDS.includes(k));
      if (unknown.length > 0) throw new BadRequest(`Unknown field: ${unknown[0].slice(0, 40)}`);
      return forward(`/criteria?${new URLSearchParams({ release }).toString()}`, { body });
    }),
  );

  return r;
}

const CRITERIA_FIELDS = ["preset", "criteria", "limit"];
const QUERY_TIMEOUT_MS = 30_000;
const QUERY_MAX_BYTES = 16 * 1024;
const QUERY_FIELDS = ["scenario", "env", "min_typicality", "min_confidence", "requirements_met", "bbox", "limit"];

class Unavailable extends Error {}
class TooLarge extends Error {}

export const LAYER_PARAMETERS = ["typicality", "coverage", "geology", "frozen", "aridity"] as const;
/** Earth context layers (T47): the same for every lunar target, stored once per release. */
const EARTH_LAYERS = new Set(["frozen", "aridity"]);
export const MAX_ZOOM = 7;

/** Raster tiles of a release (zoom 0 to 7). Mounted before the general rate limit: a map view asks for many tiles. */
export function v3LayersRouter(store: ReleaseStore | undefined, log: (message: string, error?: unknown) => void): express.Router {
  const r = express.Router();
  r.get("/:scenario/:env/:parameter/:z/:x/:file", async (req, res) => {
    if (!store) {
      res.status(503).json({ error: "No v3 release is installed on this server (run tools/discovery/release.py)" });
      return;
    }
    try {
      const release = store.releaseId(req.query.release);
      const s = await store.selection(release, req.params.scenario, req.params.env, undefined, undefined);
      const parameter = LAYER_PARAMETERS.find((p) => p === req.params.parameter);
      if (!parameter) throw new NotFound(`Unknown layer parameter: ${req.params.parameter.slice(0, 40)}`);
      const m = /^([0-9]{1,3})\.png$/.exec(req.params.file);
      const z = Number(req.params.z);
      const x = Number(req.params.x);
      const y = m ? Number(m[1]) : NaN;
      const n = 2 ** z;
      if (![z, x, y].every(Number.isInteger) || z < 0 || z > MAX_ZOOM || x < 0 || x >= n || y < 0 || y >= n || !/^[0-9]+$/.test(req.params.x)) {
        throw new BadRequest(`Tiles exist for zoom 0 to ${MAX_ZOOM}, with x and y inside the zoom`);
      }
      const file = await store.layerTile(release, EARTH_LAYERS.has(parameter) ? "_earth" : s.target, parameter, z, x, y);
      res.setHeader("X-Release", release);
      res.setHeader("Cache-Control", "public, max-age=3600");
      if (!file) {
        res.status(204).end();
        return;
      }
      res.type("png").sendFile(file);
    } catch (error) {
      if (error instanceof BadRequest) res.status(400).json({ error: error.message });
      else if (error instanceof NotFound) res.status(404).json({ error: error.message });
      else {
        log(`GET layer tile failed`, error);
        res.status(500).json({ error: "Internal error" });
      }
    }
  });
  return r;
}

/**
 * Status of a release (ADR-009 section 4): validity from the release, freshness from the refresher when it ran.
 * A source of the release whose last check is older than twice its interval, or that was never checked, is
 * `check_overdue`, so a stopped refresher shows.
 */
export async function liveStatus(store: ReleaseStore, release: string, now = Date.now()): Promise<Record<string, unknown>> {
  const doc = (await store.doc(release, "status")) as Record<string, any>;
  const live = await store.freshness();
  const newer = store.newerRelease(release);
  const base = (doc.freshness ?? { refresher: false, sources: [] }) as Record<string, any>;
  let freshness: Record<string, any> = { ...base };
  if (live?.refresher) {
    const method = (await store.doc(release, "method").catch(() => ({ sources: [] }))) as { sources?: { id: string }[] };
    const ids = (method.sources ?? []).map((s) => s.id);
    freshness = {
      refresher: true,
      written_at: live.written_at,
      sources: ids.map((id) => {
        const s = live.sources[id];
        if (!s) return { id, state: "check_overdue", checked_on: null, reason: "not checked by the refresher" };
        const last = s.last_check ? Date.parse(s.last_check) : NaN;
        const overdue = s.interval_hours != null && (Number.isNaN(last) || now - last > 2 * s.interval_hours * 3600_000);
        return { id, state: overdue ? "check_overdue" : s.state, checked_on: s.last_check ?? null, last_success: s.last_success ?? null,
          detected_on: s.detected_on ?? null, reason: s.reason ?? null };
      }),
      ...(live.held?.length ? { held: live.held } : {}),
      ...(live.progress ? { progress: live.progress } : {}),
      ...(live.new_products?.length ? { new_products: live.new_products } : {}),
      ...(live.impact?.length ? { impact: live.impact } : {}),
    };
  }
  if (newer) freshness.newer_release = newer;
  return { ...doc, freshness };
}

/** A zone with its place name and median slope when the release has annotations (coordinates stay). */
function annotate<Z extends { id: string }>(z: Z, ann: Annotations | undefined): Z & { place?: unknown; slope_median?: number | null } {
  const a = ann && Object.hasOwn(ann.zones, z.id) ? ann.zones[z.id] : undefined;
  return a ? { ...z, place: a.place ?? null, slope_median: a.slope_median } : z;
}
