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
  it("resolves a predefined mode", () => {
    const r = resolveRequest({ mode: "colony" });
    expect(r).toEqual({ mode: "colony", criteria: MODES.colony.criteria, bareSoilOnly: true });
  });

  it("accepts free criteria and disabling the filter", () => {
    const r = resolveRequest({
      criteria: [{ param: "wind", max: 3, tolerance: 3, weight: 1 }],
      bareSoilOnly: false,
    });
    expect(r.mode).toBe("custom");
    expect(r.bareSoilOnly).toBe(false);
    expect(r.criteria).toEqual([{ param: "wind", max: 3, tolerance: 3, weight: 1 }]);
  });

  it.each([
    ["missing body", null],
    ["mode et criteria ensemble", { mode: "robotics", criteria: [] }],
    ["ni mode ni criteria", {}],
    ["unknown mode", { mode: "mars" }],
    ["criteria vide", { criteria: [] }],
    ["non-object criterion", { criteria: [42] }],
    ["unknown parameter", { criteria: [{ param: "gravity", max: 1, tolerance: 1, weight: 1 }] }],
    ["no bound", { criteria: [{ param: "wind", tolerance: 1, weight: 1 }] }],
    ["min > max", { criteria: [{ param: "wind", min: 5, max: 1, tolerance: 1, weight: 1 }] }],
    ["negative tolerance", { criteria: [{ param: "wind", max: 1, tolerance: -1, weight: 1 }] }],
    ["poids nul", { criteria: [{ param: "wind", max: 1, tolerance: 1, weight: 0 }] }],
    ["non-numeric bound", { criteria: [{ param: "wind", max: "3", tolerance: 1, weight: 1 }] }],
    [
      "duplicate parameter",
      {
        criteria: [
          { param: "wind", max: 1, tolerance: 1, weight: 1 },
          { param: "wind", max: 2, tolerance: 1, weight: 1 },
        ],
      },
    ],
    ["non-boolean bareSoilOnly", { mode: "robotics", bareSoilOnly: "no" }],
  ])("refuse : %s", (_label, body) => {
    expect(() => resolveRequest(body)).toThrow(ValidationError);
  });
});

describe("collectValues", () => {
  const site: Site = { id: "x", name: "X", lat: 1, lon: 2, role: "candidate" };

  it("merges connectors and ignores the ones that fail", async () => {
    const onError = vi.fn();
    const values = await collectValues(
      site,
      [async () => ({ wind: 2 }), async () => Promise.reject(new Error("panne")), async () => ({ solar: 3 })],
      onError,
    );
    expect(values).toEqual({ wind: 2, solar: 3 });
    expect(onError).toHaveBeenCalledOnce();
  });

  it("passes the site coordinates to the connectors", async () => {
    const connector = vi.fn(async () => ({}));
    await collectValues(site, [connector]);
    expect(connector).toHaveBeenCalledWith({ lat: 1, lon: 2 });
  });
});

describe("analyze on the fixtures", () => {
  it.each(["robotics", "calibration", "colony"] as const)(
    "mode %s: Haughton ahead, Amazon excluded and last",
    async (mode) => {
      const response = await analyze({ mode }, await fixtureDeps());
      expect(response.mode).toBe(mode);
      const ids = response.sites.map((s) => s.id);
      expect(ids.at(-1)).toBe("amazon");
      expect(response.sites.at(-1)).toMatchObject({ total: 0, excluded: "vegetation" });
      expect(ids.indexOf("haughton")).toBeLessThan(ids.indexOf("amazon"));
      expect(response.sites[0].criteria).toHaveLength(MODES[mode].criteria.length);
    },
  );

  it("sorts kept sites by descending total", async () => {
    const response = await analyze({ mode: "robotics" }, await fixtureDeps());
    const kept = response.sites.filter((s) => !s.excluded).map((s) => s.total);
    expect(kept).toEqual([...kept].sort((a, b) => b - a));
  });

  it("scores the Amazon when the bare-soil filter is off", async () => {
    const response = await analyze(
      { criteria: [{ param: "humidity", min: 80, tolerance: 10, weight: 1 }], bareSoilOnly: false },
      await fixtureDeps(),
    );
    expect(response.sites.every((s) => s.excluded === undefined)).toBe(true);
    expect(response.sites.find((s) => s.id === "amazon")?.total).toBe(100);
  });

  it("returns a site without values with missing criteria, no error", async () => {
    const response = await analyze(
      { mode: "colony" },
      { sites: [{ id: "vide", name: "Vide", lat: 0, lon: 0, role: "candidate" }], connectors: [async () => ({})] },
    );
    expect(response.sites[0].total).toBe(0);
    expect(response.sites[0].criteria.every((c) => c.verdict === "missing")).toBe(true);
  });

  it("respects the concurrency limit", async () => {
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

  it("propagates a ValidationError without querying the connectors", async () => {
    const connector = vi.fn(async () => ({}));
    await expect(
      analyze({ mode: "mars" }, { sites: [{ id: "a", name: "A", lat: 0, lon: 0, role: "candidate" }], connectors: [connector] }),
    ).rejects.toThrow(ValidationError);
    expect(connector).not.toHaveBeenCalled();
  });
});

describe("loadFixtures", () => {
  it("rejects a file without a sites array", async () => {
    const bad = fileURLToPath(new URL("../package.json", import.meta.url));
    await expect(loadFixtures(bad)).rejects.toThrow("Invalid fixtures file");
  });

  it("returns an empty object for unknown coordinates", async () => {
    const connector = createFixtureConnector(await loadFixtures(FIXTURES));
    expect(await connector({ lat: 0, lon: 0 })).toEqual({});
  });
});
