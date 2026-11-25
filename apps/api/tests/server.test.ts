import type { AddressInfo } from "node:net";
import type { Server } from "node:http";
import path from "node:path";
import { afterAll, beforeAll, describe, expect, it } from "vitest";
import { parse } from "yaml";
import { copyFile, mkdir, mkdtemp, readFile, rm } from "node:fs/promises";
import { tmpdir } from "node:os";
import { createFixtureConnector, loadFixtures } from "../src/analyze/fixtures.js";
import type { Connector } from "../src/analyze/analyze.js";
import { createApp } from "../src/server/app.js";
import type { AppDeps } from "../src/server/app.js";
import { REPO_ROOT, API_ROOT } from "../src/server/config.js";
import { loadSites, parseSites } from "../src/server/load.js";
import { PARAMETERS } from "../src/server/parameters.js";
import { PARAM_IDS } from "../src/scoring/index.js";

const DATA = path.join(REPO_ROOT, "data");
const ORIGIN = "https://front.example.net";

type Running = { url: string; close: () => Promise<void> };

async function start(overrides: Partial<AppDeps> = {}, connectors?: Connector[]): Promise<Running> {
  const fixtures = await loadFixtures(path.join(DATA, "fixtures", "site-values.json"));
  const openapi = parse(await readFile(path.join(API_ROOT, "openapi.yaml"), "utf8")) as Record<string, unknown>;
  const app = createApp({
    sites: fixtures.sites,
    connectors: connectors ?? [createFixtureConnector(fixtures)],
    sourceNames: ["fixtures"],
    openapi,
    moonReference: { id: "moon-south-pole", params: {} },
    allowedOrigins: [ORIGIN],
    ...overrides,
  });
  const server: Server = await new Promise((resolve) => {
    const s = app.listen(0, "127.0.0.1", () => resolve(s));
  });
  const { port } = server.address() as AddressInfo;
  return { url: `http://127.0.0.1:${port}`, close: () => new Promise((r) => server.close(() => r())) };
}

const post = (url: string, body: unknown, raw = false): Promise<Response> =>
  fetch(`${url}/api/analyze`, { method: "POST", headers: { "content-type": "application/json" }, body: raw ? (body as string) : JSON.stringify(body) });

describe("HTTP server", () => {
  let api: Running;
  beforeAll(async () => {
    api = await start();
  });
  afterAll(async () => api.close());

  it("GET /api/health answers ok", async () => {
    const res = await fetch(`${api.url}/api/health`);
    expect(res.status).toBe(200);
    expect(await res.json()).toEqual({ status: "ok" });
    expect(res.headers.get("x-powered-by")).toBeNull();
    expect(res.headers.get("x-content-type-options")).toBe("nosniff");
  });

  it("GET /api/modes lists the 3 predefined modes with their criteria", async () => {
    const body = (await (await fetch(`${api.url}/api/modes`)).json()) as { modes: { id: string; criteria: unknown[] }[] };
    expect(body.modes.map((m) => m.id)).toEqual(["robotics", "calibration", "colony"]);
    expect(body.modes.every((m) => m.criteria.length > 0)).toBe(true);
  });

  it("GET /api/parameters covers the whole catalog", async () => {
    const body = (await (await fetch(`${api.url}/api/parameters`)).json()) as { parameters: { id: string }[] };
    expect(body.parameters.map((p) => p.id).sort()).toEqual([...PARAM_IDS].sort());
    expect(PARAMETERS).toHaveLength(PARAM_IDS.length);
  });

  it("GET /api/reference/moon returns the profile, and 404 if absent", async () => {
    expect(await (await fetch(`${api.url}/api/reference/moon`)).json()).toMatchObject({ id: "moon-south-pole" });
    const other = await start({ moonReference: undefined });
    const res = await fetch(`${other.url}/api/reference/moon`);
    expect(res.status).toBe(404);
    await other.close();
  });

  it("POST /api/analyze (mode): contract shape, sorted by descending total, Amazon excluded and last", async () => {
    const res = await post(api.url, { mode: "robotics" });
    expect(res.status).toBe(200);
    const body = (await res.json()) as { mode: string; sites: { id: string; total: number; excluded?: string; criteria: { param: string; value: number | null; score: number; verdict: string }[] }[] };
    expect(body.mode).toBe("robotics");
    // Haughton (sample values): mean slope 7.5° and detrended roughness 9.1 m are inside the lunar interquartile
    // ranges, all ground is under 15°, dry: 100. Atacama: its detrended roughness (2.5 m) is below the lunar 5th
    // percentile (3.3 m), so one criterion out of four scores 0: 75.
    expect(body.sites.map((s) => s.id)).toEqual(["haughton", "atacama", "amazon"]);
    expect(body.sites.map((s) => s.total)).toEqual([100, 75, 0]);
    expect(body.sites[2]?.excluded).toBe("vegetation");
    for (const s of body.sites) {
      expect(s).toMatchObject({ coverage: 1, requirements: "met" });
      for (const c of s.criteria) expect(Object.keys(c)).toEqual(expect.arrayContaining(["param", "value", "score", "verdict", "contribution", "maxContribution"]));
    }
    expect((body as unknown as { methodology: { version: string } }).methodology.version).toBe("2.0.0");
  });

  it("POST /api/analyze (free criteria, filter off) keeps the Amazon in the ranking", async () => {
    const res = await post(api.url, { criteria: [{ param: "humidity", max: 40, tolerance: 30, weight: 1 }], bareSoilOnly: false });
    const body = (await res.json()) as { mode: string; sites: { id: string; total: number; excluded?: string }[] };
    expect(body.mode).toBe("custom");
    expect(body.sites[0]?.id).toBe("atacama");
    expect(body.sites.every((s) => s.excluded === undefined)).toBe(true);
  });

  it.each([
    ["unknown mode", { mode: "mars" }],
    ["neither mode nor criteria", {}],
    ["mode and criteria together", { mode: "robotics", criteria: [{ param: "wind", max: 3, tolerance: 3, weight: 1 }] }],
    ["criterion without a range", { criteria: [{ param: "wind", tolerance: 3, weight: 1 }] }],
    ["unknown parameter", { criteria: [{ param: "gravite", max: 3, tolerance: 3, weight: 1 }] }],
    ["poids nul", { criteria: [{ param: "wind", max: 3, tolerance: 3, weight: 0 }] }],
  ])("POST /api/analyze rejette en 400 : %s", async (_name, body) => {
    const res = await post(api.url, body);
    expect(res.status).toBe(400);
    expect(await res.json()).toEqual({ error: expect.any(String) });
  });

  it("POST /api/analyze: unreadable JSON → 400, huge body → 413", async () => {
    const bad = await post(api.url, "{pas du json", true);
    expect(bad.status).toBe(400);
    expect(await bad.json()).toEqual({ error: "Invalid JSON body" });
    const big = await post(api.url, JSON.stringify({ mode: "robotics", pad: "x".repeat(60_000) }), true);
    expect(big.status).toBe(413);
  });

  it("a failing source does not break the analysis: only missing criteria", async () => {
    const down: Connector = async () => {
      throw new Error("source en panne");
    };
    const errors: string[] = [];
    const flaky = await start({ onConnectorError: (e) => errors.push((e as Error).message) }, [down]);
    const res = await post(flaky.url, { mode: "colony" });
    expect(res.status).toBe(200);
    const body = (await res.json()) as { sites: { total: number; criteria: { verdict: string }[] }[] };
    expect(body.sites).toHaveLength(3);
    expect(body.sites.every((s) => s.total === 0 && s.criteria.every((c) => c.verdict === "missing"))).toBe(true);
    expect(errors.length).toBe(3);
    await flaky.close();
  });

  it("GET /api/sites/{id}: card with raw values and sources", async () => {
    const res = await fetch(`${api.url}/api/sites/haughton?mode=robotics`);
    expect(res.status).toBe(200);
    const body = (await res.json()) as { id: string; total: number; mode: string; values: Record<string, number>; sources: string[]; terrain?: string };
    expect(body).toMatchObject({ id: "haughton", total: 100, mode: "robotics", sources: ["fixtures"], terrain: "impact" });
    expect(body).toMatchObject({ coverage: 1, requirements: "met", explanation: { decisive: [], missing: [] } });
    expect(body.values.t2m_min).toBe(-48.55);
  });

  it("GET /api/sites/{id}: source of each value and lunar reference of the mode's criteria", async () => {
    const moon = {
      params: {
        slope_mean: { min: 5.23, max: 12.89, unit: "°", source: "LOLA" },
        wind: { min: 0, max: 0, unit: "m/s", source: "no atmosphere" },
        roughness: { unit: "m", source: "no value" },
      },
    };
    const real = await start({ moonReference: moon, useFixtures: false });
    const body = (await (await fetch(`${real.url}/api/sites/haughton?mode=robotics`)).json()) as {
      valueSources: Record<string, string>;
      moon: Record<string, unknown>;
    };
    expect(body.valueSources).toMatchObject({ t2m_min: "nasa-power", slope_mean: "copernicus-dem", quake_count: "usgs-comcat" });
    // All sourced parameters, whatever the mode (the front end shows those of its criteria); roughness has no value.
    expect(body.moon).toEqual({
      slope_mean: { min: 5.23, max: 12.89, unit: "°", source: "LOLA" },
      wind: { min: 0, max: 0, unit: "m/s", source: "no atmosphere" },
    });
    await real.close();
    const fixtures = await start({ useFixtures: true });
    const fx = (await (await fetch(`${fixtures.url}/api/sites/haughton`)).json()) as { valueSources: Record<string, string> };
    expect(fx.valueSources.t2m_min).toBe("fixtures");
    await fixtures.close();
  });

  it("GET /api/sources: every catalog parameter has a named Earth source", async () => {
    const { sources } = (await (await fetch(`${api.url}/api/sources`)).json()) as {
      sources: { id: string; name: string; url: string; body: string; params: string[]; terms: string }[];
    };
    const earth = sources.filter((s) => s.body === "earth").flatMap((s) => s.params);
    expect([...earth].sort()).toEqual([...PARAM_IDS].sort());
    expect(new Set(earth).size).toBe(earth.length); // one source per parameter
    for (const s of sources) expect(s.name && s.url.startsWith("https://") && s.terms).toBeTruthy();
  });

  it("GET /api/sites/{id}: Amazon excluded; 404 unknown site; 400 unknown mode", async () => {
    const amazon = (await (await fetch(`${api.url}/api/sites/amazon`)).json()) as { total: number; excluded?: string };
    expect(amazon).toMatchObject({ total: 0, excluded: "vegetation" });
    expect((await fetch(`${api.url}/api/sites/nope`)).status).toBe(404);
    expect((await fetch(`${api.url}/api/sites/haughton?mode=mars`)).status).toBe(400);
  });

  it("unknown route → 404 JSON", async () => {
    const res = await fetch(`${api.url}/api/nimporte`);
    expect(res.status).toBe(404);
    expect(await res.json()).toEqual({ error: "Unknown route" });
  });

  it("CORS: only the front-end origin is allowed", async () => {
    const ok = await fetch(`${api.url}/api/modes`, { headers: { Origin: ORIGIN } });
    expect(ok.headers.get("access-control-allow-origin")).toBe(ORIGIN);
    const ko = await fetch(`${api.url}/api/modes`, { headers: { Origin: "https://autre.example.org" } });
    expect(ko.headers.get("access-control-allow-origin")).toBeNull();
  });

  it("documentation : /api/openapi.json et /api/docs", async () => {
    const spec = (await (await fetch(`${api.url}/api/openapi.json`)).json()) as { openapi: string; paths: Record<string, unknown> };
    expect(spec.openapi).toMatch(/^3\./);
    expect(Object.keys(spec.paths)).toEqual(expect.arrayContaining(["/api/analyze", "/api/sites/{id}", "/api/health"]));
    const docs = await fetch(`${api.url}/api/docs/`);
    expect(docs.status).toBe(200);
    expect(await docs.text()).toContain("swagger");
  });

  it("rate limit: 429 when exceeded, but /api/health stays available", async () => {
    const limited = await start({ rateLimitPerMinute: 3 });
    const codes: number[] = [];
    for (let i = 0; i < 5; i++) codes.push((await fetch(`${limited.url}/api/modes`)).status);
    expect(codes).toEqual([200, 200, 200, 429, 429]);
    expect((await fetch(`${limited.url}/api/health`)).status).toBe(200);
    await limited.close();
  });

  it("rate limit: the cells of a map view have their own, higher limit (a view moves often), like tiles (T45)", async () => {
    const limited = await start({ rateLimitPerMinute: 3 });
    for (let i = 0; i < 4; i++) await fetch(`${limited.url}/api/modes`);
    expect((await fetch(`${limited.url}/api/modes`)).status).toBe(429);
    const cells: number[] = [];
    for (let i = 0; i < 6; i++) cells.push((await fetch(`${limited.url}/api/v3/cells?scenario=B&env=moon-psr&bbox=0,0,1,1`)).status);
    expect(cells.every((c) => c !== 429)).toBe(true);
    await limited.close();
  });
});

describe("openapi.yaml contract ↔ real responses", () => {
  it("the documented paths are exactly the ones the server exposes", async () => {
    const spec = parse(await readFile(path.join(API_ROOT, "openapi.yaml"), "utf8")) as { paths: Record<string, Record<string, unknown>> };
    const v3 = ["/api/v3/coverage", "/api/v3/method", "/api/v3/status", "/api/v3/profiles", "/api/v3/profiles/{id}", "/api/v3/releases",
      "/api/v3/releases/{id}", "/api/v3/scenarios", "/api/v3/scenarios/{id}", "/api/v3/zones", "/api/v3/zones/{id}",
      "/api/v3/layers/{scenario}/{env}/{parameter}/{z}/{x}/{y}.png", "/api/v3/cells", "/api/v3/query", "/api/v3/sites", "/api/v3/changes", "/api/v3/tiles/{tile}/provenance",
      "/api/v3/analogs/target", "/api/v3/analogs/zone/{id}", "/api/v3/analogs/point", "/api/v3/criteria"];
    expect(Object.keys(spec.paths).sort()).toEqual(
      ["/api/analyze", "/api/health", "/api/modes", "/api/parameters", "/api/reference/moon", "/api/sites/{id}", "/api/sources", ...v3].sort(),
    );
    expect(Object.keys(spec.paths["/api/analyze"] ?? {})).toEqual(["post"]);
  });

  it("the contract's ParamId enum is the catalog's", async () => {
    const spec = parse(await readFile(path.join(API_ROOT, "openapi.yaml"), "utf8")) as { components: { schemas: { ParamId: { enum: string[] } } } };
    expect([...spec.components.schemas.ParamId.enum].sort()).toEqual([...PARAM_IDS].sort());
  });
});

describe("site loading", () => {
  it("parseSites drops invalid entries and keeps the others", () => {
    const notes: string[] = [];
    const sites = parseSites(
      [
        { id: "ok", name: "OK", lat: 10, lon: 20, role: "validation", terrain: "desert" },
        { id: "Mauvais Id", name: "x", lat: 0, lon: 0 },
        { id: "ok", name: "doublon", lat: 0, lon: 0 },
        { id: "lat", name: "x", lat: 95, lon: 0 },
        { id: "no-role", name: "S", lat: 1, lon: 2 },
      ],
      (n) => notes.push(n),
    );
    expect(sites.map((s) => s.id)).toEqual(["ok", "no-role"]);
    expect(sites[1]?.role).toBe("candidate");
    expect(notes).toHaveLength(3);
  });

  it("parseSites accepts { sites: [...] } and rejects the rest", () => {
    expect(parseSites({ sites: [{ id: "a", name: "A", lat: 0, lon: 0 }] })).toHaveLength(1);
    expect(() => parseSites("nope")).toThrow();
  });

  it("loadSites falls back to the fixtures when candidates.json is missing", async () => {
    const notes: string[] = [];
    const dir = await mkdtemp(path.join(tmpdir(), "cyberspace-data-"));
    await mkdir(path.join(dir, "fixtures"));
    await copyFile(path.join(DATA, "fixtures", "site-values.json"), path.join(dir, "fixtures", "site-values.json"));
    const sites = await loadSites(dir, (n) => notes.push(n));
    expect(sites.map((s) => s.id)).toEqual(["haughton", "atacama", "amazon"]);
    expect(notes[0]).toContain("candidates.json missing");
    await rm(dir, { recursive: true });
  });

  it("repository data/candidates.json: all sites are valid, with a negative control", async () => {
    const notes: string[] = [];
    const sites = await loadSites(DATA, (n) => notes.push(n));
    expect(notes).toEqual([]);
    expect(sites.length).toBeGreaterThanOrEqual(30);
    expect(sites.some((s) => s.role === "negative")).toBe(true);
    expect(sites.filter((s) => s.role === "validation").length).toBeGreaterThanOrEqual(7);
  });
});
