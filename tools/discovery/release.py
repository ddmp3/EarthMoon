"""Static release of a run for API v3 (T44, ADR-003, ADR-004).

A release is a folder of JSON files written once from a validated run. The API serves them as they are and never
computes a number itself:

    <out>/index.json                                   current release and the last 3 (ADR-009)
    <out>/<release>/release.json                       id, run, protocol, commit, data versions, processing chain
    <out>/<release>/profiles.json, scenarios.json, method.json, coverage.json
    <out>/<release>/zones/<scenario>/<target>/t<tau>-m<min>.json    zones of one grid value, ranked

    PYTHONPATH=tools python tools/discovery/release.py --run /data/run002 --out /data/releases

Every number keeps its spread and its source; a value that was not computed is null with a reason, never zero.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

ROOT = Path(__file__).resolve().parents[2]
PROTOCOL = "validation-protocol-v3"
METHODOLOGY_VERSION = "v3"
SCENARIO_FILES = {"A": "A-lunar-base.yaml", "B": "B-lunar-robotics.yaml"}
EARTH_SOURCES = ["copernicus-dem-glo30", "copernicus-dem-glo90", "esa-worldcover", "add-rock-outcrop-v7-3",
                 "natural-earth-admin0-110m"]
# Overlay classes of the map (docs/wiki/ui/map-spec.md), in the order they are tested: a cell gets the first that applies.
COVERAGE_CLASSES = ["screened_out", "no_data", "ground_hidden", "partial", "low_confidence", "evaluated"]
COVERAGE_TEXT = {
    "screened_out": "not refined at the lunar pixel: no 90 m window near this target (T22 rule)",
    "no_data": "no valid elevation, or land cover unknown for half the windows (outside WorldCover)",
    "ground_hidden": "half the windows or more hidden by forest, crops, buildings, water, wetland, mangroves, snow or ice",
    "partial": "fewer than half the windows of the cell are valid for this target",
    "low_confidence": "not high confidence: under 20 valid windows, or 10% or more masked or of unknown cover",
    "evaluated": "high confidence: at least 20 valid windows and under 10% masked or of unknown cover",
}


def _f(a) -> np.ndarray:
    a = np.asarray(a)
    if a.dtype.kind == "f":
        return a
    return np.array([np.nan if v is None else v for v in a], dtype=float)


def coverage_class(cells: dict, target: str) -> np.ndarray:
    """Overlay class of each cell for one target."""
    n = len(cells["cell"])
    screened = np.asarray(cells.get(f"{target}:screened_out", [None] * n), dtype=object) == True  # noqa: E712
    tw, tv = _f(cells.get(f"{target}:windows", [None] * n)), _f(cells.get(f"{target}:valid", [None] * n))
    windows = _f(cells["windows"])
    unknown = _f(cells["cover_unknown"])
    masked = np.nan_to_num(_f(cells["masked_share"]), nan=0.0)
    no_data = (np.nan_to_num(tv) == 0) & (masked < 0.5) | (unknown >= 0.5 * windows)
    hidden = masked >= 0.5
    partial = np.nan_to_num(tv) < 0.5 * np.nan_to_num(tw)
    low = np.asarray(cells["confidence"], dtype=object) != "high"
    out = np.full(n, "evaluated", dtype=object)
    for name, m in zip(COVERAGE_CLASSES[::-1][1:], (low, partial, hidden, no_data, screened)):
        out[m] = name                                             # last assignment wins: first class in the order
    return out


def coverage_shares(cells: dict, target: str, land_km2: float) -> dict:
    """Land area per overlay class. One 1 km window on a 1 km grid is about 1 km² of land; the land outside every
    assessed cell was screened out."""
    cls = coverage_class(cells, target)
    area = np.nan_to_num(_f(cells["windows"]))
    km2 = {c: float(area[cls == c].sum()) for c in COVERAGE_CLASSES}
    km2["screened_out"] += max(0.0, land_km2 - float(area.sum()))
    total = sum(km2.values())
    return {"land_km2": round(land_km2, 1),
            "classes": {c: {"km2": round(km2[c], 1), "share": round(km2[c] / total, 4) if total else None,
                            "meaning": COVERAGE_TEXT[c]} for c in COVERAGE_CLASSES}}


def zone_id(scenario: str, target: str, tau: float, min_cells: int, rank: int) -> str:
    return f"{scenario}.{target}.t{tau}.m{min_cells}.{rank}"


def _rows(ids: list, cells: dict) -> np.ndarray:
    table = np.asarray(cells["cell"]).astype(np.int64)
    order = np.argsort(table)
    a = np.asarray(ids).astype(np.int64)
    k = np.clip(np.searchsorted(table[order], a), 0, table.size - 1)
    return order[k][table[order][k] == a]


def zone_record(z: dict, rank: int, tau: float, min_cells: int, cells: dict) -> dict:
    """A zone as the API serves it: values with their spread, requirements, coverage of its cells, Monte Carlo."""
    r = _rows(z["cell_ids"], cells)
    conf = np.asarray(cells["confidence"], dtype=object)[r]
    return {
        "id": zone_id(z["scenario"], z["target"], tau, min_cells, rank), "rank": rank,
        "scenario": z["scenario"], "target": z["target"], "lat": z["lat"], "lon": z["lon"],
        "cells": z["cells"], "area_km2": z["area_km2"],
        "typicality": {"median": z["median"], "p25": z["cell_median_p25"], "p75": z["cell_median_p75"]},
        "high_confidence_share": z["high_confidence_share"],
        "requirements": {k[4:]: v for k, v in z.items() if k.startswith("req:")},
        "suitability_median": z.get("suitability_median"),
        "coverage": {"windows": int(np.nansum(_f(cells["windows"])[r])),
                     "valid_unmasked": int(np.nansum(_f(cells["valid_unmasked"])[r])),
                     "cover_unknown": int(np.nansum(_f(cells["cover_unknown"])[r])),
                     "cells_by_confidence": {c: int(np.sum(conf == c)) for c in ("high", "medium", "low")}},
        "monte_carlo": {"top_decile_share": z["mc_top_decile_share"]} if "mc_top_decile_share" in z else None,
        "tiles": z.get("tiles", []),
    }


def release_id(content: dict) -> str:
    """r- and 8 hex characters of the SHA-256 of the release content (sorted keys): same content, same id."""
    return "r-" + hashlib.sha256(json.dumps(content, sort_keys=True, default=str).encode()).hexdigest()[:8]


def _catalogue() -> dict:
    import yaml
    out = {}
    for f in sorted((ROOT / "data/catalog").glob("*.yaml")):
        for p in yaml.safe_load(f.read_text(encoding="utf-8"))["products"]:
            out[p["id"]] = p
    return out


def method(source_ids: list[str], steps: list[dict]) -> dict:
    """Data and method panel: each source from the catalogues with its status, and the processing chain."""
    cat = _catalogue()
    keep = ("id", "body", "product", "producer", "url", "coverage", "resolution_spatial", "resolution_effective",
            "uncertainty", "limitations", "status", "verified_on", "verified_url", "attribution")
    sources = []
    for sid in source_ids:
        p = cat.get(sid)
        if p is None:
            sources.append({"id": sid, "status": "not in catalogue"})
        else:
            sources.append({k: p.get(k) for k in keep} | {"licence": (p.get("access") or {}).get("licence")})
    return {"sources": sources, "processing": steps}


def scenarios() -> list[dict]:
    import yaml
    from discovery.compare_run import RULES, SUITABILITY
    from discovery.discover import ELIMINATING, SCENARIO_TARGETS
    out = []
    for sid, f in SCENARIO_FILES.items():
        y = yaml.safe_load((ROOT / "data/scenarios" / f).read_text(encoding="utf-8"))
        reqs = [{**r, "eliminating": r["id"] in ELIMINATING[sid],
                 "rule": {k: v for k, v in RULES[r["id"]].items() if k != "why"} if r["id"] in RULES else None}
                for r in y.get("requirements", [])]
        out.append({"id": sid, "name": y["name"], "objective": y["objective"], "targets": y["targets"],
                    "assessed_targets": SCENARIO_TARGETS[sid],
                    "not_comparable": {t: "no Earth cube at this target's pixel scale (for example 5 m)"
                                       for t in y["targets"] if t not in SCENARIO_TARGETS[sid]},
                    "similarity": y.get("similarity", []), "context": y.get("context", []), "requirements": reqs,
                    "suitability": {k: v for k, v in SUITABILITY[sid].items()}, "cannot_assess": y.get("cannot_assess", [])})
    return out


def profiles() -> list[dict]:
    out = []
    for f in sorted((ROOT / "data/profiles/moon").glob("moon-*.json")):
        p = json.loads(f.read_text(encoding="utf-8"))
        out.append({k: p.get(k) for k in ("id", "body", "spec", "inputs", "params", "windows", "metrics", "not_computed")})
    return out


def processing_steps(run: Path) -> list[dict]:
    """The processing chain, from the code constants and the run files (not typed by hand)."""
    from discovery.compare import MASK_CLASSES
    from discovery.compare_run import RULES
    from discovery.discover import MIN, SCALES, TARGET_SCALE, TAU
    from discovery.healpix import NSIDE, cell_area_km2
    screen = json.loads((run / "screen.json").read_text()) if (run / "screen.json").exists() else {}
    assess = json.loads((run / "assess.json").read_text()) if (run / "assess.json").exists() else {}
    return [
        {"step": "screening", "what": "90 m windows (Copernicus GLO-90) select the 1° tiles refined per target",
         "rule": screen.get("rule"), "intervals": screen.get("intervals")},
        {"step": "windows", "what": "1 km windows at the lunar pixel of each target (Copernicus GLO-30)",
         "pixel_m": SCALES, "target_scale": TARGET_SCALE},
        {"step": "masks", "what": "windows whose ground is hidden are excluded (WorldCover 2021; rock outcrops south of 60°S)",
         "classes": list(MASK_CLASSES)},
        {"step": "typicality", "what": "two-sided percentile of each window's mean slope among the lunar windows"},
        {"step": "cells", "what": f"HEALPix cells (NSIDE {NSIDE}, {cell_area_km2():.2f} km²), one global equal-area grid",
         "assessed_tiles": assess.get("assessed_tiles"), "cells": assess.get("cells")},
        {"step": "requirements", "rules": {k: v["why"] for k, v in RULES.items()}},
        {"step": "zones", "what": "connected high-confidence candidate cells (HEALPix neighbours)", "tau": TAU, "min_cells": MIN},
        {"step": "validation", "protocol": PROTOCOL},
    ]


def land_km2(cube: Path) -> float:
    """Land area as the number of 1 km windows of the global 90 m cube (row counts from the Parquet footers)."""
    import pyarrow.parquet as pq
    return float(sum(pq.ParquetFile(f).metadata.num_rows for f in sorted((cube / "glo90-90m").glob("*.windows.parquet"))))


def _tile_land(f: str) -> np.ndarray:
    import pyarrow.parquet as pq
    from discovery.discover import global_cell
    t = pq.read_table(f, columns=["lat", "lon"])
    return np.unique(global_cell(t.column("lat").to_numpy(), t.column("lon").to_numpy()))


def land_cells(cube: Path, workers: int = 12) -> np.ndarray:
    """Sorted ids of the global cells holding at least one window of the global 90 m cube: the land the map
    can speak about (sea and DEM voids hold no window)."""
    from concurrent.futures import ProcessPoolExecutor
    files = [str(f) for f in sorted((cube / "glo90-90m").glob("*.windows.parquet"))]
    if workers <= 1:
        parts = [_tile_land(f) for f in files]
    else:
        with ProcessPoolExecutor(max_workers=workers) as pool:
            parts = list(pool.map(_tile_land, files, chunksize=64))
    return np.unique(np.concatenate(parts)) if parts else np.zeros(0, np.int64)


def export(run: Path, cube: Path, out: Path, commit: str) -> str:
    from discovery.discover import MIN, MIN_CELLS, SCENARIO_TARGETS, TAU, TAUS, load_cells, zones_for
    cols = ["cell", "windows", "valid_unmasked", "masked_share", "cover_unknown", "confidence", "lat", "lon", "area_km2",
            "tile", "suitability_A", "suitability_B", "req:base_slope", "req:climbing_limit_lrv", "req:climbing_limit_viper"]
    targets = sorted({t for ts in SCENARIO_TARGETS.values() for t in ts})
    for t in targets:
        cols += [f"{t}:{k}" for k in ("windows", "valid", "screened_out", "median")]
    cells = load_cells(str(run / "cells.parquet"), cols)
    land = land_km2(cube)
    validation = json.loads((run / "validation.json").read_text()) if (run / "validation.json").exists() else {}
    profs = profiles()
    used = list(EARTH_SOURCES)
    for p in profs:
        if p["id"] in targets:
            used += [k.split("/")[0] for k in (p.get("inputs") or {}) if k.split("/")[0] not in used]
    content = {"run": run.name, "methodology_version": METHODOLOGY_VERSION, "protocol": PROTOCOL, "commit": commit,
               "processing": processing_steps(run), "validation": validation, "land_km2": land}
    rid = release_id(content)
    d = out / rid
    (d / "zones").mkdir(parents=True, exist_ok=True)

    def write(path: Path, obj) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(obj, separators=(",", ":"), default=str) + "\n", encoding="utf-8")

    from datetime import date
    head = {"release": rid, "methodology_version": METHODOLOGY_VERSION}
    write(d / "release.json", {**head, **content, "created": date.today().isoformat(),
                               "grid": {"tau": list(TAUS), "min_cells": list(MIN_CELLS), "nominal": {"tau": TAU, "min_cells": MIN}}})
    write(d / "profiles.json", {**head, "profiles": profs})
    write(d / "scenarios.json", {**head, "scenarios": scenarios()})
    write(d / "method.json", {**head, **method(used, processing_steps(run))})
    write(d / "coverage.json", {**head, "scenarios": {sc: {t: coverage_shares(cells, t, land) for t in ts}
                                                       for sc, ts in SCENARIO_TARGETS.items()}})
    for sc, ts in SCENARIO_TARGETS.items():
        for t in ts:
            for tau in TAUS:
                for mc in MIN_CELLS:
                    if tau == TAU and mc == MIN and (run / f"zones-{sc}-{t}.json").exists():
                        zs = json.loads((run / f"zones-{sc}-{t}.json").read_text())     # nominal: carries the Monte Carlo
                    else:
                        zs = zones_for(cells, sc, t, tau, mc)
                    write(d / "zones" / sc / t / f"t{tau}-m{mc}.json",
                          {**head, "scenario": sc, "target": t, "tau": tau, "min_cells": mc,
                           "zones": [zone_record(z, k + 1, tau, mc, cells) for k, z in enumerate(zs)]})
    idx_path = out / "index.json"
    idx = json.loads(idx_path.read_text()) if idx_path.exists() else {"releases": []}
    entry = {"id": rid, "run": run.name, "methodology_version": METHODOLOGY_VERSION, "protocol": PROTOCOL,
             "commit": commit, "created": date.today().isoformat()}
    idx["releases"] = [entry] + [r for r in idx["releases"] if r["id"] != rid][:3]
    idx["current"] = rid
    write(idx_path, idx)
    return rid


def main(argv=None) -> int:
    import os
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--run", type=Path, required=True)
    ap.add_argument("--cube", type=Path, default=Path("/data/cube"))
    ap.add_argument("--out", type=Path, required=True)
    a = ap.parse_args(argv)
    land = a.run / "land-cells.npy"
    if not land.exists():
        np.save(land, land_cells(a.cube))
    print(export(a.run, a.cube, a.out, os.environ.get("EARTHMOON_COMMIT", "unknown")))
    return 0


if __name__ == "__main__":
    sys.exit(main())
