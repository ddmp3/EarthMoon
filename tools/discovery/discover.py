"""First global discovery run (T43, run-001): assessment of every refined tile, zones, controls, bias bands.

Rules fixed before the run (T43), on top of T26 and validation-protocol-v1:
- a candidate cell has a median typicality >= tau for the target, is not eliminated by a requirement of the
  scenario, and fewer than half of its windows are masked;
- zones are candidate cells joined by 8-neighbour connection (zones.py), of at least min_cells cells;
- zones are ranked by the median typicality of their cells, then by area (larger first);
- a control point belongs to the cell whose centre is nearest, within 3.6 km (half a cell diagonal); with no such
  cell its value is missing;
- south of 60°S, where WorldCover has no data, a window is masked when less than half of it is rock (SCAR outcrops):
  the rest is ice or snow.
"""
from __future__ import annotations

import numpy as np

from discovery.compare import MASK_CLASSES
from discovery.zones import EARTH_R_KM, _xyz

TAUS, MIN_CELLS = (0.5, 0.7, 0.9), (1, 3, 9)
TAU, MIN = 0.5, 3
REACH_KM = 3.6


def candidates(median: np.ndarray, eliminated: np.ndarray, masked_share: np.ndarray, tau: float,
               confidence: np.ndarray | None = None) -> np.ndarray:
    """Protocol v2 rule; with `confidence` (protocol v3) a candidate must also have high confidence."""
    m = np.asarray(median, float)
    out = np.isfinite(m) & (np.nan_to_num(m) >= tau) & ~np.asarray(eliminated, bool) & (np.asarray(masked_share) < 0.5)
    if confidence is not None:
        out &= np.asarray(confidence, dtype=object) == "high"
    return out


# protocol v3: one global equal-area grid of 5 km cells (EASE-Grid 2.0), so that no cell is cut by a tile edge
EASE = "EPSG:6933"
CELL_M = 5000.0


def global_cell(lat: np.ndarray, lon: np.ndarray, cell_m: float = CELL_M) -> np.ndarray:
    """Integer id of the 5 km EASE-Grid 2.0 cell holding each point."""
    from rasterio.warp import transform
    x, y = transform("EPSG:4326", EASE, np.asarray(lon, float).tolist(), np.asarray(lat, float).tolist())
    ix = np.floor(np.array(x) / cell_m).astype(np.int64) + 4_000_000
    iy = np.floor(np.array(y) / cell_m).astype(np.int64) + 4_000_000
    return ix * 10_000_000 + iy


def cell_centre(cell: np.ndarray, cell_m: float = CELL_M) -> tuple[np.ndarray, np.ndarray]:
    from rasterio.warp import transform
    c = np.asarray(cell, np.int64)
    x = ((c // 10_000_000) - 4_000_000 + 0.5) * cell_m
    y = ((c % 10_000_000) - 4_000_000 + 0.5) * cell_m
    lon, lat = transform(EASE, "EPSG:4326", x.tolist(), y.tolist())
    return np.array(lat), np.array(lon)


def owner_tile(lat: np.ndarray, lon: np.ndarray) -> np.ndarray:
    """The 1° tile holding each cell centre: the only tile that assesses that cell."""
    la = np.floor(np.asarray(lat, float)).astype(int)
    lo = np.floor((np.asarray(lon, float) + 180) % 360 - 180).astype(int)
    return np.array([f"{a},{b}" for a, b in zip(la, lo)], dtype=object)


def rank_zones(zones: list[dict]) -> list[dict]:
    return sorted(zones, key=lambda z: (-z["median"], -z["area_km2"]))


def locate_points(plat: np.ndarray, plon: np.ndarray, lat: np.ndarray, lon: np.ndarray,
                  reach_km: float = REACH_KM) -> np.ndarray:
    """Index of the nearest cell centre for each point, or -1 when none is within reach_km."""
    cells = _xyz(np.asarray(lat, float), np.asarray(lon, float))
    pts = _xyz(np.asarray(plat, float), np.asarray(plon, float))
    out = np.full(len(pts), -1)
    for k, p in enumerate(pts):
        d = np.linalg.norm(cells - p, axis=1)
        i = int(np.argmin(d))
        if d[i] <= reach_km:
            out[k] = i
    return out


def percentile_rank(value: float, values: np.ndarray) -> float:
    """Share (%) of evaluated cells with a lower value; NaN for a missing value."""
    v = np.asarray(values, float)
    v = v[np.isfinite(v)]
    if not np.isfinite(value) or v.size == 0:
        return float("nan")
    return float(100.0 * np.mean(v < value))


def latitude_bands(lat: np.ndarray, selected: np.ndarray) -> dict:
    """Cells and selected cells per 10° latitude band (cells are equal-area, so counts compare)."""
    out = {}
    edges = np.arange(-90, 91, 10)
    for lo, hi in zip(edges[:-1], edges[1:]):
        m = (lat >= lo) & (lat < hi) if hi < 90 else (lat >= lo) & (lat <= hi)
        out[f"{lo}..{hi}"] = {"cells": int(m.sum()), "selected": int((m & selected).sum())}
    return out


def rock_masked(rock_share: np.ndarray, wc_covered: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """South of 60°S (rock share known, WorldCover absent): masked when under half rock. Returns (masked, known)."""
    known = np.isfinite(rock_share) & ~(np.nan_to_num(wc_covered) > 0)
    return known & (np.nan_to_num(rock_share) < 0.5), known


def dossier_zones(zones: list[dict], top: int = 20, same_km: float = 10.0) -> list[dict]:
    """Top zones of a scenario across its targets; a zone found for several targets (centres within same_km) is
    kept once, with the other targets listed in `also_for`."""
    kept: list[dict] = []
    for z in rank_zones(zones):
        p = _xyz(np.array([z["lat"]]), np.array([z["lon"]]))[0]
        dup = next((k for k in kept if np.linalg.norm(_xyz(np.array([k["lat"]]), np.array([k["lon"]]))[0] - p) <= same_km), None)
        if dup is not None:
            if z["target"] != dup["target"] and z["target"] not in dup["also_for"]:
                dup["also_for"].append(z["target"])
            continue
        kept.append({**z, "also_for": []})
        if len(kept) == top:
            break
    return kept


def top_decile_share(zone_medians_per_run: list[np.ndarray], sample_medians_per_run: list[np.ndarray]) -> float:
    """Share of runs in which the zone median (median of its cell medians) reaches the 90th percentile of the
    sampled cells of the same run."""
    hits = 0
    for z, s in zip(zone_medians_per_run, sample_medians_per_run):
        zm = np.nanmedian(z) if np.isfinite(z).any() else -1.0
        hits += zm >= np.nanpercentile(s, 90)
    return hits / len(zone_medians_per_run)


__all__ = ["candidates", "rank_zones", "locate_points", "percentile_rank", "latitude_bands", "rock_masked",
           "EARTH_R_KM"]


# --- assessment of one tile (IO) ---------------------------------------------------------------------------

SCALES = {"glo30-40m": 40.0, "glo30-59m": 59.225293836}
TARGET_SCALE = {"moon-south-polar-cap-v2": "glo30-40m", "moon-polar-lit-highlands": "glo30-40m",
                "moon-psr": "glo30-40m", "moon-mare-plains": "glo30-59m", "moon-pits": "glo30-59m"}
SCENARIO_TARGETS = {"A": ["moon-polar-lit-highlands", "moon-psr", "moon-pits"],
                    "B": ["moon-polar-lit-highlands", "moon-psr", "moon-mare-plains", "moon-south-polar-cap-v2"]}
ELIMINATING = {"A": [], "B": ["climbing_limit_lrv"]}
WCOLS = ["i", "j", "lat", "lon", "slope_mean", "traversable_15", "traversable_20", *MASK_CLASSES, "wc_covered"]
_CTX: dict = {}


def _context(refs_path: str, rock_path: str) -> dict:
    """Per-worker inputs, loaded once: lunar references and the Antarctic rock raster."""
    if "refs" not in _CTX:
        import json
        from rasterio.transform import Affine
        d = np.load(refs_path)
        _CTX["refs"] = {k: d[k] for k in d.files}
        _CTX["rock"] = np.load(rock_path + ".npy", mmap_mode="r")
        _CTX["rock_tf"] = Affine(*json.loads(open(rock_path + ".json").read())["transform"])
    return _CTX


def window_masks(w: dict, ctx: dict) -> tuple[np.ndarray, np.ndarray]:
    """(masked, cover unknown) per window: WorldCover north of 60°S, rock outcrops south of it."""
    from discovery.antarctic import outcrop_share
    from discovery.compare import masked_windows
    masked, unknown = masked_windows(w)
    south = np.asarray(w["lat"]) < -60
    if south.any():
        share = np.full(len(w["lat"]), np.nan)
        share[south] = outcrop_share(np.asarray(w["lat"])[south], np.asarray(w["lon"])[south], ctx["rock"], ctx["rock_tf"])
        rmask, known = rock_masked(share, w["wc_covered"])
        masked = masked | rmask
        unknown = unknown & ~known
    return masked, unknown


def refined_scales(lists: list[str]) -> dict:
    """Tile -> the scales at which this run refined it, from the screening lists (tiles-refine-<scale>.txt).
    Files of other scales may exist from an earlier run with other code: they are never read."""
    from pathlib import Path
    out: dict = {}
    for f in lists:
        scale = next(sc for sc in SCALES if sc in Path(f).name)
        for k in Path(f).read_text().split():
            out.setdefault(k.strip(), []).append(scale)
    return {k: sorted(v) for k, v in out.items()}


def assess_tile(key: str, cube: str, refs_path: str, rock_path: str, scales: list[str] | None = None) -> list[dict]:
    """Rows of every cell of one tile: similarity per target, requirements, suitability, coverage, confidence."""
    import pyarrow.parquet as pq
    from pathlib import Path
    from discovery.compare import assess_cells
    from discovery.compare_run import RULES, SUITABILITY, confidence
    from discovery.copernicus import tile_name
    ctx = _context(refs_path, rock_path)
    la, lo = (int(v) for v in key.split(","))
    name = tile_name(la, lo, "glo30")
    rows: dict = {}
    win = {}
    for scale in (scales if scales is not None else SCALES):
        f = Path(cube) / scale / f"{name}.windows.parquet"
        if f.exists():
            t = pq.read_table(f, columns=WCOLS)
            w = {k: t.column(k).to_numpy() for k in WCOLS}
            w["cell"] = np.array([f"{name}:{i}:{j}" for i, j in zip(w["i"], w["j"])])
            w["masked"], w["unknown"] = window_masks(w, ctx)
            win[scale] = w
            c = pq.read_table(Path(cube) / scale / f"{name}.cells.parquet", columns=["cell", "lat", "lon", "area_km2"])
            for cid, cla, clo, ar in zip(*(c.column(k).to_pylist() for k in ("cell", "lat", "lon", "area_km2"))):
                rows.setdefault(cid, {"cell": cid, "tile": key, "lat": cla, "lon": clo, "area_km2": ar})
    for t, scale in TARGET_SCALE.items():
        if scale not in win:
            for r in rows.values():
                r[f"{t}:screened_out"] = True
            continue
        w = win[scale]
        s = np.where(w["masked"], np.nan, w["slope_mean"])
        res = assess_cells({"cell": w["cell"], "slope_mean": s}, {t: ctx["refs"][t]}, [], None)
        for cid, out in res.items():
            r = rows.setdefault(cid, {"cell": cid, "tile": key, "lat": np.nan, "lon": np.nan, "area_km2": np.nan})
            for k, v in out["similarity"][t].items():
                r[f"{t}:{k}"] = v
    cov_scale = "glo30-40m" if "glo30-40m" in win else ("glo30-59m" if "glo30-59m" in win else None)
    if cov_scale:
        # requirements, suitability, coverage and confidence at the finest refined scale of the tile
        w = win[cov_scale]
        reqs = [{"id": rid, **{k: v for k, v in rule.items() if k in ("param", "at_least", "at_most")}} for rid, rule in RULES.items()]
        res = assess_cells({"cell": w["cell"], **{k: w[k] for k in ("slope_mean", "traversable_15", "traversable_20")}}, {}, reqs, None)
        for sc, rule in SUITABILITY.items():
            s = assess_cells({"cell": w["cell"], rule["param"]: w[rule["param"]]}, {}, [],
                             {k: rule[k] for k in ("id", "param", "good", "bad")})
            for cid, out in s.items():
                rows[cid][f"suitability_{sc}"] = out["suitability"]["median"]
        ids, inv = np.unique(w["cell"], return_inverse=True)
        n = np.bincount(inv)
        valid = np.bincount(inv, weights=(np.isfinite(w["slope_mean"]) & ~w["masked"]).astype(float)).astype(int)
        nm = np.bincount(inv, weights=w["masked"].astype(float)).astype(int)
        nu = np.bincount(inv, weights=w["unknown"].astype(float)).astype(int)
        for k, cid in enumerate(ids):
            r = rows[cid]
            for rid, st in res[cid]["requirements"].items():
                r[f"req:{rid}"] = st["status"]
            r.update({"assessed_at": cov_scale, "windows": int(n[k]), "valid_unmasked": int(valid[k]), "masked": int(nm[k]),
                      "cover_unknown": int(nu[k]), "masked_share": float(nm[k] / n[k]),
                      "confidence": confidence(int(valid[k]), int(n[k]), int(nm[k]), int(nu[k]))})
    return list(rows.values())


def _schema():
    import pyarrow as pa
    f = [pa.field("cell", pa.string()), pa.field("tile", pa.string()), pa.field("lat", pa.float64()),
         pa.field("lon", pa.float64()), pa.field("area_km2", pa.float64())]
    for t in TARGET_SCALE:
        f += [pa.field(f"{t}:{k}", pa.int64()) for k in ("windows", "valid")]
        f += [pa.field(f"{t}:{k}", pa.float64()) for k in ("median", "share_above_half", "p25", "p75")]
        f += [pa.field(f"{t}:screened_out", pa.bool_())]
    f += [pa.field(f"req:{r}", pa.string()) for r in ("base_slope", "climbing_limit_lrv", "climbing_limit_viper")]
    f += [pa.field("suitability_A", pa.float64()), pa.field("suitability_B", pa.float64()),
          pa.field("assessed_at", pa.string()), pa.field("windows", pa.int64()), pa.field("valid_unmasked", pa.int64()),
          pa.field("masked", pa.int64()), pa.field("cover_unknown", pa.int64()), pa.field("masked_share", pa.float64()),
          pa.field("confidence", pa.string())]
    return pa.schema(f)


CELL_SCHEMA = _schema()


def write_rows(path, rows: list[dict]) -> int:
    """Cell rows of one tile, with the fixed schema (missing columns are null)."""
    import pyarrow as pa
    import pyarrow.parquet as pq
    cols = {f.name: [r.get(f.name) for r in rows] for f in CELL_SCHEMA}
    for f in CELL_SCHEMA:
        if pa.types.is_floating(f.type):
            cols[f.name] = [None if (v is None or v != v) else float(v) for v in cols[f.name]]
    pq.write_table(pa.Table.from_pydict(cols, schema=CELL_SCHEMA), path, compression="zstd")
    return len(rows)


def assess_tile_to_file(key: str, cube: str, refs_path: str, rock_path: str, outdir: str, scales: list[str]) -> int:
    from pathlib import Path
    rows = assess_tile(key, cube, refs_path, rock_path, scales)
    return write_rows(Path(outdir) / f"{key.replace(',', '_')}.parquet", rows) if rows else 0


# --- commands ----------------------------------------------------------------------------------------------

def build_refs(profiles_windows: str, pits_json: str, out: str) -> dict:
    """Sorted lunar slope_mean of every target, in one npz loaded once per worker."""
    import json
    import pyarrow.parquet as pq
    from pathlib import Path
    refs = {}
    for t in TARGET_SCALE:
        if t == "moon-pits":
            sites = json.loads(Path(pits_json).read_text(encoding="utf-8"))["sites"]
            v = np.array([s["context_slope_mean"] for s in sites if s["context_slope_mean"] is not None], float)
        else:
            v = pq.read_table(Path(profiles_windows) / f"{t}.windows.parquet", columns=["slope_mean"]).column(0).to_numpy()
        refs[t] = np.sort(v[np.isfinite(v)].astype("float64"))
    np.savez(out, **refs)
    return {t: int(v.size) for t, v in refs.items()}


def assess_all(tiles: dict, cube: str, refs_path: str, rock_path: str, out: str, workers: int) -> dict:
    """Each worker writes the cells of its tile to its own file; the files are then joined by streaming, so
    memory stays flat (keeping millions of rows as Python dicts ran out of memory)."""
    import time
    from concurrent.futures import ProcessPoolExecutor, as_completed
    from pathlib import Path
    import pyarrow.parquet as pq
    parts = Path(out).parent / "cells-parts"
    if parts.exists():
        import shutil
        shutil.rmtree(parts)                                       # never mix parts of two assessments
    parts.mkdir(parents=True, exist_ok=True)
    n_cells, failed, t0 = 0, [], time.time()
    with ProcessPoolExecutor(max_workers=workers) as pool:
        futs = {pool.submit(assess_tile_to_file, k, cube, refs_path, rock_path, str(parts), sc): k for k, sc in tiles.items()}
        for n, f in enumerate(as_completed(futs), 1):
            try:
                n_cells += f.result()
            except (OSError, ValueError, KeyError) as e:
                failed.append({"tile": futs[f], "error": f"{type(e).__name__}: {e}"})
            if n % 1000 == 0:
                print(f"{n}/{len(tiles)} tiles, {(time.time() - t0) / 3600:.2f} h", flush=True)
    with pq.ParquetWriter(out, CELL_SCHEMA, compression="zstd") as w:
        for f in sorted(parts.glob("*.parquet")):
            w.write_table(pq.read_table(f, schema=CELL_SCHEMA))
    return {"tiles": len(tiles), "cells": n_cells, "failed": failed, "hours": round((time.time() - t0) / 3600, 2)}


LOAD_COLUMNS = (["cell", "tile", "lat", "lon", "area_km2", "masked_share", "confidence", "suitability_A", "suitability_B",
                 "req:base_slope", "req:climbing_limit_lrv", "req:climbing_limit_viper"]
                + [f"{t}:median" for t in TARGET_SCALE])


def load_cells(path: str, columns: list[str] | None = None) -> dict:
    """The columns that zones, validation and dossiers use (all 50 columns of 6.7 M cells do not fit)."""
    import pyarrow.parquet as pq
    t = pq.read_table(path, columns=columns or LOAD_COLUMNS)
    return {k: t.column(k).to_numpy(zero_copy_only=False) for k in t.column_names}


def _num(a) -> np.ndarray:
    """Float array of a column: numeric columns as they are (nulls are already NaN), others element by element."""
    if isinstance(a, np.ndarray) and a.dtype.kind == "f":
        return a
    return np.array([np.nan if v is None else v for v in a], dtype=float)


def zones_for(cells: dict, scenario: str, target: str, tau: float, min_cells: int) -> list[dict]:
    from discovery.zones import zone_table
    med = _num(cells.get(f"{target}:median", [None] * len(cells["cell"])))
    elim = np.zeros(med.size, bool)
    for r in ELIMINATING[scenario]:
        elim |= np.asarray(cells.get(f"req:{r}", [None] * med.size)) == "failed"
    cand = candidates(med, elim, np.nan_to_num(_num(cells["masked_share"]), nan=1.0), tau)
    idx = np.flatnonzero(cand)
    if idx.size == 0:
        return []
    zs = zone_table(_num(cells["lat"])[idx], _num(cells["lon"])[idx], np.nan_to_num(_num(cells["area_km2"])[idx]), min_cells)
    out = []
    su_all = _num(cells.get(f"suitability_{scenario}", [None] * med.size))        # once, not once per zone
    for z in zs:
        m = idx[z["members"]]
        conf = np.asarray(cells["confidence"])[m]
        row = {"target": target, "scenario": scenario, "cells": z["cells"], "area_km2": round(z["area_km2"], 1),
               "lat": round(z["lat"], 5), "lon": round(z["lon"], 5), "median": round(float(np.median(med[m])), 4),
               "cell_median_p25": round(float(np.percentile(med[m], 25)), 4),
               "cell_median_p75": round(float(np.percentile(med[m], 75)), 4),
               "high_confidence_share": round(float(np.mean(conf == "high")), 3),
               "tiles": sorted(set(np.asarray(cells["tile"])[m].tolist())), "cell_ids": np.asarray(cells["cell"])[m].tolist()}
        for r in ("base_slope", "climbing_limit_lrv", "climbing_limit_viper"):
            st = np.asarray(cells.get(f"req:{r}", [None] * med.size))[m]
            row[f"req:{r}"] = {k: int(np.sum(st == k)) for k in ("met", "failed", "unknown")}
        su = su_all[m]
        row["suitability_median"] = round(float(np.nanmedian(su)), 3) if np.isfinite(su).any() else None
        out.append(row)
    return rank_zones(out)


def _candidate_index(cells: dict, scenario: str, target: str, tau: float) -> np.ndarray:
    med = _num(cells.get(f"{target}:median", [None] * len(cells["cell"])))
    elim = np.zeros(med.size, bool)
    for r in ELIMINATING[scenario]:
        elim |= np.asarray(cells.get(f"req:{r}", [None] * med.size)) == "failed"
    return np.flatnonzero(candidates(med, elim, np.nan_to_num(_num(cells["masked_share"]), nan=1.0), tau))


def zone_counts(cells: dict, scenario: str, target: str, tau: float, min_cells: tuple) -> dict:
    """Number and area of zones for each minimum size, with one connection per tau (no per-zone statistics)."""
    from discovery.zones import connect
    idx = _candidate_index(cells, scenario, target, tau)
    if idx.size == 0:
        return {mc: {"zones": 0, "area_km2": 0.0} for mc in min_cells}
    lab = connect(_num(cells["lat"])[idx], _num(cells["lon"])[idx])
    _, inv, size = np.unique(lab, return_inverse=True, return_counts=True)
    area = np.bincount(inv, weights=np.nan_to_num(_num(cells["area_km2"])[idx]))
    return {mc: {"zones": int((size >= mc).sum()), "area_km2": round(float(area[size >= mc].sum()), 1)}
            for mc in min_cells}


def zones_command(run, top: int = 20) -> dict:
    import json
    cells = load_cells(str(run / "cells.parquet"))
    summary = {"rule": {"tau": TAU, "min_cells": MIN, "grid": {"tau": TAUS, "min_cells": MIN_CELLS}}, "scenarios": {}}
    for sc, targets in SCENARIO_TARGETS.items():
        allz, per = [], {}
        for t in targets:
            grid = {}
            for tau in TAUS:
                for mc, v in zone_counts(cells, sc, t, tau, MIN_CELLS).items():
                    grid[f"tau={tau},min={mc}"] = v
            zs = zones_for(cells, sc, t, TAU, MIN)
            (run / f"zones-{sc}-{t}.json").write_text(json.dumps(zs, indent=1) + "\n")
            per[t] = {"grid": grid, "zones": len(zs), "top": [{k: v for k, v in z.items() if k != "cell_ids"} for z in zs[:top]]}
            allz.extend(zs)
        dz = dossier_zones([{k: v for k, v in z.items() if k != "cell_ids"} for z in allz], top=top)
        summary["scenarios"][sc] = {"targets": per, "dossier_zones": dz}
    (run / "zones.json").write_text(json.dumps(summary, indent=1) + "\n")
    return summary


def main(argv=None) -> int:
    import argparse
    import json
    import sys
    from pathlib import Path
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("what", choices=["refs", "assess", "zones"])
    ap.add_argument("--cube", default="/data/cube")
    ap.add_argument("--run", default="/data/run001")
    ap.add_argument("--profiles-windows", default="/data/profiles/moon")
    ap.add_argument("--pits", default="data/profiles/moon/moon-pits.json")
    ap.add_argument("--rock", default="/data/add-rock-outcrop/outcrops_200m_3031")
    ap.add_argument("--tiles", nargs="+", help="tile lists; the union is assessed")
    ap.add_argument("--workers", type=int, default=12)
    a = ap.parse_args(argv)
    run = Path(a.run)
    run.mkdir(parents=True, exist_ok=True)
    if a.what == "refs":
        print(json.dumps(build_refs(a.profiles_windows, a.pits, str(run / "refs.npz"))))
    elif a.what == "zones":
        out = zones_command(run)
        for sc, v in out["scenarios"].items():
            print(sc, {t: x["zones"] for t, x in v["targets"].items()}, "dossiers", len(v["dossier_zones"]))
    else:
        tiles = refined_scales(a.tiles)
        out = assess_all(tiles, a.cube, str(run / "refs.npz"), a.rock, str(run / "cells.parquet"), a.workers)
        (run / "assess.json").write_text(json.dumps(out, indent=1) + "\n")
        print(json.dumps({k: v for k, v in out.items() if k != "failed"}), "failed", len(out["failed"]))
    return 0


if __name__ == "__main__":
    import sys
    sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parents[1]))
    sys.exit(main())
