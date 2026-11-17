"""Before / after comparison of the scientific corrections, one step at a time (docs/SCIENTIFIC_VALIDATION.md).

Each step applies one more correction to the previous one and is scored with the Python reference scorer.
For every step and mode the script reports, against the v1 baseline:
    * Spearman rank correlation of the totals (1 = same ranking),
    * how many of the baseline top 10 are still in the top 10,
    * how many team expectations (known_for, data/candidates.json) are met (top half of the ranked sites).

Inputs, all versioned:
    data/reference/baseline-v1-values.json   values the v1 API used (live sources read on 2026-11-17)
    data/dataset-v2.json                     frozen data set of methodology v2
    data/reference/scenarios-v2.json         scenario definitions of methodology v2

    python tools/validation/ablation.py            # prints the Markdown table

Standard library only.
"""
from __future__ import annotations

import copy
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "scoring"))
import score_sites as ss  # noqa: E402

DATA = os.path.join(HERE, "..", "..", "data")
MODES = ("robotics", "calibration", "colony")


def load(name: str):
    with open(os.path.join(DATA, name), encoding="utf-8") as fh:
        return json.load(fh)


def ranks(values: list[float]) -> list[float]:
    """Average ranks (ties share the mean rank)."""
    order = sorted(range(len(values)), key=lambda i: values[i])
    out = [0.0] * len(values)
    i = 0
    while i < len(order):
        j = i
        while j + 1 < len(order) and values[order[j + 1]] == values[order[i]]:
            j += 1
        for k in range(i, j + 1):
            out[order[k]] = (i + j) / 2 + 1
        i = j + 1
    return out


def spearman(a: list[float], b: list[float]) -> float:
    ra, rb = ranks(a), ranks(b)
    n = len(ra)
    ma, mb = sum(ra) / n, sum(rb) / n
    cov = sum((x - ma) * (y - mb) for x, y in zip(ra, rb))
    va, vb = sum((x - ma) ** 2 for x in ra), sum((y - mb) ** 2 for y in rb)
    return cov / (va * vb) ** 0.5 if va > 0 and vb > 0 else float("nan")


def replace(criteria: list[dict], param: str, new: dict | None) -> list[dict]:
    """Criteria with `param` replaced by `new` (weight and group kept), or dropped when `new` is None."""
    out = []
    for c in criteria:
        if c["param"] != param:
            out.append(c)
        elif new is not None:
            out.append({**{k: v for k, v in c.items() if k in ("weight", "group")}, **new})
    return out


def steps(v1_sites: list[dict], v2_sites: list[dict]) -> list[tuple[str, list[dict], dict[str, list[dict]]]]:
    """(label, sites, modes) of each cumulative step."""
    v1 = copy.deepcopy(ss.MODES_V1)
    out = [("S0 baseline (v1 criteria, v1 data)", v1_sites, v1)]

    out.append(("S1 + corrected data: temperatures at site elevation, 40 m terrain grid, unrepresentative reanalysis values left missing", v2_sites, v1))

    m = copy.deepcopy(v1)
    quakes = {"param": "quake_m45_count", "max": 5, "tolerance": 45}
    for mode in MODES:
        m[mode] = replace(m[mode], "quake_count", quakes)
    out.append(("S2 + earthquakes M >= 4.5 instead of M >= 2.5", v2_sites, m))

    m = copy.deepcopy(m)
    for mode in MODES:
        m[mode] = replace(m[mode], "volcano_distance", None)
    out.append(("S3 + distance to a volcano removed", v2_sites, m))

    m = copy.deepcopy(m)
    m["calibration"] = replace(m["calibration"], "humidity", {"param": "specific_humidity", "max": 3, "tolerance": 5})
    out.append(("S4 + specific humidity instead of relative humidity", v2_sites, m))

    m = copy.deepcopy(m)
    v2 = ss.load_modes()
    by_param = {c["param"]: c for c in v2["robotics"]}
    keep = ("param", "min", "max", "tolerance", "toleranceBelow", "toleranceAbove", "required")
    pick = lambda p: {k: v for k, v in by_param[p].items() if k in keep}  # noqa: E731
    m["robotics"] = replace(m["robotics"], "slope_mean", pick("slope_mean"))
    m["robotics"] = replace(m["robotics"], "roughness", pick("roughness_detrended"))
    m["robotics"] = replace(m["robotics"], "slope_max", pick("traversable_15"))
    out.append(("S5 + detrended roughness, lunar percentiles as tolerances, traversable share as a hard requirement", v2_sites, m))

    out.append(("S6 methodology v2 (irrelevant criteria removed, equal weights, permafrost thresholds, slope requirement for the base)", v2_sites, v2))
    return out


def summarize(res: dict, baseline: dict | None, expected: set[str]) -> dict:
    ranked = res["sites"]
    totals = {s["id"]: s["total"] for s in ranked}
    half = (len(ranked) + 1) // 2
    position = {s["id"]: i + 1 for i, s in enumerate(ranked)}
    met = sorted(i for i in expected if position.get(i, 10 ** 6) <= half)
    out = {"top10": [s["id"] for s in ranked[:10]], "totals": totals, "met": met, "expected": len(expected),
           "coverage": sum(s["coverage"] for s in ranked) / len(ranked),
           "failed": sum(s["requirements"] == "failed" for s in ranked)}
    if baseline is not None:
        common = sorted(set(totals) & set(baseline["totals"]))
        out["spearman"] = spearman([baseline["totals"][i] for i in common], [totals[i] for i in common])
        out["top10_kept"] = len(set(out["top10"]) & set(baseline["top10"]))
    return out


def run() -> list[dict]:
    candidates = load("candidates.json")
    expected = {m: {c["id"] for c in candidates if m in c.get("known_for", [])} for m in MODES}
    v1_sites = load(os.path.join("reference", "baseline-v1-values.json"))["sites"]
    v2_sites = ss.dataset_sites()
    rows, baseline = [], {}
    for label, sites, modes in steps(v1_sites, v2_sites):
        row = {"label": label, "modes": {}}
        for mode in MODES:
            summary = summarize(ss.analyze(sites, mode, modes=modes), baseline.get(mode), expected[mode])
            baseline.setdefault(mode, summary)
            row["modes"][mode] = summary
        rows.append(row)
    return rows


def to_markdown(rows: list[dict]) -> str:
    lines = ["| Step | Mode | Rank correlation with baseline | Baseline top 10 kept | Expectations met | Mean coverage | Sites failing a requirement |",
             "|---|---|---|---|---|---|---|"]
    for row in rows:
        for mode in MODES:
            s = row["modes"][mode]
            rho = f"{s['spearman']:.2f}" if "spearman" in s else "1.00"
            kept = s.get("top10_kept", 10)
            lines.append(f"| {row['label']} | {mode} | {rho} | {kept}/10 | {len(s['met'])}/{s['expected']} | "
                         f"{s['coverage']:.0%} | {s['failed']} |")
    total = lambda row: (sum(len(row["modes"][m]["met"]) for m in MODES), sum(row["modes"][m]["expected"] for m in MODES))  # noqa: E731
    lines += ["", "Expectations met over the three modes: " + "; ".join(f"{r['label'].split(' ')[0]} {total(r)[0]}/{total(r)[1]}" for r in rows) + "."]
    return "\n".join(lines) + "\n"


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    print(to_markdown(run()))
