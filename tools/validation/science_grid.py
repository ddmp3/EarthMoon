"""Scientific evaluation grid: the automatable indicators, computed the same way for methodology v1 and v2.

The grid itself (criteria, methods, reference levels, targets) is defined in docs/wiki/v2/SCIENTIFIC_VALIDATION.md.
This script computes every indicator that can be counted from the repository, so that the before / after
comparison does not depend on anyone's opinion. Indicators that need a human judgement are listed in the
document and are not computed here.

    python tools/validation/science_grid.py        # prints the Markdown table (v1 and v2)
    python tools/validation/science_grid.py --v3   # counted indicators of v3 (T49), from the run summaries

Standard library only.
"""
from __future__ import annotations

import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "scoring"))
import score_sites as ss  # noqa: E402

DATA = os.path.join(HERE, "..", "..", "data")
MODES = ("robotics", "calibration", "colony")

# Indicators the audit found scientifically invalid for their use (docs/wiki/v2/SCIENTIFIC_AUDIT.md, findings).
INVALID = {
    "volcano_distance": "V1: distance to a vent is neither a rock type nor evidence of a lava tube",
    "quake_count": "S1: the M >= 2.5 catalog is complete only where networks are dense",
    "humidity": "C2: relative humidity depends on temperature",
    "roughness": "T2: measures the mean tilt, not roughness",
    "slope_max": "T3: extreme-value statistic, and rover limits used as a two-sided similarity target",
    "solar": "C4: annual all-sky insolation is not analogous to lunar polar illumination",
}
# v1: values that were frozen in the repository (the others were read live at request time).
V1_FROZEN = {"slope_mean", "slope_max", "roughness", "elevation", "ndvi", "lst_day", "lst_night", "lst_amplitude", "latitude_abs"}
# v1: where each interval came from (docs/history/v1-scenarios.md).
V1_BASIS = {"slope_mean": "lunar_measurement", "roughness": "lunar_measurement", "slope_max": "mission_requirement"}
ELEVATION_LIMIT_M = 300.0
TEMPERATURES = {"t2m_mean", "t2m_min", "t2m_max"}


def load(*parts: str):
    with open(os.path.join(DATA, *parts), encoding="utf-8") as fh:
        return json.load(fh)


def share(part: float, whole: float) -> str:
    return f"{part:g}/{whole:g} ({part / whole:.0%})" if whole else "n/a"


def indicators(version: str) -> dict[str, str]:
    dataset = load("dataset-v2.json")["sites"]
    snapshot = load("snapshots", "live-sources.json")["sites"]
    precomputed = {s["id"]: s for s in load("candidates-precomputed.json")}
    if version == "v1":
        modes = ss.MODES_V1
        frozen = lambda c: c["param"] in V1_FROZEN  # noqa: E731
        basis = lambda c: V1_BASIS.get(c["param"], "expert_judgement")  # noqa: E731
        with_sigma = lambda c: False  # noqa: E731
        documented = lambda c: False  # noqa: E731
    else:
        modes = ss.load_modes()
        frozen = lambda c: True  # noqa: E731
        basis = lambda c: c.get("basis", "expert_judgement")  # noqa: E731
        sample = next(iter(dataset.values()))["values"]
        with_sigma = lambda c: any(s["values"][c["param"]]["sigma"] is not None for s in dataset.values())  # noqa: E731
        documented = lambda c: all(c.get(k) for k in ("role", "basis", "rationale"))  # noqa: E731
        assert sample
    criteria = [c for m in MODES for c in modes[m]]
    n = len(criteria)

    def weight_share(mode: str) -> float:
        total = sum(c["weight"] for c in modes[mode])
        return sum(c["weight"] for c in modes[mode] if basis(c) != "expert_judgement") / total

    uses_temperature = any(c["param"] in TEMPERATURES for c in criteria)
    mismatch = 0
    for site_id, live in snapshot.items():
        elevation = (precomputed[site_id].get("precomputed") or {}).get("elevation")
        cell = (live.get("power") or {}).get("cell_elevation_m")
        if elevation is None or cell is None or abs(elevation - cell) <= ELEVATION_LIMIT_M:
            continue
        corrected = "elevation_corrected" in dataset[site_id]["values"]["t2m_mean"]["flags"]
        if uses_temperature and (version == "v1" or not corrected):
            mismatch += 1
    return {
        "1 Criteria whose values are frozen and versioned": share(sum(map(frozen, criteria)), n),
        "2 Criteria using an indicator the audit found invalid": share(sum(c["param"] in INVALID for c in criteria), n),
        "3 Sites scored with an air temperature taken more than 300 m off their elevation": f"{mismatch}/{len(snapshot)}",
        "5 Weight resting on a lunar measurement or a documented mission requirement (mean of the modes)":
            f"{sum(weight_share(m) for m in MODES) / len(MODES):.0%} (" + ", ".join(f"{m} {weight_share(m):.0%}" for m in MODES) + ")",
        "7 Criteria whose values carry a quantified uncertainty": share(sum(map(with_sigma, criteria)), n),
        "8 Hard requirements (criteria that cannot be averaged away)": str(sum(bool(c.get("required")) for c in criteria)),
        "11 Criteria stating their role, basis and rationale in the API": share(sum(map(documented, criteria)), n),
    }


def to_markdown() -> str:
    v1, v2 = indicators("v1"), indicators("v2")
    lines = ["| Indicator (number = grid criterion) | Methodology v1 | Methodology v2 |", "|---|---|---|"]
    lines += [f"| {k} | {v1[k]} | {v2[k]} |" for k in v1]
    return "\n".join(lines) + "\n"


# ---- v3 (T49): counted from the run summaries and catalogues in the repository ----
ROOT = os.path.join(HERE, "..", "..")
V3_RUNS = ("run-002", "run-mars-001")                       # the runs served by the current releases


def _json(*parts):
    with open(os.path.join(ROOT, *parts), encoding="utf-8") as fh:
        return json.load(fh)


def _release_sources() -> set:
    out = set()
    base = os.path.join(DATA, "releases-fixture")
    for d in sorted(os.listdir(base)):
        f = os.path.join(base, d, "method.json")
        if os.path.exists(f):
            out |= {s["id"] for s in _json("data", "releases-fixture", d, "method.json")["sources"]}
    return out


def v3_indicators() -> dict:
    import collections
    out: dict = {"runs": list(V3_RUNS), "masks": {}, "negatives_top10": {}, "self_consistency": {}, "monte_carlo": {},
                 "reproducibility": {}, "dossiers": {}, "cells": {}}
    scenarios_with_positives = 0
    for run in V3_RUNS:
        v = _json("data", "runs", run, "validation.json")
        m = v["negatives"]["masks"]
        out["masks"][run] = f"{m['masked_or_flagged']}/{m['of']}"
        top = v["negatives"]["top10"]
        out["negatives_top10"][run] = f"{sum(x['pass'] for x in top.values())}/{len(top)} targets"
        sc = v["self_consistency"]
        bad = sorted((t, x["ks"]) for t, x in sc.items() if not x.get("pass"))
        out["self_consistency"][run] = f"{len(sc) - len(bad)}/{len(sc)} targets" + (
            " (fails: " + ", ".join(f"{t} {k:.3f}" for t, k in bad) + ")" if bad else "")
        out["monte_carlo"][run] = {t: f"{x['stable_zones_90pct']}/{x['zones']}" for t, x in v["monte_carlo"].items()}
        rp = v["reproducibility"]["tiles"]
        out["reproducibility"][run] = f"{sum(t['identical_sha256'] for t in rp)}/{len(rp)} tiles"
        pos = v["positives"]
        for k, val in pos.items():
            if k in ("consequence",):
                continue
            scenarios_with_positives += isinstance(val, dict) and val.get("pass") is True
        out["dossiers"][run] = dict(collections.Counter(o["outcome"] for o in _json("docs", "wiki", "runs", run, "outcomes.json")))
        out["cells"][run] = _json("data", "runs", run, "assess.json")["cells"]
    n_scen = len([f for f in os.listdir(os.path.join(DATA, "scenarios")) if f.endswith(".yaml")])   # C has no run yet
    out["positive_validation"] = f"{scenarios_with_positives} of {n_scen} scenarios"
    checks = _json("data", "runs", "run-002", "checks.json")
    out["nasadem"] = {sc: checks[sc]["nasadem"] for sc in ("A", "B")}
    out["resolution_30m"] = {sc: checks[sc]["resolution_30m"] for sc in ("A", "B")}
    cov = _json("data", "runs", "run-002", "coverage-summary.json")
    out["hidden_share"] = {"run-002": cov["half_or_more_masked"]}
    geo = _json("data", "runs", "run-002", "geology-report.json")
    out["geology_top_zones"] = {k: geo[k] for k in ("dossiers_A", "dossiers_B")}
    import yaml
    cat = {}
    for name in ("earth", "moon", "mars"):
        with open(os.path.join(DATA, "catalog", f"{name}.yaml"), encoding="utf-8") as fh:
            cat.update({p["id"]: p for p in (yaml.safe_load(fh) or {}).get("products", [])})
    used = _release_sources()
    out["sources"] = {"used": len(used), "verified": sum(cat.get(i, {}).get("status") == "verified" for i in used),
                      "with_refresh": sum("refresh" in cat.get(i, {}) for i in used),
                      "watched": sum(bool((cat.get(i, {}).get("refresh") or {}).get("watch")) for i in used)}
    return out


def v3_markdown() -> str:
    v = v3_indicators()
    rows = [
        ("Cells assessed (5 km, equal-area)", {r: f"{n:,}" for r, n in v["cells"].items()}),
        ("Negatives in the top 10% (pass: at most 1 of 18)", v["negatives_top10"]),
        ("Masks check (pass: 18/18)", v["masks"]),
        ("Self-consistency (KS <= 0.05)", v["self_consistency"]),
        ("Reproducibility (identical SHA-256)", v["reproducibility"]),
        ("Monte Carlo: zones stable in 90% of runs", {r: ", ".join(f"{t} {x}" for t, x in m.items()) for r, m in v["monte_carlo"].items()}),
        ("Dossiers of the top zones", {r: ", ".join(f"{k} {n}" for k, n in sorted(d.items())) for r, d in v["dossiers"].items()}),
    ]
    lines = ["| Indicator | " + " | ".join(v["runs"]) + " |", "|---|" + "---|" * len(v["runs"])]
    for name, by in rows:
        lines.append(f"| {name} | " + " | ".join(str(by.get(r, "—")) for r in v["runs"]) + " |")
    n = v["nasadem"]
    lines.append("| NASADEM instead of Copernicus, top 20 kept (A, B) | " +
                 f"{n['A']['top_overlap']:.0%}, {n['B']['top_overlap']:.0%} | — |")
    r30 = v["resolution_30m"]
    lines.append("| 30 m instead of the planetary pixel, top 20 kept (A, B) | " +
                 f"{r30['A']['top_overlap']:.0%}, {r30['B']['top_overlap']:.0%} | — |")
    s = v["sources"]
    lines.append(f"| Sources of the releases: verified, with a refresh block, watched | {s['verified']}/{s['used']}, "
                 f"{s['with_refresh']}/{s['used']}, {s['watched']}/{s['used']} | (same) |")
    lines.append(f"| Scenarios with a positive validation (3 or more verified controls that pass) | {v['positive_validation']} | |")
    return chr(10).join(lines) + chr(10)


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    print(v3_markdown() if "--v3" in sys.argv else to_markdown())
