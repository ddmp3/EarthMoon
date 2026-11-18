import { readFile } from "node:fs/promises";
import path from "node:path";
import { describe, expect, it } from "vitest";
import { analyze, confidenceOf } from "../src/analyze/analyze.js";
import type { Connector, Site } from "../src/analyze/analyze.js";
import { explain } from "../src/analyze/explain.js";
import { resolveRequest } from "../src/analyze/validate.js";
import { MODES, PARAM_IDS, assess, normal, makeRandom, perturbValues, rankStability, scoreValue } from "../src/scoring/index.js";
import type { Criterion } from "../src/scoring/index.js";
import { REPO_ROOT } from "../src/server/config.js";
import { loadSites } from "../src/server/load.js";
import { buildSources } from "../src/sources/index.js";
import { createDatasetConnector, createDatasetQuality } from "../src/sources/dataset.js";

/** Methodology v2: what the engine must guarantee (docs/METHOD.md). */

const slope: Criterion = { param: "slope_mean", min: 5, max: 13, tolerance: 8, toleranceBelow: 2, toleranceAbove: 8, weight: 1 };
const dry: Criterion = { param: "precipitation", max: 1, tolerance: 1, weight: 1 };
const gate: Criterion = { param: "traversable_15", min: 0.5, tolerance: 0.25, weight: 1, required: true };

describe("asymmetric tolerance (lunar 5th and 95th percentiles)", () => {
  it("uses toleranceBelow under the interval and toleranceAbove over it", () => {
    expect(scoreValue(4, slope)).toBeCloseTo(0.5);
    expect(scoreValue(3, slope)).toBe(0);
    expect(scoreValue(17, slope)).toBeCloseTo(0.5);
    expect(scoreValue(21, slope)).toBe(0);
  });

  it("falls back to tolerance when a side is not given", () => {
    expect(scoreValue(17, { param: "slope_mean", max: 13, tolerance: 8, weight: 1 })).toBeCloseTo(0.5);
  });
});

describe("missing data is neither good nor bad", () => {
  it("reports coverage and the bounds of the total instead of guessing", () => {
    const a = assess({ slope_mean: 8 }, [slope, dry]);
    expect(a.total).toBe(100);
    expect(a.coverage).toBe(0.5);
    expect(a.totalMin).toBe(50);
    expect(a.totalMax).toBe(100);
    expect(a.missing).toEqual(["precipitation"]);
  });

  it("separates a measured zero from an absent value", () => {
    const quakes: Criterion = { param: "quake_m45_count", max: 5, tolerance: 45, weight: 1 };
    expect(assess({ quake_m45_count: 0 }, [quakes])).toMatchObject({ total: 100, coverage: 1, missing: [] });
    expect(assess({ quake_m45_count: null }, [quakes])).toMatchObject({ total: 0, coverage: 0, missing: ["quake_m45_count"] });
  });

  it("gives bounds equal to the total when everything is measured", () => {
    const a = assess({ slope_mean: 17, precipitation: 0 }, [slope, dry]);
    expect(a.totalMin).toBeCloseTo(a.total);
    expect(a.totalMax).toBeCloseTo(a.total);
    expect(a.coverage).toBe(1);
  });
});

describe("hard requirements are never averaged away", () => {
  it("fails a site scoring 0 on a required criterion, whatever its total", () => {
    const a = assess({ slope_mean: 8, precipitation: 0, traversable_15: 0.1 }, [slope, dry, gate]);
    expect(a.total).toBeCloseTo(66.67, 1);
    expect(a.requirements).toBe("failed");
    expect(a.failed).toEqual(["traversable_15"]);
  });

  it("is unknown, not failed, when the required value is missing", () => {
    expect(assess({ slope_mean: 8 }, [slope, gate]).requirements).toBe("unknown");
  });

  it("is met when the required criterion scores above 0", () => {
    expect(assess({ traversable_15: 0.3 }, [gate]).requirements).toBe("met");
  });

  it("ranks a failing site after every passing site", async () => {
    const sites: Site[] = [
      { id: "steep", name: "Steep", lat: 1, lon: 1, role: "candidate" },
      { id: "poor", name: "Poor", lat: 2, lon: 2, role: "candidate" },
    ];
    const connector: Connector = async ({ lat }) =>
      lat === 1 ? { slope_mean: 8, precipitation: 0, traversable_15: 0.05 } : { slope_mean: 30, precipitation: 3, traversable_15: 0.6 };
    const res = await analyze({ criteria: [slope, dry, gate], bareSoilOnly: false }, { sites, connectors: [connector] });
    expect(res.sites.map((s) => s.id)).toEqual(["poor", "steep"]);
    expect(res.sites[1]).toMatchObject({ requirements: "failed", failedRequirements: ["traversable_15"] });
    expect(res.sites[1].total).toBeGreaterThan(res.sites[0].total);
  });

  it("is accepted in free criteria", () => {
    const r = resolveRequest({ criteria: [{ param: "traversable_15", min: 0.5, tolerance: 0.25, weight: 1, required: true, toleranceBelow: 0.25 }] });
    expect(r.criteria[0]).toMatchObject({ required: true, toleranceBelow: 0.25 });
    expect(() => resolveRequest({ criteria: [{ param: "wind", max: 3, tolerance: 3, weight: 1, required: "yes" }] })).toThrow("required");
    expect(() => resolveRequest({ criteria: [{ param: "wind", max: 3, tolerance: 3, weight: 1, toleranceAbove: -1 }] })).toThrow("toleranceAbove");
  });
});

describe("contributions explain the total", () => {
  it("sums to the total, and each criterion is bounded by its share of the weight", () => {
    const a = assess({ slope_mean: 17, precipitation: 0, traversable_15: 1 }, [slope, dry, gate]);
    const sum = a.criteria.reduce((acc, c) => acc + c.contribution, 0);
    expect(sum).toBeCloseTo(a.total);
    for (const c of a.criteria) expect(c.contribution).toBeLessThanOrEqual(c.maxContribution + 1e-9);
  });

  it("orders strengths and weaknesses, and names decisive and missing criteria", () => {
    const criteria = [slope, dry, gate];
    const e = explain(assess({ slope_mean: 17, traversable_15: 0.1 }, criteria), criteria);
    expect(e.weaknesses.map((w) => w.param)).toEqual(["traversable_15", "slope_mean"]);
    expect(e.strengths).toEqual([]);
    expect(e.decisive).toEqual(["traversable_15"]);
    expect(e.missing).toEqual(["precipitation"]);
  });

  it("reports how much of the result rests on expert judgement", () => {
    const criteria: Criterion[] = [{ ...slope, basis: "lunar_measurement" }, { ...dry, basis: "expert_judgement" }];
    expect(explain(assess({ slope_mean: 8, precipitation: 0 }, criteria), criteria).expertShare).toBe(0.5);
  });

  it("carries the uncertainty and the flags of each value", () => {
    const a = assess({ slope_mean: 8 }, [slope], { slope_mean: 1.2 }, { slope_mean: ["flat_artifact"] });
    expect(a.criteria[0]).toMatchObject({ sigma: 1.2, flags: ["flat_artifact"] });
  });
});

describe("Monte Carlo propagation of data uncertainty", () => {
  it("draws a standard normal distribution", () => {
    const random = makeRandom(7);
    const draws = Array.from({ length: 20000 }, () => normal(random));
    const mean = draws.reduce((a, b) => a + b, 0) / draws.length;
    const variance = draws.reduce((a, b) => a + (b - mean) ** 2, 0) / draws.length;
    expect(mean).toBeCloseTo(0, 1);
    expect(variance).toBeCloseTo(1, 1);
  });

  it("perturbs only values with a quantified uncertainty and keeps them in their physical range", () => {
    const random = makeRandom(3);
    for (let i = 0; i < 200; i++) {
      const v = perturbValues({ traversable_15: 0.98, wind: 2, slope_mean: 0.1 }, { traversable_15: 0.2, slope_mean: 1 }, ["traversable_15", "wind", "slope_mean"], random);
      expect(v.traversable_15).toBeLessThanOrEqual(1);
      expect(v.slope_mean).toBeGreaterThanOrEqual(0);
      expect(v.wind).toBe(2);
    }
  });

  it("leaves missing values missing", () => {
    expect(perturbValues({ slope_mean: null }, { slope_mean: 1 }, ["slope_mean"], makeRandom(1)).slope_mean).toBeNull();
  });

  it("widens the interval of the total when the data are uncertain", () => {
    const criteria = [slope];
    const exact = rankStability([{ id: "a", values: { slope_mean: 13 }, factor: 1 }], criteria).get("a");
    const noisy = rankStability([{ id: "a", values: { slope_mean: 13 }, factor: 1, sigmas: { slope_mean: 4 } }], criteria).get("a");
    expect(noisy && exact && noisy.totalP90 - noisy.totalP10).toBeGreaterThan((exact?.totalP90 ?? 0) - (exact?.totalP10 ?? 0));
  });

  it("reports how often a site meets its requirements", () => {
    const s = rankStability([{ id: "a", values: { traversable_15: 0.26 }, factor: 1, sigmas: { traversable_15: 0.1 } }], [gate]).get("a");
    expect(s?.requirementsShare).toBeGreaterThan(0.2);
    expect(s?.requirementsShare).toBeLessThan(0.8);
  });
});

describe("confidence is separate from the score", () => {
  it("is low with little data, an unknown requirement or a wide interval", () => {
    expect(confidenceOf(0.5, "met", 5)).toBe("low");
    expect(confidenceOf(1, "unknown", 5)).toBe("low");
    expect(confidenceOf(1, "met", 40)).toBe("low");
  });

  it("is high only with full data and a narrow interval", () => {
    expect(confidenceOf(1, "met", 10)).toBe("high");
    expect(confidenceOf(0.8, "met", 10)).toBe("medium");
    expect(confidenceOf(1, "met", 20)).toBe("medium");
    expect(confidenceOf(1, "failed", 10)).toBe("high");
  });
});

describe("scenario definitions", () => {
  it("every criterion states its role, basis and rationale", () => {
    for (const mode of Object.values(MODES)) {
      expect(mode.target).not.toBe("");
      for (const c of mode.criteria) {
        expect(c.role, `${mode.id}/${c.param}`).toBeDefined();
        expect(c.basis, `${mode.id}/${c.param}`).toBeDefined();
        expect((c.rationale ?? "").length, `${mode.id}/${c.param}`).toBeGreaterThan(40);
      }
    }
  });

  it("no predefined scenario uses a deprecated indicator", () => {
    const deprecated = ["volcano_distance", "quake_count", "humidity", "roughness", "slope_max", "solar"];
    for (const mode of Object.values(MODES)) {
      expect(mode.criteria.map((c) => c.param).filter((p) => deprecated.includes(p)), mode.id).toEqual([]);
    }
  });

  it("lunar-measured intervals are the interquartile range of the lunar reference, tolerances reach p5 and p95", async () => {
    const moon = JSON.parse(await readFile(path.join(REPO_ROOT, "data", "reference", "moon-south-pole.json"), "utf8")) as {
      terrain_v2: { params: Record<string, { distribution: Record<string, number> }> };
    };
    const measured = Object.values(MODES).flatMap((m) => m.criteria).filter((c) => c.basis === "lunar_measurement");
    expect(measured.length).toBeGreaterThan(0);
    for (const c of measured) {
      const d = moon.terrain_v2.params[c.param].distribution;
      expect(c.min).toBeCloseTo(d.p25, 2);
      expect(c.max).toBeCloseTo(d.p75, 2);
      expect(c.toleranceBelow).toBeCloseTo(d.p25 - d.p5, 2);
      expect(c.toleranceAbove).toBeCloseTo(d.p95 - d.p75, 2);
    }
  });

  it("each instrument of the calibration mode has the same total weight", () => {
    const byGroup = new Map<string, number>();
    for (const c of MODES.calibration.criteria) byGroup.set(c.group ?? "", (byGroup.get(c.group ?? "") ?? 0) + c.weight);
    expect([...byGroup.values()].every((w) => Math.abs(w - 1) < 1e-9)).toBe(true);
  });

  it("is identical to the definitions used by the Python reference scorer", async () => {
    const file = JSON.parse(await readFile(path.join(REPO_ROOT, "data", "reference", "scenarios-v2.json"), "utf8")) as { modes: unknown };
    expect(file.modes).toEqual(JSON.parse(JSON.stringify(MODES)));
  });
});

describe("frozen data set", () => {
  const dataset = {
    version: "9.9.9",
    sites: [{ lat: 1, lon: 2, values: { slope_mean: { value: 6, sigma: 1.5, flags: [] }, ndvi: { value: null, sigma: null, flags: ["x"] }, wind: { value: 3 } } }],
  };

  it("returns values, with null for an absent measurement", async () => {
    expect(await createDatasetConnector(dataset)({ lat: 1, lon: 2 })).toEqual({ slope_mean: 6, ndvi: null, wind: 3 });
    expect(await createDatasetConnector(dataset)({ lat: 9, lon: 9 })).toEqual({});
  });

  it("returns the quantified uncertainties and the flags", () => {
    expect(createDatasetQuality(dataset)({ lat: 1, lon: 2 })).toEqual({ sigmas: { slope_mean: 1.5 }, flags: { ndvi: ["x"] } });
    expect(createDatasetQuality(dataset)({ lat: 9, lon: 9 })).toBeUndefined();
  });

  it("the repository data set covers every site and every parameter of the scenarios, read without any network call", async () => {
    const dataDir = path.join(REPO_ROOT, "data");
    const set = await buildSources(dataDir, false);
    expect(set.datasetVersion).toBe("2.0.0");
    expect(set.connectors).toHaveLength(2);
    const sites = await loadSites(dataDir);
    const res = await analyze({ mode: "robotics" }, { sites, connectors: set.connectors, quality: set.quality, datasetVersion: set.datasetVersion });
    expect(res.methodology).toEqual({ version: "2.0.0", dataset: "2.0.0" });
    expect(res.sites).toHaveLength(sites.length);
    // A site whose reanalysis grid cell is more than 1 km off in elevation has no precipitation value:
    // the criterion is reported missing, never filled in.
    for (const s of res.sites) {
      expect(s.coverage === 1 || (s.missing ?? []).length > 0, s.id).toBe(true);
      expect(s.coverage, s.id).toBeGreaterThanOrEqual(0.75);
    }
    expect(res.sites.find((s) => s.id === "mauna-kea")).toMatchObject({ coverage: 0.75, missing: ["precipitation"] });
    expect(PARAM_IDS).toContain("roughness_detrended");
  });

  it("gives the same totals as the Python reference scorer on the repository data set", async () => {
    const dataDir = path.join(REPO_ROOT, "data");
    const expected = JSON.parse(await readFile(path.join(dataDir, "reference", "expected-rankings-v2.json"), "utf8")) as {
      modes: Record<string, { id: string; total: number; requirements: string | null; coverage: number | null }[]>;
    };
    const set = await buildSources(dataDir, false);
    const sites = await loadSites(dataDir);
    for (const mode of ["robotics", "calibration", "colony"] as const) {
      const res = await analyze({ mode }, { sites, connectors: set.connectors, quality: set.quality });
      expect(res.sites.map((s) => s.id).sort()).toEqual(expected.modes[mode].map((e) => e.id).sort());
      for (const e of expected.modes[mode]) {
        const site = res.sites.find((s) => s.id === e.id);
        if (e.requirements === null) {
          expect(site, `${mode}/${e.id}`).toMatchObject({ total: 0, excluded: "vegetation" });
        } else {
          expect(site, `${mode}/${e.id}`).toMatchObject({ total: e.total, requirements: e.requirements, coverage: e.coverage });
        }
      }
      // Same order for the sites that are not tied.
      const ranked = res.sites.filter((s) => !s.excluded);
      const reference = expected.modes[mode].filter((e) => e.requirements !== null);
      ranked.forEach((s, i) => expect(s.total, `${mode} rank ${i + 1}`).toBe(reference[i].total));
    }
  });
});
