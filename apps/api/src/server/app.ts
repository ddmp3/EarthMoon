import cors from "cors";
import express from "express";
import type { NextFunction, Request, Response } from "express";
import rateLimit from "express-rate-limit";
import swaggerUi from "swagger-ui-express";
import { analyze, collectValues, METHODOLOGY_VERSION } from "../analyze/analyze.js";
import type { AnalyzeDeps } from "../analyze/analyze.js";
import { ValidationError } from "../analyze/validate.js";
import { moonValues } from "../analyze/moon.js";
import { MODES, PARAM_IDS, assess, isModeId, vegetationFactor } from "../scoring/index.js";
import { explain } from "../analyze/explain.js";
import { SOURCES, valueSources } from "../sources/catalog.js";
import { PARAMETERS } from "./parameters.js";
import { v3LayersRouter, v3Router } from "../v3/router.js";
import type { ReleaseStore } from "../v3/store.js";

export type AppDeps = AnalyzeDeps & {
  /** Names of the connected sources, returned by GET /api/sites/{id}. */
  sourceNames: string[];
  /** True if values come from the sample data (USE_FIXTURES): the per-value sources say so. */
  useFixtures?: boolean;
  /** Parsed OpenAPI contract (served on /api/docs and /api/openapi.json). */
  openapi: Record<string, unknown>;
  /** data/reference/moon-south-pole.json, if present. */
  moonReference?: unknown;
  allowedOrigins?: string[];
  rateLimitPerMinute?: number;
  log?: (message: string, error?: unknown) => void;
  /** Static v3 releases (tools/discovery/release.py); without them /api/v3 answers 503. */
  releases?: ReleaseStore;
  /** Internal discovery service for /api/v3/cells and /api/v3/query (ADR-005); without it they answer 503. */
  discoveryUrl?: string;
};

export function createApp(deps: AppDeps): express.Express {
  const log = deps.log ?? (() => undefined);
  const allowed = deps.allowedOrigins ?? [];
  const app = express();
  app.disable("x-powered-by");
  app.set("trust proxy", 1); // Azure Container Apps: the client IP is in X-Forwarded-For

  app.use((_req, res, next) => {
    res.setHeader("X-Content-Type-Options", "nosniff");
    res.setHeader("Referrer-Policy", "no-referrer");
    next();
  });
  app.use(
    cors({
      origin: (origin, callback) => callback(null, !origin || allowed.includes(origin)),
      methods: ["GET", "POST"],
    }),
  );

  // Health probe and docs: before the rate limiter (Azure probes are frequent).
  app.get("/api/health", (_req, res) => {
    res.json({ status: "ok" });
  });
  app.get("/api/openapi.json", (_req, res) => {
    res.json(deps.openapi);
  });
  app.use("/api/docs", swaggerUi.serve, swaggerUi.setup(deps.openapi));

  // Map tiles: static files, many per view, so their own, higher limit.
  app.use(
    "/api/v3/layers",
    rateLimit({ windowMs: 60_000, limit: (deps.rateLimitPerMinute ?? 120) * 10, standardHeaders: "draft-7", legacyHeaders: false,
      message: { error: "Too many requests, try again in a minute" } }),
    v3LayersRouter(deps.releases, log),
  );

  app.use(
    "/api",
    rateLimit({
      windowMs: 60_000,
      limit: deps.rateLimitPerMinute ?? 120,
      standardHeaders: "draft-7",
      legacyHeaders: false,
      message: { error: "Too many requests, try again in a minute" },
    }),
  );
  app.use(express.json({ limit: "50kb" }));

  app.get("/api/modes", (_req, res) => {
    res.json({ modes: Object.values(MODES) });
  });

  app.get("/api/parameters", (_req, res) => {
    res.json({ parameters: PARAMETERS });
  });

  app.get("/api/sources", (_req, res) => {
    res.json({ sources: SOURCES });
  });

  app.get("/api/reference/moon", (_req, res) => {
    if (deps.moonReference === undefined) {
      res.status(404).json({ error: "Lunar reference profile unavailable" });
      return;
    }
    res.json(deps.moonReference);
  });

  app.post("/api/analyze", async (req, res) => {
    try {
      res.json(await analyze(req.body, deps));
    } catch (error) {
      if (error instanceof ValidationError) {
        res.status(400).json({ error: error.message });
        return;
      }
      log("POST /api/analyze failed", error);
      res.status(500).json({ error: "Internal error" });
    }
  });

  app.get("/api/sites/:id", async (req, res) => {
    const site = deps.sites.find((s) => s.id === req.params.id);
    if (!site) {
      res.status(404).json({ error: `Unknown site: ${req.params.id}` });
      return;
    }
    const mode = typeof req.query.mode === "string" ? req.query.mode : "robotics";
    if (!isModeId(mode)) {
      res.status(400).json({ error: `Unknown mode: ${mode}` });
      return;
    }
    try {
      const values = await collectValues(site, deps.connectors, deps.onConnectorError);
      const quality = deps.quality?.(site);
      const definitions = MODES[mode].criteria;
      const a = assess(values, definitions, quality?.sigmas, quality?.flags);
      const criteria = a.criteria;
      const factor = vegetationFactor(values);
      const excluded = factor === 0;
      const total = excluded ? 0 : Math.round(a.total * factor);
      res.json({
        id: site.id,
        name: site.name,
        lat: site.lat,
        lon: site.lon,
        role: site.role,
        ...(site.terrain ? { terrain: site.terrain } : {}),
        mode,
        total,
        criteria,
        ...(excluded ? { excluded: "vegetation" } : {}),
        ...(factor > 0 && factor < 1 ? { vegetationFactor: Math.round(factor * 100) / 100 } : {}),
        coverage: Math.round(a.coverage * 100) / 100,
        totalRange: { min: Math.round(a.totalMin * factor), max: Math.round(a.totalMax * factor) },
        requirements: a.requirements,
        ...(a.failed.length > 0 ? { failedRequirements: a.failed } : {}),
        ...(a.missing.length > 0 ? { missing: a.missing } : {}),
        explanation: explain(a, definitions),
        methodology: { version: METHODOLOGY_VERSION, ...(deps.datasetVersion ? { dataset: deps.datasetVersion } : {}) },
        values,
        sources: deps.sourceNames,
        valueSources: valueSources(values, deps.useFixtures),
        moon: moonValues(deps.moonReference, PARAM_IDS),
      });
    } catch (error) {
      log(`GET /api/sites/${site.id} failed`, error);
      res.status(500).json({ error: "Internal error" });
    }
  });

  app.use("/api/v3", v3Router(deps.releases, log, deps.discoveryUrl));

  app.use("/api", (_req, res) => {
    res.status(404).json({ error: "Unknown route" });
  });

  // Invalid or oversized JSON body: client error, not a server error.
  app.use((error: unknown, _req: Request, res: Response, next: NextFunction) => {
    const type = (error as { type?: string } | null)?.type;
    if (type === "entity.parse.failed") {
      res.status(400).json({ error: "Invalid JSON body" });
      return;
    }
    if (type === "entity.too.large") {
      res.status(413).json({ error: "Body too large" });
      return;
    }
    log("Unhandled error", error);
    if (res.headersSent) {
      next(error);
      return;
    }
    res.status(500).json({ error: "Internal error" });
  });

  return app;
}
