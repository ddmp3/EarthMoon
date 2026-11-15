import { mkdtemp, writeFile } from "node:fs/promises";
import os from "node:os";
import path from "node:path";
import { describe, expect, it, vi } from "vitest";
import { withCache, warmUp } from "../src/sources/cache.js";
import { coordinatesConnector } from "../src/sources/coordinates.js";
import { createPrecomputedConnector, loadPrecomputed } from "../src/sources/precomputed.js";
import { fetchJson, HttpError } from "../src/sources/http.js";
import type { FetchLike } from "../src/sources/http.js";
import { buildSources } from "../src/sources/index.js";
import { createPowerConnector, parsePower, powerUrl } from "../src/sources/power.js";
import { createUsgsConnector, parseUsgsCount, usgsUrl } from "../src/sources/usgs.js";
import { createGvpConnector, GVP_WFS_URL, haversineKm, nearestVolcanoKm, parseVolcanoes } from "../src/sources/gvp.js";
import { REPO_ROOT } from "../src/server/config.js";

const ok = (body: unknown): ReturnType<FetchLike> => Promise.resolve({ ok: true, status: 200, json: async () => body });
const status = (code: number): ReturnType<FetchLike> => Promise.resolve({ ok: false, status: code, json: async () => ({}) });

const POWER_BODY = {
  properties: {
    parameter: {
      T2M: { JAN: -30, ANN: -14.42 },
      T2M_MIN: { ANN: -48.55 },
      T2M_MAX: { ANN: 16.81 },
      WS2M: { ANN: 3.08 },
      RH2M: { ANN: 94.36 },
      PRECTOTCORR: { ANN: 0.85 },
      ALLSKY_SFC_SW_DWN: { ANN: 2.32 },
    },
  },
};

describe("fetchJson", () => {
  it("retries on 502 then succeeds", async () => {
    const calls: number[] = [];
    const impl: FetchLike = () => (calls.push(1) < 3 ? status(502) : ok({ fine: true }));
    expect(await fetchJson("https://x.test/a", { fetchImpl: impl, backoffMs: 0 })).toEqual({ fine: true });
    expect(calls).toHaveLength(3);
  });

  it("gives up after the allowed attempts, with the HTTP error", async () => {
    const impl = vi.fn<FetchLike>(() => status(503));
    await expect(fetchJson("https://x.test/a", { fetchImpl: impl, backoffMs: 0, retries: 1 })).rejects.toMatchObject({ status: 503 });
    expect(impl).toHaveBeenCalledTimes(2);
  });

  it("does not retry on a 4xx error", async () => {
    const impl = vi.fn<FetchLike>(() => status(404));
    await expect(fetchJson("https://x.test/a", { fetchImpl: impl, backoffMs: 0 })).rejects.toBeInstanceOf(HttpError);
    expect(impl).toHaveBeenCalledTimes(1);
  });

  it("retries on network error", async () => {
    let n = 0;
    const impl: FetchLike = () => (n++ === 0 ? Promise.reject(new Error("ECONNRESET")) : ok({ a: 1 }));
    expect(await fetchJson("https://x.test/a", { fetchImpl: impl, backoffMs: 0 })).toEqual({ a: 1 });
  });

  it("aborts a request that is too slow", async () => {
    const slow: FetchLike = (_u, init) =>
      new Promise((_resolve, reject) => init?.signal?.addEventListener("abort", () => reject(new Error("aborted"))));
    await expect(fetchJson("https://x.test/a", { fetchImpl: slow, timeoutMs: 20, retries: 0 })).rejects.toThrow("aborted");
  });
});

describe("NASA POWER", () => {
  it("builds the climatology URL with the 7 parameters", () => {
    const url = new URL(powerUrl(75.38, -89.67));
    expect(url.origin + url.pathname).toBe("https://power.larc.nasa.gov/api/temporal/climatology/point");
    expect(url.searchParams.get("parameters")).toBe("T2M,T2M_MIN,T2M_MAX,WS2M,RH2M,PRECTOTCORR,ALLSKY_SFC_SW_DWN");
    expect(url.searchParams.get("latitude")).toBe("75.38");
    expect(url.searchParams.get("longitude")).toBe("-89.67");
  });

  it("translates the response into catalog identifiers (annual means)", () => {
    expect(parsePower(POWER_BODY)).toEqual({
      t2m_mean: -14.42,
      t2m_min: -48.55,
      t2m_max: 16.81,
      wind: 3.08,
      humidity: 94.36,
      precipitation: 0.85,
      solar: 2.32,
    });
  });

  it("turns -999 (no data) and missing fields into null", () => {
    const body = { properties: { parameter: { T2M: { ANN: -999 }, WS2M: {} } } };
    const out = parsePower(body);
    expect(out.t2m_mean).toBeNull();
    expect(out.wind).toBeNull();
    expect(out.solar).toBeNull();
  });

  it("rejects a response with an unexpected shape", () => {
    expect(() => parsePower({ oops: true })).toThrow();
    expect(() => parsePower(null)).toThrow();
  });

  it("the connector queries the site URL", async () => {
    const impl = vi.fn<FetchLike>(() => ok(POWER_BODY));
    const values = await createPowerConnector({ fetchImpl: impl })({ lat: 75.38, lon: -89.67 });
    expect(values.t2m_min).toBe(-48.55);
    expect(impl.mock.calls[0]?.[0]).toBe(powerUrl(75.38, -89.67));
  });
});

describe("USGS", () => {
  it("construit l'URL de comptage (M ≥ 2,5, 300 km, depuis 2000)", () => {
    const url = new URL(usgsUrl(75.38, -89.67));
    expect(url.pathname).toBe("/fdsnws/event/1/count");
    expect(Object.fromEntries(url.searchParams)).toMatchObject({ maxradiuskm: "300", minmagnitude: "2.5", starttime: "2000-01-01", latitude: "75.38", longitude: "-89.67" });
  });

  it("reads the earthquake count", async () => {
    expect(parseUsgsCount({ count: 18, maxAllowed: 20000 })).toBe(18);
    const values = await createUsgsConnector({ fetchImpl: () => ok({ count: 18 }) })({ lat: 1, lon: 2 });
    expect(values).toEqual({ quake_count: 18 });
  });

  it.each([[{}], [{ count: "18" }], [{ count: -1 }], [{ count: 1.5 }], [null]])("refuse %j", (body) => {
    expect(() => parseUsgsCount(body)).toThrow();
  });
});

describe("cache", () => {
  it("queries the source only once for the same position", async () => {
    const inner = vi.fn(async () => ({ quake_count: 5 }));
    const cached = withCache(inner);
    await cached({ lat: 10.0001, lon: 20 });
    await cached({ lat: 10.0004, lon: 20 });
    expect(inner).toHaveBeenCalledTimes(1);
    await cached({ lat: 11, lon: 20 });
    expect(inner).toHaveBeenCalledTimes(2);
  });

  it("shares the call between concurrent requests", async () => {
    let release: () => void = () => undefined;
    const gate = new Promise<void>((r) => (release = r));
    const inner = vi.fn(async () => {
      await gate;
      return { quake_count: 1 };
    });
    const cached = withCache(inner);
    const both = Promise.all([cached({ lat: 1, lon: 1 }), cached({ lat: 1, lon: 1 })]);
    release();
    expect(await both).toEqual([{ quake_count: 1 }, { quake_count: 1 }]);
    expect(inner).toHaveBeenCalledTimes(1);
  });

  it("expires after the TTL and never caches a failure", async () => {
    let t = 0;
    let fail = true;
    const inner = vi.fn(async () => {
      if (fail) throw new Error("down");
      return { quake_count: 2 };
    });
    const cached = withCache(inner, { ttlMs: 100, now: () => t });
    await expect(cached({ lat: 1, lon: 1 })).rejects.toThrow("down");
    fail = false;
    expect(await cached({ lat: 1, lon: 1 })).toEqual({ quake_count: 2 });
    expect(inner).toHaveBeenCalledTimes(2);
    await cached({ lat: 1, lon: 1 });
    expect(inner).toHaveBeenCalledTimes(2);
    t = 101;
    await cached({ lat: 1, lon: 1 });
    expect(inner).toHaveBeenCalledTimes(3);
  });

  it("returns copies: changing the result does not pollute the cache", async () => {
    const cached = withCache(async () => ({ quake_count: 3 }));
    const first = await cached({ lat: 1, lon: 1 });
    first.quake_count = 999;
    expect(await cached({ lat: 1, lon: 1 })).toEqual({ quake_count: 3 });
  });

  it("warmUp warms the cache without ever failing", async () => {
    const good = vi.fn(async () => ({ quake_count: 1 }));
    await warmUp([good, async () => { throw new Error("x"); }], [{ lat: 1, lon: 1 }, { lat: 2, lon: 2 }]);
    expect(good).toHaveBeenCalledTimes(2);
  });
});

describe("precomputed values (DEM, MODIS) and coordinates", () => {
  const sites = [
    { id: "a", lat: -24.5, lon: -69.25, precomputed: { slope_mean: 6, slope_max: 28, roughness: 25, elevation: 2400, source: "Copernicus" } },
    { id: "b", lat: 1, lon: 2, precomputed: { slope_mean: null, slope_max: 3, roughness: "x", elevation: 5 } },
    { id: "c", lat: 3, lon: 4 },
  ];

  it("finds the site by its coordinates", async () => {
    expect(await createPrecomputedConnector(sites)({ lat: -24.5, lon: -69.25 })).toEqual({ slope_mean: 6, slope_max: 28, roughness: 25, elevation: 2400 });
  });

  it("sets null for non-numbers, and returns nothing for an unknown or uncomputed site", async () => {
    const conn = createPrecomputedConnector(sites);
    expect(await conn({ lat: 1, lon: 2 })).toEqual({ slope_mean: null, slope_max: 3, roughness: null, elevation: 5 });
    expect(await conn({ lat: 3, lon: 4 })).toEqual({});
    expect(await conn({ lat: 50, lon: 50 })).toEqual({});
  });

  it("also passes MODIS values, and only the parameters present", async () => {
    const conn = createPrecomputedConnector([
      { lat: -3.47, lon: -62.37, precomputed: { ndvi: 0.85, lst_day: 31, lst_night: 22, lst_amplitude: 9, modis_source: "x" } },
    ]);
    expect(await conn({ lat: -3.47, lon: -62.37 })).toEqual({ ndvi: 0.85, lst_day: 31, lst_night: 22, lst_amplitude: 9 });
  });

  it("reads the file produced by tools/precompute", async () => {
    const dir = await mkdtemp(path.join(os.tmpdir(), "geo-"));
    const file = path.join(dir, "candidates-precomputed.json");
    await writeFile(file, JSON.stringify(sites));
    expect(await loadPrecomputed(file)).toHaveLength(3);
    await writeFile(file, JSON.stringify({ nope: 1 }));
    await expect(loadPrecomputed(file)).rejects.toThrow("Invalid precomputed");
  });

  it("latitude_abs = |latitude|", async () => {
    expect(await coordinatesConnector({ lat: -24.5, lon: 0 })).toEqual({ latitude_abs: 24.5 });
  });
});

describe("buildSources", () => {
  it("fixtures mode: coordinates + sample values, with a warning", async () => {
    const set = await buildSources(path.join(REPO_ROOT, "data"), true);
    expect(set.names).toEqual(["coordinates", "fixtures (sample values)"]);
    expect(set.notes[0]).toContain("not for the demo");
    const merged = Object.assign({}, ...(await Promise.all(set.connectors.map((c) => c({ lat: 75.38, lon: -89.67 })))));
    expect(merged).toMatchObject({ latitude_abs: 75.38, t2m_min: -48.55 });
  });

  it("real mode without a precomputed file: POWER + USGS, and notes what is missing", async () => {
    const dir = await mkdtemp(path.join(os.tmpdir(), "data-"));
    const set = await buildSources(dir, false);
    expect(set.names).toEqual(["coordinates", "NASA POWER", "USGS Earthquake Catalog", "Smithsonian GVP"]);
    expect(set.notes.join(" ")).toMatch(/candidates-precomputed\.json is missing/);
  });

  it("real mode with geometry only: flags that MODIS is missing", async () => {
    const dir = await mkdtemp(path.join(os.tmpdir(), "data-"));
    await writeFile(path.join(dir, "candidates-precomputed.json"), JSON.stringify([{ id: "a", lat: 1, lon: 2, precomputed: { slope_mean: 4 } }]));
    const set = await buildSources(dir, false);
    expect(set.names).toContain("Copernicus DEM (precomputed)");
    expect(set.connectors).toHaveLength(5);
    expect(set.notes.join(" ")).toMatch(/has no MODIS/);
  });

  it("real mode with geometry and MODIS: a single precomputed connector for both", async () => {
    const dir = await mkdtemp(path.join(os.tmpdir(), "data-"));
    await writeFile(path.join(dir, "candidates-precomputed.json"), JSON.stringify([{ id: "a", lat: 1, lon: 2, precomputed: { slope_mean: 4, ndvi: 0.05 } }]));
    const set = await buildSources(dir, false);
    expect(set.names).toContain("Copernicus DEM + MODIS (precomputed)");
    expect(set.notes.join(" ")).not.toMatch(/has no MODIS/);
  });
});

describe("Smithsonian GVP (volcano_distance)", () => {
  const WFS = {
    type: "FeatureCollection",
    features: [
      // Latitude/Longitude attributes present: they take precedence over the geometry
      { type: "Feature", geometry: { type: "Point", coordinates: [-155.47, 19.82] }, properties: { Volcano_Name: "Mauna Kea", Latitude: 19.82, Longitude: -155.47 } },
      // No attributes: geometry read as [lon, lat]
      { type: "Feature", geometry: { type: "Point", coordinates: [-67.73, -23.37] }, properties: { Volcano_Name: "Lascar" } },
      { type: "Feature", geometry: null, properties: { Volcano_Name: "no position" } },
      { type: "Feature", geometry: { type: "Point", coordinates: [500, 500] }, properties: {} },
    ],
  };

  it("haversine: 1° of longitude at the equator ≈ 111.2 km; same point = 0", () => {
    expect(haversineKm(0, 0, 0, 1)).toBeCloseTo(111.19, 1);
    expect(haversineKm(45, 7, 45, 7)).toBe(0);
    expect(haversineKm(0, 179.5, 0, -179.5)).toBeCloseTo(111.19, 1); // crosses the antimeridian
  });

  it("reads volcanoes from the GeoJSON and ignores entries without a valid position", () => {
    const v = parseVolcanoes(WFS);
    expect(v).toEqual([
      { lat: 19.82, lon: -155.47, name: "Mauna Kea" },
      { lat: -23.37, lon: -67.73, name: "Lascar" },
    ]);
  });

  it.each([[{}], [{ features: [] }], [{ features: [{ geometry: null }] }], [null]])("refuse %j", (body) => {
    expect(() => parseVolcanoes(body)).toThrow();
  });

  it("distance to the nearest volcano", () => {
    const v = parseVolcanoes(WFS);
    expect(nearestVolcanoKm(v, 19.82, -155.47)).toBe(0);
    expect(nearestVolcanoKm(v, -24.5, -69.25)).toBeGreaterThan(150);
    expect(nearestVolcanoKm(v, -24.5, -69.25)).toBeLessThan(220);
  });

  it("the connector loads the list only once and rounds to 0.1 km", async () => {
    const impl = vi.fn<FetchLike>(() => ok(WFS));
    const conn = createGvpConnector({ fetchImpl: impl, url: GVP_WFS_URL });
    const [a, b] = await Promise.all([conn({ lat: 19.82, lon: -155.47 }), conn({ lat: -24.5, lon: -69.25 })]);
    expect(a).toEqual({ volcano_distance: 0 });
    expect(Number.isInteger((b.volcano_distance as number) * 10)).toBe(true);
    await conn({ lat: 0, lon: 0 });
    expect(impl).toHaveBeenCalledTimes(1);
  });

  it("a load failure is not remembered, and the list is reloaded after the TTL", async () => {
    let t = 0;
    let fail = true;
    const impl = vi.fn<FetchLike>(() => (fail ? status(404) : ok(WFS)));
    const conn = createGvpConnector({ fetchImpl: impl, ttlMs: 1000, now: () => t, backoffMs: 0 });
    await expect(conn({ lat: 0, lon: 0 })).rejects.toThrow();
    fail = false;
    await conn({ lat: 0, lon: 0 });
    await conn({ lat: 1, lon: 1 });
    expect(impl).toHaveBeenCalledTimes(2);
    t = 1001;
    await conn({ lat: 0, lon: 0 });
    expect(impl).toHaveBeenCalledTimes(3);
  });

  it("the default URL asks for Holocene volcanoes as GeoJSON, lon/lat order", () => {
    const url = new URL(GVP_WFS_URL);
    expect(url.searchParams.get("typeName")).toBe("GVP-VOTW:Smithsonian_VOTW_Holocene_Volcanoes");
    expect(url.searchParams.get("outputFormat")).toBe("application/json");
    expect(url.searchParams.get("srsName")).toBe("EPSG:4326");
  });
});
