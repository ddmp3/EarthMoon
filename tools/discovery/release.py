"""Static release of a run for API v3 (T44, ADR-003, ADR-004).

A release is a folder of JSON files written once from a validated run. The API serves them as they are and never
computes a number itself:

    <out>/index.json                                   current release and the last 3 (ADR-009)
    <out>/<release>/release.json                       id, run, protocol, commit, data versions, processing chain
    <out>/<release>/profiles.json, scenarios.json, method.json, coverage.json, status.json
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
# Body-specific settings; the Mars release replaces them (discovery.mars_run.configure_release)
BODY = "moon"
PROFILE_DIR, PROFILE_GLOB = "data/profiles/moon", "moon-*.json"
INPUT_SOURCES: dict = {}            # profile input prefix -> catalogue id, for bodies without a cube of their own
NOT_COMPARABLE_TEXT = "no Earth cube at this target's pixel scale (for example 5 m)"
SCREENING = True                    # the lunar runs screen tiles at 90 m first
COVERAGE_AREA = "windows"           # windows: one 1 km window is 1 km2 of land; cells: the cell area (Mars windows overlap cells)
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
    area = np.nan_to_num(_f(cells["windows"] if COVERAGE_AREA == "windows" else cells["area_km2"]))
    km2 = {c: float(area[cls == c].sum()) for c in COVERAGE_CLASSES}
    km2["screened_out"] += max(0.0, land_km2 - float(area.sum()))
    total = sum(km2.values())
    return {"land_km2": round(land_km2, 1),
            "classes": {c: {"km2": round(km2[c], 1), "share": round(km2[c] / total, 4) if total else None,
                            "meaning": COVERAGE_TEXT[c]} for c in COVERAGE_CLASSES}}


def zone_id(scenario: str, target: str, tau: float, min_cells: int, rank: int) -> str:
    return f"{scenario}.{target}.t{tau}.m{min_cells}.{rank}"


def cell_index(cells: dict) -> dict:
    """Arrays a zone record reads, prepared once per release: sorting 6 M cell ids for every zone took hours."""
    table = np.asarray(cells["cell"]).astype(np.int64)
    order = np.argsort(table)
    out = {"sorted": table[order], "order": order, "windows": _f(cells["windows"]),
           "valid_unmasked": _f(cells["valid_unmasked"]), "cover_unknown": _f(cells["cover_unknown"]),
           "confidence": np.asarray(cells["confidence"], dtype=object)}
    geo = {k: _f(v) for k, v in cells.items() if k.startswith("geo:") and k.count(":") == 2}
    if geo:
        out["geo"] = geo
    if "ctx:frozen_e4" in cells:
        out["ctx"] = {"frozen_e4": np.asarray(cells["ctx:frozen_e4"], dtype=object), "magt_c": _f(cells["ctx:magt_c"]),
                      "aridity_class": np.asarray(cells["ctx:aridity_class"], dtype=object)}
    return out


FROZEN_STATES = ("met", "partial", "failed", "not covered")
ARIDITY_NAMES = ("hyper-arid", "arid", "semi-arid", "dry sub-humid", "humid", "no data")


def zone_context(ix: dict, rows: np.ndarray) -> dict | None:
    """Earth context of a zone (T47, E18): share of its cells per frozen-ground state and aridity class. A model,
    never a similarity with the Moon."""
    ctx = ix.get("ctx")
    if not ctx or rows.size == 0:
        return None
    fz, ac, m = ctx["frozen_e4"][rows], ctx["aridity_class"][rows], ctx["magt_c"][rows]
    share = lambda a, k: round(float(np.mean(a == k)), 4)  # noqa: E731
    return {"class": "model", "comparable_with_moon": False,
            "frozen_e4": {k: share(fz, k) for k in FROZEN_STATES},
            "magt_c_median": round(float(np.nanmedian(m)), 2) if np.isfinite(m).any() else None,
            "aridity": {k: share(ac, k) for k in ARIDITY_NAMES},
            "sources": ["obu-permafrost-2018", "global-aridity-index-v3"]}


GEO_STATES = ("match", "partial", "no_match", "unresolved", "no_map")
GEO_SOURCE = "Macrostrat carto tiles, zoom 8 (CC-BY 4.0); crosswalk E17"


def zone_geology(ix: dict, rows: np.ndarray, target: str) -> dict | None:
    """Mean share of each geology state over the 9 samples of every cell of a zone, for the target's group (T46)."""
    from discovery.geology import TARGET_GROUP
    geo, g = ix.get("geo"), TARGET_GROUP.get(target)
    if not geo or g is None or f"geo:{g}:match" not in geo or rows.size == 0:
        return None
    return {"group": g, "source": GEO_SOURCE,
            **{st: round(float(np.nanmean(geo[f"geo:{g}:{st}"][rows])), 4) for st in GEO_STATES}}


def _rows(ids: list, index: dict) -> np.ndarray:
    srt, order = index["sorted"], index["order"]
    a = np.asarray(ids).astype(np.int64)
    k = np.clip(np.searchsorted(srt, a), 0, srt.size - 1)
    return order[k][srt[k] == a]


def zone_record(z: dict, rank: int, tau: float, min_cells: int, cells: dict, index: dict | None = None) -> dict:
    """A zone as the API serves it: values with their spread, requirements, coverage of its cells, Monte Carlo."""
    ix = index if index is not None else cell_index(cells)
    r = _rows(z["cell_ids"], ix)
    conf = ix["confidence"][r]
    return {
        "id": zone_id(z["scenario"], z["target"], tau, min_cells, rank), "rank": rank,
        "scenario": z["scenario"], "target": z["target"], "lat": z["lat"], "lon": z["lon"],
        "cells": z["cells"], "area_km2": z["area_km2"],
        "typicality": {"median": z["median"], "p25": z["cell_median_p25"], "p75": z["cell_median_p75"]},
        "high_confidence_share": z["high_confidence_share"],
        "requirements": {k[4:]: v for k, v in z.items() if k.startswith("req:")},
        "suitability_median": z.get("suitability_median"),
        "coverage": {"windows": int(np.nansum(ix["windows"][r])),
                     "valid_unmasked": int(np.nansum(ix["valid_unmasked"][r])),
                     "cover_unknown": int(np.nansum(ix["cover_unknown"][r])),
                     "cells_by_confidence": {c: int(np.sum(conf == c)) for c in ("high", "medium", "low")}},
        "monte_carlo": {"top_decile_share": z["mc_top_decile_share"]} if "mc_top_decile_share" in z else None,
        "geology": zone_geology(ix, r, z["target"]),
        "context": zone_context(ix, r),
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


def status(validation: dict, sources: list[dict], release: str, created: str) -> dict:
    """GET /api/v3/status (ADR-009): validity of the release and freshness of its sources.

    Validated only when every check of the protocol passes; a check that cannot run (no positive control) counts as
    not passed. Until the refresher exists (T52), no source is checked automatically: each one is `not_checkable`,
    with the date it was verified by hand in the catalogue."""
    neg = validation.get("negatives") or {}
    top10 = neg.get("top10") or {}
    selfc = validation.get("self_consistency") or {}
    pos = validation.get("positives") or {}
    failing = sorted(t for t, x in selfc.items() if not x.get("pass"))
    checks = [
        {"check": "positives", "pass": pos.get("pass"), "detail": pos.get("consequence") or ""},
        {"check": "negatives_top10", "pass": bool(top10) and all(x.get("pass") for x in top10.values()) if top10 else None,
         "detail": "at most 1 of 18 negatives in the top 10% of each target"},
        {"check": "masks", "pass": (neg.get("masks") or {}).get("pass"),
         "detail": f"{(neg.get('masks') or {}).get('masked_or_flagged', '?')} of {(neg.get('masks') or {}).get('of', '?')} negatives masked or flagged"},
        {"check": "self_consistency", "pass": (not failing) if selfc else None,
         "detail": ("fails for " + ", ".join(failing)) if failing else "KS <= 0.05 for every target"},
        {"check": "reproducibility", "pass": (validation.get("reproducibility") or {}).get("pass"),
         "detail": "identical SHA-256 on rebuild"},
    ]
    ok = all(c["pass"] is True for c in checks)
    return {"validity": {"state": "validated" if ok else "not_validated", "protocol": PROTOCOL, "release": release,
                         "published": created, "checks": checks},
            "freshness": {"refresher": False,
                          "note": "no automatic check yet (refresher planned in T52): sources were verified by hand",
                          "sources": [{"id": s["id"], "state": "not_checkable", "checked_on": s.get("verified_on")}
                                      for s in sources]}}


# Files of the lunar cube (T41, docs/wiki/runs/moon-profiles.md) by name prefix, and the catalogue entry they come from.
MOON_CUBE_FILES = (("SLDEM2015_", "sldem2015"), ("GeoUnits.", "usgs-unified-geologic-map"), ("ironhd", "lp-grs-ns-special-products"))


def profile_sources(profs: list[dict], targets: list[str]) -> list[str]:
    """Catalogue ids of the lunar sources behind the assessed targets, each once, in order of first use. The lunar cube
    is not a catalogue entry: it is replaced by the sources of its input files (SLDEM2015 when none are listed)."""
    out: list[str] = []

    def add(sid: str) -> None:
        if sid not in out:
            out.append(sid)

    for p in profs:
        if p["id"] not in targets:
            continue
        inputs = p.get("inputs") or {}
        for key, val in inputs.items():
            sid = key.split("/")[0]
            if sid in INPUT_SOURCES:
                add(INPUT_SOURCES[sid])
            elif sid != "moon-cube":
                add(sid)
            elif key == "moon-cube/inputs" and isinstance(val, dict):
                for name in val:
                    for prefix, cat in MOON_CUBE_FILES:
                        if name.startswith(prefix):
                            add(cat)
            elif "moon-cube/inputs" not in inputs:
                add("sldem2015")
    return out


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
                    "not_comparable": {t: NOT_COMPARABLE_TEXT for t in y["targets"] if t not in SCENARIO_TARGETS[sid]},
                    "similarity": y.get("similarity", []), "context": y.get("context", []), "requirements": reqs,
                    "suitability": {k: v for k, v in SUITABILITY.get(sid, {}).items()},
                    "cannot_assess": y.get("cannot_assess", [])})
    return out


def profiles() -> list[dict]:
    out = []
    for f in sorted((ROOT / PROFILE_DIR).glob(PROFILE_GLOB)):
        p = json.loads(f.read_text(encoding="utf-8"))
        out.append({k: p.get(k) for k in ("id", "body", "spec", "inputs", "params", "windows", "metrics", "not_computed")})
    return out


def processing_steps(run: Path) -> list[dict]:
    """The processing chain, from the code constants and the run files (not typed by hand)."""
    from discovery.compare import MASK_CLASSES
    from discovery.compare_run import RULES
    from discovery.discover import MIN, RULES_IN_USE, SCALES, TARGET_SCALE, TAU
    from discovery.healpix import NSIDE, cell_area_km2
    screen = json.loads((run / "screen.json").read_text()) if (run / "screen.json").exists() else {}
    assess = json.loads((run / "assess.json").read_text()) if (run / "assess.json").exists() else {}
    rules = RULES if RULES_IN_USE is None else RULES_IN_USE
    first = ([{"step": "screening", "what": "90 m windows (Copernicus GLO-90) select the 1° tiles refined per target",
               "rule": screen.get("rule"), "intervals": screen.get("intervals")},
              {"step": "windows", "what": "1 km windows at the lunar pixel of each target (Copernicus GLO-30)",
               "pixel_m": SCALES, "target_scale": TARGET_SCALE}] if SCREENING else
             [{"step": "windows", "what": "windows of 25 x 25 pixels at the MOLA pixel of each target, on every Earth tile "
                                          "(Copernicus GLO-90 resampled; decision E19)",
               "pixel_m": SCALES, "target_scale": TARGET_SCALE}])
    return [
        *first,
        {"step": "masks", "what": "windows whose ground is hidden are excluded (WorldCover 2021; rock outcrops south of 60°S)",
         "classes": list(MASK_CLASSES)},
        {"step": "typicality", "what": f"two-sided percentile of each window's mean slope among the {'lunar' if BODY == 'moon' else 'Martian'} windows"},
        {"step": "cells", "what": f"HEALPix cells (NSIDE {NSIDE}, {cell_area_km2():.2f} km²), one global equal-area grid",
         "assessed_tiles": assess.get("assessed_tiles"), "cells": assess.get("cells")},
        {"step": "requirements", "rules": {k: v["why"] for k, v in rules.items()}},
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


def _context(run: Path, cells: dict) -> dict:
    """Context columns of the run (context.parquet of tools/discovery/context.py), in the order of `cells`."""
    import pyarrow.parquet as pq
    f = run / "context.parquet"
    if not f.exists():
        return {}
    t = pq.read_table(f)
    ids = np.asarray(t.column("cell").to_numpy(zero_copy_only=False)).astype(np.int64)
    order = np.argsort(ids)
    want = np.asarray(cells["cell"]).astype(np.int64)
    k = np.clip(np.searchsorted(ids[order], want), 0, ids.size - 1)
    found = ids[order][k] == want
    out = {}
    for name in t.column_names:
        if not name.startswith("ctx:"):
            continue
        col = t.column(name).to_numpy(zero_copy_only=False)[order]
        if col.dtype.kind == "f":
            v = np.full(want.size, np.nan, np.float32)
        else:
            v = np.full(want.size, "no data" if "aridity" in name else "not covered", dtype=object)
        v[found] = col[k[found]]
        out[name] = v
    return out


def _geology(run: Path, cells: dict) -> dict:
    """Geology columns of the run (geology.parquet of tools/discovery/geology.py), in the order of `cells`; empty if
    the run has no geology assessment."""
    import pyarrow.parquet as pq
    f = run / "geology.parquet"
    if not f.exists():
        return {}
    t = pq.read_table(f)
    ids = np.asarray(t.column("cell").to_numpy(zero_copy_only=False)).astype(np.int64)
    order = np.argsort(ids)
    want = np.asarray(cells["cell"]).astype(np.int64)
    k = np.clip(np.searchsorted(ids[order], want), 0, ids.size - 1)
    found = ids[order][k] == want
    out = {}
    for name in t.column_names:
        if name.startswith("geo:") and name.count(":") == 2:
            v = np.full(want.size, np.nan, np.float32)
            v[found] = t.column(name).to_numpy(zero_copy_only=False)[order][k[found]]
            out[name] = v
    return out


def export(run: Path, cube: Path, out: Path, commit: str) -> str:
    from discovery.discover import MIN, MIN_CELLS, SCENARIO_TARGETS, TAU, TAUS, load_cells, zones_for
    cols = ["cell", "windows", "valid_unmasked", "masked_share", "cover_unknown", "confidence", "lat", "lon", "area_km2",
            "tile", "suitability_A", "suitability_B", "req:base_slope", "req:climbing_limit_lrv", "req:climbing_limit_viper"]
    targets = sorted({t for ts in SCENARIO_TARGETS.values() for t in ts})
    for t in targets:
        cols += [f"{t}:{k}" for k in ("windows", "valid", "screened_out", "median", "p25", "p75")]
    cells = load_cells(str(run / "cells.parquet"), cols)
    geo_table = _geology(run, cells)                              # T46: geology of each cell, when assessed
    cells.update(geo_table)
    ctx_table = _context(run, cells)                              # T47: Earth context of each cell, when assessed
    cells.update(ctx_table)
    land = land_km2(cube)
    validation = json.loads((run / "validation.json").read_text()) if (run / "validation.json").exists() else {}
    profs = profiles()
    used = list(EARTH_SOURCES) + profile_sources(profs, targets)
    if geo_table:
        used.append("macrostrat")
    if ctx_table:
        used += ["obu-permafrost-2018", "global-aridity-index-v3"]
    context_summary = ({k: v for k, v in json.loads((run / "context.json").read_text()).items() if k != "layers"}
                       if ctx_table and (run / "context.json").exists() else None)
    geology_summary = json.loads((run / "geology.json").read_text()) if geo_table and (run / "geology.json").exists() else None
    content = {"run": run.name, "methodology_version": METHODOLOGY_VERSION, "protocol": PROTOCOL, "commit": commit,
               "processing": processing_steps(run), "validation": validation, "land_km2": land, "geology": geology_summary,
               "context": context_summary}
    rid = release_id(content)
    d = out / rid
    (d / "zones").mkdir(parents=True, exist_ok=True)

    def write(path: Path, obj) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(obj, separators=(",", ":"), default=str) + "\n", encoding="utf-8")

    from datetime import date
    head = {"release": rid, "methodology_version": METHODOLOGY_VERSION}
    import pyarrow.parquet as pq                                  # the cells the discovery service reads (ADR-005)
    import pyarrow as pa
    table = pq.read_table(run / "cells.parquet", columns=[c for c in cols if c not in ("lat", "lon", "area_km2", "tile")])
    for k, v in geo_table.items():
        table = table.append_column(k, pa.array(np.asarray(v, np.float32)))
    for k, v in ctx_table.items():
        arr = np.asarray(v)
        table = table.append_column(k, pa.array(arr.astype(np.float32) if arr.dtype.kind == "f" else arr.tolist()))
    pq.write_table(table, d / "cells.parquet", compression="zstd")
    write(d / "release.json", {**head, **content, "created": date.today().isoformat(),
                               "grid": {"tau": list(TAUS), "min_cells": list(MIN_CELLS), "nominal": {"tau": TAU, "min_cells": MIN}}})
    write(d / "profiles.json", {**head, "profiles": profs})
    write(d / "scenarios.json", {**head, "scenarios": scenarios()})
    meth = method(used, processing_steps(run))
    write(d / "method.json", {**head, **meth})
    write(d / "status.json", {**head, **status(validation, meth["sources"], rid, date.today().isoformat())})
    write(d / "coverage.json", {**head, "scenarios": {sc: {t: coverage_shares(cells, t, land) for t in ts}
                                                       for sc, ts in SCENARIO_TARGETS.items()}})
    index = cell_index(cells)
    for sc, ts in SCENARIO_TARGETS.items():
        for t in ts:
            for tau in TAUS:
                for mc in MIN_CELLS:
                    cached = run / "zones-grid" / sc / t / f"t{tau}-m{mc}.json"
                    if tau == TAU and mc == MIN and (run / f"zones-{sc}-{t}.json").exists():
                        zs = json.loads((run / f"zones-{sc}-{t}.json").read_text())     # nominal: carries the Monte Carlo
                    elif cached.exists():
                        zs = json.loads(cached.read_text())                              # same run, same zones
                    else:
                        zs = zones_for(cells, sc, t, tau, mc)
                        cached.parent.mkdir(parents=True, exist_ok=True)
                        cached.write_text(json.dumps(zs))
                    write(d / "zones" / sc / t / f"t{tau}-m{mc}.json",
                          {**head, "scenario": sc, "target": t, "tau": tau, "min_cells": mc,
                           "zones": [zone_record(z, k + 1, tau, mc, cells, index) for k, z in enumerate(zs)]})
    idx_path = out / "index.json"
    idx = json.loads(idx_path.read_text()) if idx_path.exists() else {"releases": []}
    entry = {"id": rid, "run": run.name, "methodology_version": METHODOLOGY_VERSION, "protocol": PROTOCOL,
             "commit": commit, "created": date.today().isoformat(), "body": BODY}
    idx["releases"] = keep_releases(idx["releases"], entry)
    idx.setdefault("current_by_body", {})[BODY] = rid
    if BODY == "moon" or "current" not in idx:
        idx["current"] = rid                                      # the default release stays lunar
    write(idx_path, idx)
    return rid


def keep_releases(listed: list[dict], entry: dict, per_body: int = 4) -> list[dict]:
    """The new entry first, then the latest releases of each body (entries without a body are lunar)."""
    out, count = [entry], {entry.get("body", "moon"): 1}
    for r in listed:
        b = r.get("body", "moon")
        if r["id"] != entry["id"] and count.get(b, 0) < per_body:
            out.append(r)
            count[b] = count.get(b, 0) + 1
    return out


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


if __import__("os").environ.get("EARTHMOON_BODY") == "mars":     # the Mars release (scenario D, protocol mars-v1)
    from discovery import mars_run as _mars_run
    _mars_run.configure_release(sys.modules[__name__])


if __name__ == "__main__":
    sys.exit(main())
