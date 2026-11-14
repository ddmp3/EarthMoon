import { fileURLToPath } from "node:url";
import { describe, expect, it, vi } from "vitest";
import { analyze, collectValues } from "../src/analyze/analyze.js";
import type { Connector, Site } from "../src/analyze/analyze.js";
import { createFixtureConnector, loadFixtures } from "../src/analyze/fixtures.js";
import { resolveRequest, ValidationError } from "../src/analyze/validate.js";
import { MODES } from "../src/scoring/index.js";

const FIXTURES = fileURLToPath(new URL("../../../data/fixtures/site-values.json", import.meta.url));

async function fixtureDeps(): Promise<{ sites: Site[]; connectors: Connector[] }> {
  const fixtures = await loadFixtures(FIXTURES);
  return { sites: fixtures.sites, connectors: [createFixtureConnector(fixtures)] };
}

describe("resolveRequest", () => {
  it("résout un mode prédéfini", () => {
    const r = resolveRequest({ mode: "colony" });
    expect(r).toEqual({ mode: "colony", criteria: MODES.colony.criteria, bareSoilOnly: true });
  });

  it("accepte des critères libres et la désactivation du filtre", () => {
    const r = resolveRequest({
      criteria: [{ param: "wind", max: 3, tolerance: 3, weight: 1 }],
      bareSoilOnly: false,
    });
    expect(r.mode).toBe("custom");
    expect(r.bareSoilOnly).toBe(false);
    expect(r.criteria).toEqual([{ param: "wind", max: 3, tolerance: 3, weight: 1 }]);
  });

  it.each([
    ["corps absent", null],
    ["mode et criteria ensemble", { mode: "robotics", criteria: [] }],
    ["ni mode ni criteria", {}],
    ["mode inconnu", { mode: "mars" }],
    ["criteria vide", { criteria: [] }],
    ["critère non objet", { criteria: [42] }],
    ["paramètre inconnu", { criteria: [{ param: "gravity", max: 1, tolerance: 1, weight: 1 }] }],
    ["sans borne", { criteria: [{ param: "wind", tolerance: 1, weight: 1 }] }],
    ["min > max", { criteria: [{ param: "wind", min: 5, max: 1, tolerance: 1, weight: 1 }] }],
    ["tolérance négative", { criteria: [{ param: "wind", max: 1, tolerance: -1, weight: 1 }] }],
    ["poids nul", { criteria: [{ param: "wind", max: 1, tolerance: 1, weight: 0 }] }],
    ["borne non numérique", { criteria: [{ param: "wind", max: "3", tolerance: 1, weight: 1 }] }],
    [
      "paramètre en double",
      {
        criteria: [
          { param: "wind", max: 1, tolerance: 1, weight: 1 },
          { param: "wind", max: 2, tolerance: 1, weight: 1 },
        ],
      },
    ],
    ["bareSoilOnly non booléen", { mode: "robotics", bareSoilOnly: "non" }],
  ])("refuse : %s", (_label, body) => {
    expect(() => resolveRequest(body)).toThrow(ValidationError);
  });
});

describe("collectValues", () => {
  const site: Site = { id: "x", name: "X", lat: 1, lon: 2, role: "candidate" };

  it("fusionne les connecteurs et ignore ceux qui échouent", async () => {
    const onError = vi.fn();
    const values = await collectValues(
      site,
      [async () => ({ wind: 2 }), async () => Promise.reject(new Error("panne")), async () => ({ solar: 3 })],
      onError,
    );
    expect(values).toEqual({ wind: 2, solar: 3 });
    expect(onError).toHaveBeenCalledOnce();
  });

  it("passe les coordonnées du site aux connecteurs", async () => {
    const connector = vi.fn(async () => ({}));
    await collectValues(site, [connector]);
    expect(connector).toHaveBeenCalledWith({ lat: 1, lon: 2 });
  });
});

describe("analyze sur les fixtures", () => {
  it.each(["robotics", "calibration", "colony"] as const)(
    "mode %s : Haughton devant, Amazonie écartée en dernier",
    async (mode) => {
      const response = await analyze({ mode }, await fixtureDeps());
      expect(response.mode).toBe(mode);
      const ids = response.sites.map((s) => s.id);
      expect(ids.at(-1)).toBe("amazonie");
      expect(response.sites.at(-1)).toMatchObject({ total: 0, excluded: "vegetation" });
      expect(ids.indexOf("haughton")).toBeLessThan(ids.indexOf("amazonie"));
      expect(response.sites[0].criteria).toHaveLength(MODES[mode].criteria.length);
    },
  );

  it("trie les sites retenus par total décroissant", async () => {
    const response = await analyze({ mode: "robotics" }, await fixtureDeps());
    const kept = response.sites.filter((s) => !s.excluded).map((s) => s.total);
    expect(kept).toEqual([...kept].sort((a, b) => b - a));
  });

  it("score l'Amazonie quand le filtre sol nu est désactivé", async () => {
    const response = await analyze(
      { criteria: [{ param: "humidity", min: 80, tolerance: 10, weight: 1 }], bareSoilOnly: false },
      await fixtureDeps(),
    );
    expect(response.sites.every((s) => s.excluded === undefined)).toBe(true);
    expect(response.sites.find((s) => s.id === "amazonie")?.total).toBe(100);
  });

  it("renvoie un site sans valeurs avec des critères missing, sans erreur", async () => {
    const response = await analyze(
      { mode: "colony" },
      { sites: [{ id: "vide", name: "Vide", lat: 0, lon: 0, role: "candidate" }], connectors: [async () => ({})] },
    );
    expect(response.sites[0].total).toBe(0);
    expect(response.sites[0].criteria.every((c) => c.verdict === "missing")).toBe(true);
  });

  it("respecte la limite de parallélisme", async () => {
    let running = 0;
    let peak = 0;
    const slow: Connector = async () => {
      running++;
      peak = Math.max(peak, running);
      await new Promise((r) => setTimeout(r, 5));
      running--;
      return {};
    };
    const sites: Site[] = Array.from({ length: 10 }, (_, i) => ({
      id: `s${i}`,
      name: `S${i}`,
      lat: i,
      lon: i,
      role: "candidate",
    }));
    await analyze({ mode: "robotics" }, { sites, connectors: [slow], concurrency: 3 });
    expect(peak).toBe(3);
  });

  it("propage une ValidationError sans interroger les connecteurs", async () => {
    const connector = vi.fn(async () => ({}));
    await expect(
      analyze({ mode: "mars" }, { sites: [{ id: "a", name: "A", lat: 0, lon: 0, role: "candidate" }], connectors: [connector] }),
    ).rejects.toThrow(ValidationError);
    expect(connector).not.toHaveBeenCalled();
  });
});

describe("loadFixtures", () => {
  it("refuse un fichier sans tableau sites", async () => {
    const bad = fileURLToPath(new URL("../package.json", import.meta.url));
    await expect(loadFixtures(bad)).rejects.toThrow("Fichier de fixtures invalide");
  });

  it("renvoie un objet vide pour des coordonnées inconnues", async () => {
    const connector = createFixtureConnector(await loadFixtures(FIXTURES));
    expect(await connector({ lat: 0, lon: 0 })).toEqual({});
  });
});
