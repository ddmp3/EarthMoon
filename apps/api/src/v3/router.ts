import express from "express";
import type { Request, Response } from "express";
import { BadRequest, NotFound, parseZoneId } from "./store.js";
import type { ReleaseStore } from "./store.js";

const DEFAULT_LIMIT = 50;
const MAX_LIMIT = 200;

/** Routes of /api/v3 served from static releases (ADR-004). Every answer carries `release` and `methodology_version`. */
export function v3Router(store: ReleaseStore | undefined, log: (message: string, error?: unknown) => void): express.Router {
  const r = express.Router();

  const handle =
    (fn: (req: Request, release: string) => Promise<unknown>) =>
    async (req: Request, res: Response): Promise<void> => {
      if (!store) {
        res.status(503).json({ error: "No v3 release is installed on this server (run tools/discovery/release.py)" });
        return;
      }
      try {
        const release = store.releaseId(req.query.release);
        res.json(await fn(req, release));
      } catch (error) {
        if (error instanceof BadRequest) res.status(400).json({ error: error.message });
        else if (error instanceof NotFound) res.status(404).json({ error: error.message });
        else {
          log(`GET ${req.path} failed`, error);
          res.status(500).json({ error: "Internal error" });
        }
      }
    };

  const head = async (release: string) => {
    const doc = await store!.release(release);
    return { release: doc.release, methodology_version: doc.methodology_version };
  };

  r.get("/releases", (_req, res) => {
    if (!store) {
      res.status(503).json({ error: "No v3 release is installed on this server (run tools/discovery/release.py)" });
      return;
    }
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
      return {
        ...(await head(release)),
        scenario: s.scenario.id, env: s.target, tau: s.tau, min_cells: s.minCells,
        total: doc.zones.length, offset, limit,
        zones: doc.zones.slice(offset, offset + limit),
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
      return { ...(await head(release)), zone, cannot_assess: s.scenario.cannot_assess };
    }),
  );

  return r;
}
