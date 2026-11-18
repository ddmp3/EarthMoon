"""Scientific evaluation grid: the automatable indicators, computed the same way for methodology v1 and v2.

The grid itself (criteria, methods, reference levels, targets) is defined in docs/SCIENTIFIC_VALIDATION.md.
This script computes every indicator that can be counted from the repository, so that the before / after
comparison does not depend on anyone's opinion. Indicators that need a human judgement are listed in the
document and are not computed here.

    python tools/validation/science_grid.py        # prints the Markdown table

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

# Indicators the audit found scientifically invalid for their use (docs/SCIENTIFIC_AUDIT.md, findings).
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
# v1: where each interval came from (docs/scenarios.md of v1).
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


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    print(to_markdown())
