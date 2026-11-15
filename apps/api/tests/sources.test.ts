import { mkdtemp, writeFile } from "node:fs/promises";
import os from "node:os";
import path from "node:path";
import { describe, expect, it, vi } from "vitest";
import { withCache, warmUp } from "../src/sources/cache.js";
import { coordinatesConnector } from "../src/sources/coordinates.js";
import { createGeometryConnector, loadGeometry } from "../src/sources/geometry.js";
import { fetchJson, HttpError } from "../src/sources/http.js";
import type { FetchLike } from "../src/sources/http.js";
import { buildSources } from "../src/sources/index.js";
import { createPowerConnector, parsePower, powerUrl } from "../src/sources/power.js";
import { createUsgsConnector, parseUsgsCount, usgsUrl } from "../src/sources/usgs.js";
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
  it("réessaie sur 502 puis réussit", async () => {
    const calls: number[] = [];
    const impl: FetchLike = () => (calls.push(1) < 3 ? status(502) : ok({ fine: true }));
    expect(await fetchJson("https://x.test/a", { fetchImpl: impl, backoffMs: 0 })).toEqual({ fine: true });
    expect(calls).toHaveLength(3);
  });

  it("abandonne après les tentatives permises, avec l'erreur HTTP", async () => {
    const impl = vi.fn<FetchLike>(() => status(503));
    await expect(fetchJson("https://x.test/a", { fetchImpl: impl, backoffMs: 0, retries: 1 })).rejects.toMatchObject({ status: 503 });
    expect(impl).toHaveBeenCalledTimes(2);
  });

  it("ne réessaie pas sur une erreur 4xx", async () => {
    const impl = vi.fn<FetchLike>(() => status(404));
    await expect(fetchJson("https://x.test/a", { fetchImpl: impl, backoffMs: 0 })).rejects.toBeInstanceOf(HttpError);
    expect(impl).toHaveBeenCalledTimes(1);
  });

  it("réessaie sur erreur réseau", async () => {
    let n = 0;
    const impl: FetchLike = () => (n++ === 0 ? Promise.reject(new Error("ECONNRESET")) : ok({ a: 1 }));
    expect(await fetchJson("https://x.test/a", { fetchImpl: impl, backoffMs: 0 })).toEqual({ a: 1 });
  });

  it("coupe une requête trop lente", async () => {
    const slow: FetchLike = (_u, init) =>
      new Promise((_resolve, reject) => init?.signal?.addEventListener("abort", () => reject(new Error("aborted"))));
    await expect(fetchJson("https://x.test/a", { fetchImpl: slow, timeoutMs: 20, retries: 0 })).rejects.toThrow("aborted");
  });
});

describe("NASA POWER", () => {
  it("construit l'URL de climatologie avec les 7 paramètres", () => {
    const url = new URL(powerUrl(75.38, -89.67));
    expect(url.origin + url.pathname).toBe("https://power.larc.nasa.gov/api/temporal/climatology/point");
    expect(url.searchParams.get("parameters")).toBe("T2M,T2M_MIN,T2M_MAX,WS2M,RH2M,PRECTOTCORR,ALLSKY_SFC_SW_DWN");
    expect(url.searchParams.get("latitude")).toBe("75.38");
    expect(url.searchParams.get("longitude")).toBe("-89.67");
  });

  it("traduit la réponse en identifiants du catalogue (moyennes annuelles)", () => {
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

  it("transforme -999 (donnée absente) et les champs manquants en null", () => {
    const body = { properties: { parameter: { T2M: { ANN: -999 }, WS2M: {} } } };
    const out = parsePower(body);
    expect(out.t2m_mean).toBeNull();
    expect(out.wind).toBeNull();
    expect(out.solar).toBeNull();
  });

  it("refuse une réponse de forme inattendue", () => {
    expect(() => parsePower({ oops: true })).toThrow();
    expect(() => parsePower(null)).toThrow();
  });

  it("le connecteur interroge l'URL du site", async () => {
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

  it("lit le nombre de séismes", async () => {
    expect(parseUsgsCount({ count: 18, maxAllowed: 20000 })).toBe(18);
    const values = await createUsgsConnector({ fetchImpl: () => ok({ count: 18 }) })({ lat: 1, lon: 2 });
    expect(values).toEqual({ quake_count: 18 });
  });

  it.each([[{}], [{ count: "18" }], [{ count: -1 }], [{ count: 1.5 }], [null]])("refuse %j", (body) => {
    expect(() => parseUsgsCount(body)).toThrow();
  });
});

describe("cache", () => {
  it("n'interroge la source qu'une fois pour la même position", async () => {
    const inner = vi.fn(async () => ({ quake_count: 5 }));
    const cached = withCache(inner);
    await cached({ lat: 10.0001, lon: 20 });
    await cached({ lat: 10.0004, lon: 20 });
    expect(inner).toHaveBeenCalledTimes(1);
    await cached({ lat: 11, lon: 20 });
    expect(inner).toHaveBeenCalledTimes(2);
  });

  it("partage l'appel entre requêtes simultanées", async () => {
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

  it("expire après le TTL et ne met jamais un échec en cache", async () => {
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

  it("renvoie des copies : modifier le résultat ne pollue pas le cache", async () => {
    const cached = withCache(async () => ({ quake_count: 3 }));
    const first = await cached({ lat: 1, lon: 1 });
    first.quake_count = 999;
    expect(await cached({ lat: 1, lon: 1 })).toEqual({ quake_count: 3 });
  });

  it("warmUp préchauffe sans jamais échouer", async () => {
    const good = vi.fn(async () => ({ quake_count: 1 }));
    await warmUp([good, async () => { throw new Error("x"); }], [{ lat: 1, lon: 1 }, { lat: 2, lon: 2 }]);
    expect(good).toHaveBeenCalledTimes(2);
  });
});

describe("géométrie précalculée et coordonnées", () => {
  const sites = [
    { id: "a", lat: -24.5, lon: -69.25, precomputed: { slope_mean: 6, slope_max: 28, roughness: 25, elevation: 2400, source: "Copernicus" } },
    { id: "b", lat: 1, lon: 2, precomputed: { slope_mean: null, slope_max: 3, roughness: "x", elevation: 5 } },
    { id: "c", lat: 3, lon: 4 },
  ];

  it("retrouve le site par ses coordonnées", async () => {
    expect(await createGeometryConnector(sites)({ lat: -24.5, lon: -69.25 })).toEqual({ slope_mean: 6, slope_max: 28, roughness: 25, elevation: 2400 });
  });

  it("met null ce qui n'est pas un nombre, et ne renvoie rien pour un site inconnu ou non calculé", async () => {
    const conn = createGeometryConnector(sites);
    expect(await conn({ lat: 1, lon: 2 })).toEqual({ slope_mean: null, slope_max: 3, roughness: null, elevation: 5 });
    expect(await conn({ lat: 3, lon: 4 })).toEqual({});
    expect(await conn({ lat: 50, lon: 50 })).toEqual({});
  });

  it("lit le fichier produit par enrich_candidates.py", async () => {
    const dir = await mkdtemp(path.join(os.tmpdir(), "geo-"));
    const file = path.join(dir, "candidates-geometry.json");
    await writeFile(file, JSON.stringify(sites));
    expect(await loadGeometry(file)).toHaveLength(3);
    await writeFile(file, JSON.stringify({ nope: 1 }));
    await expect(loadGeometry(file)).rejects.toThrow("invalide");
  });

  it("latitude_abs = |latitude|", async () => {
    expect(await coordinatesConnector({ lat: -24.5, lon: 0 })).toEqual({ latitude_abs: 24.5 });
  });
});

describe("buildSources", () => {
  it("mode fixtures : coordonnées + valeurs d'exemple, avec avertissement", async () => {
    const set = await buildSources(path.join(REPO_ROOT, "data"), true);
    expect(set.names).toEqual(["coordonnées", "fixtures (valeurs d'exemple)"]);
    expect(set.notes[0]).toContain("pas pour la démo");
    const merged = Object.assign({}, ...(await Promise.all(set.connectors.map((c) => c({ lat: 75.38, lon: -89.67 })))));
    expect(merged).toMatchObject({ latitude_abs: 75.38, t2m_min: -48.55 });
  });

  it("mode réel sans fichier de géométrie : POWER + USGS, et note ce qui manque", async () => {
    const dir = await mkdtemp(path.join(os.tmpdir(), "data-"));
    const set = await buildSources(dir, false);
    expect(set.names).toEqual(["coordonnées", "NASA POWER", "USGS Earthquake Catalog"]);
    expect(set.notes.join(" ")).toMatch(/MODIS/);
    expect(set.notes.join(" ")).toMatch(/candidates-geometry\.json absent/);
  });

  it("mode réel avec fichier de géométrie : ajoute le connecteur Copernicus précalculé", async () => {
    const dir = await mkdtemp(path.join(os.tmpdir(), "data-"));
    await writeFile(path.join(dir, "candidates-geometry.json"), JSON.stringify([{ id: "a", lat: 1, lon: 2, precomputed: { slope_mean: 4 } }]));
    const set = await buildSources(dir, false);
    expect(set.names).toContain("Copernicus DEM (précalculé)");
    expect(set.connectors).toHaveLength(4);
  });
});
