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

from discovery.zones import EARTH_R_KM, _xyz

TAUS, MIN_CELLS = (0.5, 0.7, 0.9), (1, 3, 9)
TAU, MIN = 0.5, 3
REACH_KM = 3.6


def candidates(median: np.ndarray, eliminated: np.ndarray, masked_share: np.ndarray, tau: float) -> np.ndarray:
    m = np.asarray(median, float)
    return np.isfinite(m) & (np.nan_to_num(m) >= tau) & ~np.asarray(eliminated, bool) & (np.asarray(masked_share) < 0.5)


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
WCOLS = ["i", "j", "lat", "lon", "slope_mean", "traversable_15", "traversable_20", "wc_tree", "wc_built", "wc_water",
         "wc_snow_ice", "wc_covered"]
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


def assess_tile(key: str, cube: str, refs_path: str, rock_path: str) -> list[dict]:
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
    for scale in SCALES:
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


def assess_all(tiles: list[str], cube: str, refs_path: str, rock_path: str, out: str, workers: int) -> dict:
    import time
    from concurrent.futures import ProcessPoolExecutor, as_completed
    import pyarrow as pa
    import pyarrow.parquet as pq
    rows, failed, t0 = [], [], time.time()
    with ProcessPoolExecutor(max_workers=workers) as pool:
        futs = {pool.submit(assess_tile, k, cube, refs_path, rock_path): k for k in tiles}
        for n, f in enumerate(as_completed(futs), 1):
            try:
                rows.extend(f.result())
            except (OSError, ValueError, KeyError) as e:
                failed.append({"tile": futs[f], "error": f"{type(e).__name__}: {e}"})
            if n % 1000 == 0:
                print(f"{n}/{len(tiles)} tiles, {(time.time() - t0) / 3600:.2f} h", flush=True)
    keys = sorted({k for r in rows for k in r})
    pq.write_table(pa.table({k: [r.get(k) for r in rows] for k in keys}), out, compression="zstd")
    return {"tiles": len(tiles), "cells": len(rows), "failed": failed, "hours": round((time.time() - t0) / 3600, 2)}


def load_cells(path: str) -> dict:
    import pyarrow.parquet as pq
    t = pq.read_table(path)
    return {k: t.column(k).to_numpy(zero_copy_only=False) for k in t.column_names}


def _num(a) -> np.ndarray:
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
        su = _num(cells.get(f"suitability_{scenario}", [None] * med.size))[m]
        row["suitability_median"] = round(float(np.nanmedian(su)), 3) if np.isfinite(su).any() else None
        out.append(row)
    return rank_zones(out)


def zones_command(run, top: int = 20) -> dict:
    import json
    cells = load_cells(str(run / "cells.parquet"))
    summary = {"rule": {"tau": TAU, "min_cells": MIN, "grid": {"tau": TAUS, "min_cells": MIN_CELLS}}, "scenarios": {}}
    for sc, targets in SCENARIO_TARGETS.items():
        allz, per = [], {}
        for t in targets:
            grid = {f"tau={tau},min={mc}": (lambda z: {"zones": len(z), "area_km2": round(sum(x["area_km2"] for x in z), 1)})(
                zones_for(cells, sc, t, tau, mc)) for tau in TAUS for mc in MIN_CELLS}
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
        tiles = sorted({x.strip() for f in a.tiles for x in Path(f).read_text().split()})
        out = assess_all(tiles, a.cube, str(run / "refs.npz"), a.rock, str(run / "cells.parquet"), a.workers)
        (run / "assess.json").write_text(json.dumps(out, indent=1) + "\n")
        print(json.dumps({k: v for k, v in out.items() if k != "failed"}), "failed", len(out["failed"]))
    return 0


if __name__ == "__main__":
    import sys
    sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parents[1]))
    sys.exit(main())
