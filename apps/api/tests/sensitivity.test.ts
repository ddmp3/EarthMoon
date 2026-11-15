import { describe, expect, it } from "vitest";
import { makeRandom, rankStability } from "../src/scoring/index.js";
import type { Criterion, SensitivityEntry } from "../src/scoring/index.js";

const criteria: Criterion[] = [
  { param: "slope_mean", min: 5, max: 15, tolerance: 10, weight: 3 },
  { param: "wind", max: 3, tolerance: 3, weight: 1 },
];

const entry = (id: string, slope: number, wind: number, factor = 1): SensitivityEntry => ({
  id,
  values: { slope_mean: slope, wind },
  factor,
});

describe("makeRandom", () => {
  it("is deterministic and uniform in [0, 1)", () => {
    const a = makeRandom(7);
    const b = makeRandom(7);
    const xs = Array.from({ length: 1000 }, () => a());
    expect(xs).toEqual(Array.from({ length: 1000 }, () => b()));
    expect(xs.every((x) => x >= 0 && x < 1)).toBe(true);
    expect(xs.reduce((s, x) => s + x, 0) / xs.length).toBeCloseTo(0.5, 1);
  });
});

describe("rankStability", () => {
  it("gives a clear winner a stable rank 1", () => {
    const stability = rankStability([entry("best", 10, 1), entry("mid", 10, 5), entry("worst", 40, 9)], criteria);
    expect(stability.get("best")).toMatchObject({ rankP10: 1, rankP90: 1, topHalfShare: 1 });
    expect(stability.get("worst")).toMatchObject({ rankP10: 3, rankP90: 3 });
  });

  it("shows a wide range for two near-ties", () => {
    const stability = rankStability([entry("a", 10, 3.1), entry("b", 10, 3.2), entry("c", 80, 9)], criteria);
    const a = stability.get("a");
    const b = stability.get("b");
    expect(a && b && Math.max(a.rankP90, b.rankP90)).toBe(2);
    expect(stability.get("c")?.rankP10).toBe(3);
  });

  it("is deterministic: same data, same answer", () => {
    const entries = [entry("a", 10, 3.1), entry("b", 11, 3.0), entry("c", 30, 1)];
    expect(rankStability(entries, criteria)).toEqual(rankStability(entries, criteria));
  });

  it("leaves excluded sites out and ranks the others among themselves", () => {
    const stability = rankStability([entry("kept", 10, 1), entry("gone", 10, 1, 0)], criteria);
    expect(stability.has("gone")).toBe(false);
    expect(stability.get("kept")).toMatchObject({ rankP10: 1, rankP90: 1 });
  });

  it("applies the vegetation factor to the ranking", () => {
    const stability = rankStability([entry("bare", 10, 3), entry("veg", 10, 1, 0.3)], criteria);
    expect(stability.get("bare")?.rankMedian).toBe(1);
    expect(stability.get("veg")?.rankMedian).toBe(2);
  });
});
