import type { AddressInfo } from "node:net";
import type { Server } from "node:http";
import { mkdir, mkdtemp, readFile, rm, writeFile } from "node:fs/promises";
import { tmpdir } from "node:os";
import path from "node:path";
import { afterAll, beforeAll, describe, expect, it } from "vitest";
import { parse } from "yaml";
import { createApp } from "../src/server/app.js";
import { API_ROOT } from "../src/server/config.js";
import { ReleaseStore } from "../src/v3/store.js";

// A small release, written the way tools/discovery/release.py writes one.
const RID = "r-0a1b2c3d";
const OLD = "r-99999999";
const head = { release: RID, methodology_version: "v3" };

function zone(rank: number) {
  return {
    id: `B.moon-psr.t0.5.m3.${rank}`, rank, scenario: "B", target: "moon-psr", lat: 10 + rank, lon: 20, cells: 4,
    area_km2: 100.1, typicality: { median: Math.round(90 - rank) / 100, p25: 0.8, p75: 0.95 }, high_confidence_share: 1,
    requirements: { climbing_limit_lrv: { met: 4, failed: 0, unknown: 0 } }, suitability_median: 0.5,
    coverage: { windows: 100, valid_unmasked: 98, cover_unknown: 0, cells_by_confidence: { high: 4, medium: 0, low: 0 } },
    monte_carlo: rank === 1 ? { top_decile_share: 0.97 } : null, tiles: ["10,20"],
  };
}

async function writeRelease(dir: string): Promise<void> {
  const w = async (p: string, o: unknown) => {
    await mkdir(path.dirname(path.join(dir, p)), { recursive: true });
    await writeFile(path.join(dir, p), JSON.stringify(o));
  };
  await w("index.json", { current: RID, releases: [
    { id: RID, run: "run-002", methodology_version: "v3", protocol: "validation-protocol-v3", commit: "abc", created: "2026-11-19" },
    { id: OLD, run: "run-001", methodology_version: "v3", protocol: "validation-protocol-v2", commit: "def", created: "2026-11-18" },
  ] });
  await w(`${RID}/release.json`, { ...head, run: "run-002", grid: { tau: [0.5, 0.7, 0.9], min_cells: [1, 3, 9], nominal: { tau: 0.5, min_cells: 3 } } });
  await w(`${RID}/profiles.json`, { ...head, profiles: [{ id: "moon-psr", body: "moon", metrics: { slope_mean: { p50: 9.5 } } }] });
  await w(`${RID}/scenarios.json`, { ...head, scenarios: [
    { id: "B", name: "Robotic lunar exploration", targets: ["moon-psr", "moon-mare-plains"], assessed_targets: ["moon-psr"],
      not_comparable: {}, cannot_assess: ["Traction in regolith."] },
  ] });
  await w(`${RID}/method.json`, { ...head, sources: [{ id: "copernicus-dem-glo30", status: "verified", verified_on: "2026-11-18" }], processing: [{ step: "windows" }] });
  await w(`${RID}/coverage.json`, { ...head, scenarios: { B: { "moon-psr": { land_km2: 1000, classes: { evaluated: { km2: 400, share: 0.4, meaning: "x" } } } } } });
  await w(`${RID}/zones/B/moon-psr/t0.5-m3.json`, { ...head, scenario: "B", target: "moon-psr", tau: 0.5, min_cells: 3,
    zones: Array.from({ length: 250 }, (_, k) => zone(k + 1)) });
  await w(`${OLD}/release.json`, { release: OLD, methodology_version: "v3", run: "run-001", grid: { tau: [0.5], min_cells: [3], nominal: { tau: 0.5, min_cells: 3 } } });
}

type Running = { url: string; close: () => Promise<void> };

async function start(releases?: ReleaseStore): Promise<Running> {
  const openapi = parse(await readFile(path.join(API_ROOT, "openapi.yaml"), "utf8")) as Record<string, unknown>;
  const app = createApp({ sites: [], connectors: [], sourceNames: [], openapi, ...(releases ? { releases } : {}) });
  const server: Server = await new Promise((resolve) => {
    const s = app.listen(0, "127.0.0.1", () => resolve(s));
  });
  const { port } = server.address() as AddressInfo;
  return { url: `http://127.0.0.1:${port}`, close: () => new Promise((r) => server.close(() => r())) };
}

const json = async (url: string): Promise<{ status: number; body: Record<string, any> }> => {
  const res = await fetch(url);
  return { status: res.status, body: (await res.json()) as Record<string, any> };
};

describe("API v3 (static release)", () => {
  let dir: string;
  let api: Running;
  beforeAll(async () => {
    dir = await mkdtemp(path.join(tmpdir(), "releases-"));
    await writeRelease(dir);
    api = await start(await ReleaseStore.open(dir));
  });
  afterAll(async () => {
    await api.close();
    await rm(dir, { recursive: true, force: true });
  });

  it("lists the current release and the previous ones", async () => {
    const { status, body } = await json(`${api.url}/api/v3/releases`);
    expect(status).toBe(200);
    expect(body.current).toBe(RID);
    expect(body.releases.map((r: { id: string }) => r.id)).toEqual([RID, OLD]);
  });

  it("every response carries the release and the methodology version", async () => {
    for (const p of ["profiles", "scenarios", "method", "profiles/moon-psr", "scenarios/B", "coverage?scenario=B&env=moon-psr",
      "zones?scenario=B&env=moon-psr", "zones/B.moon-psr.t0.5.m3.1"]) {
      const { status, body } = await json(`${api.url}/api/v3/${p}`);
      expect(status, p).toBe(200);
      expect(body.release, p).toBe(RID);
      expect(body.methodology_version, p).toBe("v3");
    }
  });

  it("unknown ids return 404 with a message", async () => {
    for (const p of ["profiles/moon-nowhere", "scenarios/Z", "zones/B.moon-psr.t0.5.m3.9999", "zones/B.moon-psr.t0.5.m3.0"]) {
      const { status, body } = await json(`${api.url}/api/v3/${p}`);
      expect(status, p).toBe(404);
      expect(body.error).toMatch(/Unknown/);
    }
  });

  it("invalid queries return 400 and never reach a file path", async () => {
    for (const p of ["zones?scenario=B&env=moon-psr&tau=0.6", "zones?scenario=B&env=moon-psr&min_cells=2",
      "zones?scenario=B&env=..%2F..%2Fetc", "zones?scenario=B", "zones?scenario=B&env=moon-psr&limit=5000",
      "zones?scenario=B&env=moon-mare-plains", "coverage?scenario=B&env=moon-psr&release=..%2Fx",
      "zones/..%2F..%2Fpasswd", "zones/B.moon-psr.t0.6.m3.1"]) {
      const { status, body } = await json(`${api.url}/api/v3/${p}`);
      expect([400, 404], p).toContain(status);
      expect(typeof body.error, p).toBe("string");
    }
    const tau = await json(`${api.url}/api/v3/zones?scenario=B&env=moon-psr&tau=0.6`);
    expect(tau.status).toBe(400);
    expect(tau.body.error).toMatch(/tau/);
  });

  it("a target with no Earth assessment says it is not comparable", async () => {
    const { status, body } = await json(`${api.url}/api/v3/zones?scenario=B&env=moon-mare-plains`);
    expect(status).toBe(400);
    expect(body.error).toMatch(/not assessed/);
  });

  it("zones are ranked, paged and capped", async () => {
    const first = await json(`${api.url}/api/v3/zones?scenario=B&env=moon-psr`);
    expect(first.body.total).toBe(250);
    expect(first.body.zones).toHaveLength(50);
    expect(first.body.zones[0].rank).toBe(1);
    expect(first.body.tau).toBe(0.5);
    expect(first.body.min_cells).toBe(3);
    const page = await json(`${api.url}/api/v3/zones?scenario=B&env=moon-psr&limit=200&offset=200`);
    expect(page.body.zones).toHaveLength(50);
    expect(page.body.zones[0].rank).toBe(201);
  });

  it("a grid value of the release that was not exported is 404, not an empty list", async () => {
    const { status } = await json(`${api.url}/api/v3/zones?scenario=B&env=moon-psr&tau=0.9&min_cells=9`);
    expect(status).toBe(404);
  });

  it("zone detail has spread, coverage and an explicit null when the Monte Carlo was not run", async () => {
    const one = await json(`${api.url}/api/v3/zones/B.moon-psr.t0.5.m3.1`);
    expect(one.body.zone.typicality).toEqual({ median: 0.89, p25: 0.8, p75: 0.95 });
    expect(one.body.zone.coverage.windows).toBe(100);
    expect(one.body.zone.monte_carlo).toEqual({ top_decile_share: 0.97 });
    const two = await json(`${api.url}/api/v3/zones/B.moon-psr.t0.5.m3.2`);
    expect(two.body.zone.monte_carlo).toBeNull();
    expect(one.body.cannot_assess).toEqual(["Traction in regolith."]);
  });

  it("an older release listed in the index can be read by id", async () => {
    const { status, body } = await json(`${api.url}/api/v3/releases/${OLD}`);
    expect(status).toBe(200);
    expect(body.run).toBe("run-001");
    expect((await json(`${api.url}/api/v3/releases/r-deadbeef`)).status).toBe(404);
  });

  it("the contract documents every v3 route", async () => {
    const doc = parse(await readFile(path.join(API_ROOT, "openapi.yaml"), "utf8")) as { paths: Record<string, unknown> };
    for (const p of ["/api/v3/releases", "/api/v3/releases/{id}", "/api/v3/profiles", "/api/v3/profiles/{id}",
      "/api/v3/scenarios", "/api/v3/scenarios/{id}", "/api/v3/zones", "/api/v3/zones/{id}", "/api/v3/coverage", "/api/v3/method"]) {
      expect(doc.paths[p], p).toBeDefined();
    }
  });
});

describe("API v3 without a release", () => {
  it("answers 503 with a clear message, and the v2 routes keep working", async () => {
    const api = await start();
    const v3 = await json(`${api.url}/api/v3/zones?scenario=B&env=moon-psr`);
    expect(v3.status).toBe(503);
    expect(v3.body.error).toMatch(/release/);
    expect((await fetch(`${api.url}/api/modes`)).status).toBe(200);
    await api.close();
  });
});
