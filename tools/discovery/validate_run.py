"""Validation of a global run against validation-protocol-v3 (T43, T43b). Each check reports its pass rule and outcome.

    PYTHONPATH=tools python tools/discovery/validate_run.py all --run /data/run001

Checks (docs/VALIDATION_PROTOCOL.md):
- negatives: at most 1 of 18 in the top 10% of any scenario target after masks; all 18 masked or flagged;
- positives: none exist for scenarios A and B (protocol table), so there is no positive validation;
- self-consistency: held-out lunar windows of each target, KS distance to uniform <= 0.05;
- bias: evaluated and candidate cells per 10° latitude band and per continent (Natural Earth, 1:110m);
- uncertainty: 500 Monte Carlo runs (seed 20261119, 0.5° slope noise) on zone cells, against a fixed random
  sample of 200,000 evaluated cells that sets the top-decile threshold of each run;
- reproducibility: five refined tiles rebuilt from their inputs give identical SHA-256 and identical cell rows.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from discovery.discover import (MIN, SCENARIO_TARGETS, TARGET_SCALE, TAU, _num, candidates,  # noqa: E402
                                cell_centre, global_cell, latitude_bands, load_cells, locate_points, owner_tile,
                                percentile_rank, refined_scales, rock_masked)

ROOT = Path(__file__).resolve().parents[2]
SEED, RUNS, SIGMA, SAMPLE = 20261119, 500, 0.5, 200_000
MC_PARALLEL = 1                                                     # two large targets exceeded the 15 GB Docker VM


# --- pure part (tested) ------------------------------------------------------------------------------------

def ks_uniform(t: np.ndarray) -> float:
    s = np.sort(np.asarray(t, float))
    n = s.size
    return float(max(np.max(np.arange(1, n + 1) / n - s), np.max(s - np.arange(n) / n)))


def block_split(a: np.ndarray, b: np.ndarray, size: float) -> np.ndarray:
    """Checkerboard of blocks of `size` (same units as a and b): True for the held-out half."""
    return ((np.floor(a / size) + np.floor(b / size)) % 2).astype(bool)


def cell_rows(ids: np.ndarray, cells: dict) -> np.ndarray:
    """Row of each global cell id in the run table, -1 when the run has no such cell."""
    table = np.asarray(cells["cell"]).astype(np.int64)
    order = np.argsort(table)
    k = np.clip(np.searchsorted(table[order], ids), 0, table.size - 1)
    return np.where(table[order][k] == ids, order[k], -1)


def in_top_decile(median: float, masked_share: float, evaluated: np.ndarray) -> bool:
    """After masks: a masked cell (half or more of its windows hidden) is never counted in the top 10%."""
    if not np.isfinite(median) or masked_share >= 0.5:
        return False
    v = evaluated[np.isfinite(evaluated)]
    return bool(median >= np.percentile(v, 90))


# --- checks (IO) -------------------------------------------------------------------------------------------

def negatives(run: Path, cells: dict, cube: Path, rock_path: str) -> dict:
    import pyarrow.parquet as pq
    import yaml
    from rasterio.transform import Affine
    from discovery.antarctic import outcrop_share
    from discovery.compare import MASK_CLASSES
    from discovery.copernicus import tile_name
    pts = yaml.safe_load((ROOT / "data/validation/negatives.yaml").read_text(encoding="utf-8"))["negatives"]
    rock = np.load(rock_path + ".npy", mmap_mode="r")
    rock_tf = Affine(*json.loads(Path(rock_path + ".json").read_text())["transform"])
    lat, lon = _num(cells["lat"]), _num(cells["lon"])
    plat, plon = np.array([p["lat"] for p in pts]), np.array([p["lon"] for p in pts])
    where = cell_rows(global_cell(plat, plon), cells)               # the global cell that holds each point
    rows = []
    for k, p in enumerate(pts):
        # mask test on the 1 km window that holds the point (the unit the engine masks), global 90 m cube,
        # which also covers screened-out tiles
        name = tile_name(int(np.floor(p["lat"])), int(np.floor(p["lon"])), "glo90")
        f = cube / "glo90-90m" / f"{name}.windows.parquet"
        hidden, how = None, "no 90 m tile (sea or no DEM)"
        if f.exists():
            c = pq.read_table(f, columns=["lat", "lon", *MASK_CLASSES, "wc_covered"]).to_pydict()
            i = int(locate_points(plat[k:k + 1], plon[k:k + 1], np.array(c["lat"]), np.array(c["lon"]), reach_km=0.71)[0])
            if i < 0:
                hidden, how = None, "no 90 m window within reach"
            elif (c["wc_covered"][i] or 0) > 0:
                share = sum((c[m][i] or 0.0) for m in MASK_CLASSES)
                hidden, how = share >= 0.5, f"WorldCover hidden share {share:.2f}"
            elif p["lat"] < -60:
                r = float(outcrop_share(plat[k:k + 1], plon[k:k + 1], rock, rock_tf)[0])
                m, _ = rock_masked(np.array([r]), np.array([0.0]))
                hidden, how = bool(m[0]), f"rock share {r:.2f}"
            else:
                hidden, how = None, "cover unknown (flagged)"
        row = {**p, "ground_hidden": hidden, "mask_evidence": how, "flagged": hidden is None, "targets": {}}
        j = int(where[k])
        for t in TARGET_SCALE:
            med = _num(cells.get(f"{t}:median", [None] * lat.size))
            if j < 0:
                row["targets"][t] = {"cell": None, "top10": False, "note": "no refined cell (screened out or missing)"}
                continue
            ms = float(np.nan_to_num(_num(cells["masked_share"])[j], nan=1.0))
            row["targets"][t] = {"cell": str(cells["cell"][j]), "median": None if not np.isfinite(med[j]) else round(float(med[j]), 4),
                                 "percentile": round(percentile_rank(med[j], med), 2) if np.isfinite(med[j]) else None,
                                 "masked_share": round(ms, 3), "top10": in_top_decile(med[j], ms, med)}
        rows.append(row)
    per = {}
    for sc, ts in SCENARIO_TARGETS.items():
        for t in ts:
            n = sum(r["targets"][t]["top10"] for r in rows)
            per[f"{sc}:{t}"] = {"in_top10": n, "pass": n <= 1}
    masked_or_flagged = sum(bool(r["ground_hidden"]) or r["flagged"] for r in rows)
    return {"points": rows, "top10": per, "masks": {"masked_or_flagged": masked_or_flagged, "of": len(rows),
                                                      "pass": masked_or_flagged == len(rows)}}


def self_consistency(profiles_windows: Path) -> dict:
    import pyarrow.parquet as pq
    from discovery.compare import percentile_typicality
    out = {}
    for t in TARGET_SCALE:
        if t == "moon-pits":
            sites = json.loads((ROOT / "data/profiles/moon/moon-pits.json").read_text(encoding="utf-8"))["sites"]
            v = np.array([s["context_slope_mean"] for s in sites if s["context_slope_mean"] is not None])
            held = (np.arange(v.size) % 2).astype(bool)                       # alternate sites in atlas order
            how = "alternate sites (site set)"
        else:
            tab = pq.read_table(profiles_windows / f"{t}.windows.parquet")
            cols = tab.column_names
            v = tab.column("slope_mean").to_numpy()
            if "x_m" in cols:
                held = block_split(tab.column("x_m").to_numpy(), tab.column("y_m").to_numpy(), 5000.0)
                how = "5 km blocks (checkerboard)"
            else:
                la, lo = tab.column("lat").to_numpy(), tab.column("lon").to_numpy()
                held = block_split(la * 30.32, lo * 30.32 * np.cos(np.radians(la)), 5.0)   # km on the Moon
                how = "5 km blocks (checkerboard)"
        ok = np.isfinite(v)
        typ = percentile_typicality(v[held & ok], v[~held & ok])
        ks = ks_uniform(typ)
        out[t] = {"held_out": int(typ.size), "split": how, "mean": round(float(typ.mean()), 4), "ks": round(ks, 4),
                  "pass": ks <= 0.05}
    return out


def continents(lat: np.ndarray, lon: np.ndarray) -> np.ndarray:
    from rasterio.features import rasterize
    from rasterio.transform import from_origin
    gj = json.loads(Path("/data/natural-earth/ne_110m_admin_0_countries.geojson").read_text(encoding="utf-8"))
    names = sorted({f["properties"]["CONTINENT"] for f in gj["features"]})
    code = {n: i + 1 for i, n in enumerate(names)}
    grid = rasterize(((f["geometry"], code[f["properties"]["CONTINENT"]]) for f in gj["features"]),
                     out_shape=(1800, 3600), transform=from_origin(-180, 90, 0.1, 0.1), fill=0, dtype="uint8")
    r = np.clip(((90 - lat) / 0.1).astype(int), 0, 1799)
    c = np.clip(((lon + 180) / 0.1).astype(int), 0, 3599)
    lab = np.array(["unassigned (coast at 1:110m)"] + names)
    return lab[grid[r, c]]


def bias(cells: dict) -> dict:
    lat, lon = _num(cells["lat"]), _num(cells["lon"])
    cont = continents(lat, lon)
    out = {}
    for sc, ts in SCENARIO_TARGETS.items():
        for t in ts:
            med = _num(cells.get(f"{t}:median", [None] * lat.size))
            elim = np.zeros(lat.size, bool)
            from discovery.discover import ELIMINATING
            for r in ELIMINATING[sc]:
                elim |= np.asarray(cells.get(f"req:{r}", [None] * lat.size)) == "failed"
            cand = candidates(med, elim, np.nan_to_num(_num(cells["masked_share"]), nan=1.0), TAU,
                              confidence=cells["confidence"])
            evaluated = np.isfinite(med)
            by_cont = {}
            for name in sorted(set(cont.tolist())):
                m = cont == name
                by_cont[name] = {"evaluated": int((m & evaluated).sum()), "candidates": int((m & cand).sum())}
            out[f"{sc}:{t}"] = {"latitude": latitude_bands(lat[evaluated], cand[evaluated]), "continent": by_cont}
    return out


def _mc_target(args) -> dict:
    """One target, in its own process: masked window slopes of its zone cells and of its sample cells (written by
    the assessment, per owner tile), 500 noise draws, each zone's share of runs at or above the sample's 90th
    percentile."""
    t, k, run, refs_path, sample_ids = args
    import pyarrow.parquet as pq
    from discovery.compare import cell_medians, percentile_typicality
    ref = np.load(refs_path)[t]
    scale = TARGET_SCALE[t]
    keys = [(sc, t) for sc, ts in SCENARIO_TARGETS.items() if t in ts]
    zones = {key: json.loads((Path(run) / f"zones-{key[0]}-{t}.json").read_text()) for key in keys}
    need = np.unique(np.array(list(sample_ids) + [c for zs in zones.values() for z in zs for c in z["cell_ids"]]).astype(np.int64))
    clat, clon = cell_centre(need)
    owner = owner_tile(clat, clon)
    ids, slopes = [], []
    for key in sorted(set(owner.tolist())):
        f = Path(run) / "windows-parts" / scale / f"{key.replace(',', '_')}.parquet"
        if not f.exists():
            continue
        tab = pq.read_table(f)
        cid, sl = tab.column("cell").to_numpy(), tab.column("slope").to_numpy()
        keep = np.isin(cid, need[owner == key])
        ids.append(cid[keep])
        slopes.append(sl[keep])
    uniq, code = np.unique(np.concatenate(ids), return_inverse=True)
    base = np.concatenate(slopes).astype("float64")

    def index(cells: list) -> np.ndarray:
        a = np.asarray(cells).astype(np.int64)
        j = np.searchsorted(uniq, a)
        ok = (j < uniq.size) & (uniq[np.minimum(j, uniq.size - 1)] == a)
        return j[ok]

    s_idx = index(sample_ids)
    z_idx = {key: [index(z["cell_ids"]) for z in zones[key]] for key in keys}
    hits = {key: np.zeros(len(zones[key])) for key in keys}
    rng = np.random.default_rng([SEED, k])                         # one stream per target, fixed order
    for r in range(RUNS):
        _, med = cell_medians(percentile_typicality(base + rng.normal(0.0, SIGMA, base.size), ref), code)
        thr = np.nanpercentile(med[s_idx], 90)
        for key in keys:
            zm = np.array([np.nanmedian(med[ix]) if ix.size and np.isfinite(med[ix]).any() else -1.0 for ix in z_idx[key]])
            hits[key] += zm >= thr
        if (r + 1) % 50 == 0:
            print(f"mc {t} {r + 1}/{RUNS}", flush=True)
    out = {}
    for key in keys:
        shares = hits[key] / RUNS
        for z, sh in zip(zones[key], shares):
            z["mc_top_decile_share"] = round(float(sh), 3)
        (Path(run) / f"zones-{key[0]}-{t}.json").write_text(json.dumps(zones[key], indent=1) + "\n")
        out[f"{key[0]}:{t}"] = {"zones": len(shares), "stable_zones_90pct": int((shares >= 0.9).sum()), "runs": RUNS,
                                "seed": [SEED, k], "slope_sigma_deg": SIGMA, "sample_cells": int(s_idx.size)}
    return out


def mc_done(run: Path, t: str) -> dict | None:
    """Summary of a target whose zone files all carry their Monte Carlo share (a resumed run skips it), else None."""
    out = {}
    for sc, ts in SCENARIO_TARGETS.items():
        if t not in ts:
            continue
        zs = json.loads((Path(run) / f"zones-{sc}-{t}.json").read_text())
        if any("mc_top_decile_share" not in z for z in zs):
            return None
        out[f"{sc}:{t}"] = {"zones": len(zs), "stable_zones_90pct": sum(z["mc_top_decile_share"] >= 0.9 for z in zs),
                            "from_files": True}
    return out


def monte_carlo(run: Path, cells: dict, cube: Path, refs_path: str, rock_path: str) -> dict:
    """Zone cells and a fixed sample of 200,000 evaluated cells per target, under 500 noise draws; one process
    per target. Seeds: sample drawn with [SEED, k, 0], noise with [SEED, k], k the target's index in sorted order."""
    from concurrent.futures import ProcessPoolExecutor
    targets = sorted(TARGET_SCALE)
    jobs = []
    out = {}
    for k, t in enumerate(targets):
        done = mc_done(run, t)
        if done:                                                      # resumed: same seeds, same result
            out.update(done)
            continue
        med = _num(cells.get(f"{t}:median", [None] * len(cells["cell"])))
        idx = np.flatnonzero(np.isfinite(med))
        pick = np.random.default_rng([SEED, k, 0]).choice(idx, size=min(SAMPLE, idx.size), replace=False)
        jobs.append((t, k, str(run), refs_path, sorted(np.asarray(cells["cell"])[pick].tolist())))
    import multiprocessing
    # spawned workers start empty: forked ones copied the parent's 6.7 M-row cell table (OOM, 19/11/2026)
    with ProcessPoolExecutor(max_workers=MC_PARALLEL, mp_context=multiprocessing.get_context("spawn")) as pool:
        for res in pool.map(_mc_target, jobs):
            out.update(res)
    return out


def reproducibility(run: Path, cube: Path, refs_path: str, rock_path: str, tiles_file: Path, refined: dict) -> dict:
    """Five refined tiles (seeded) rebuilt from their inputs into a scratch folder: same SHA-256 as the manifest,
    and the same cell rows as the run table."""
    import subprocess
    from discovery.copernicus import tile_name
    from discovery.discover import assess_tile, neighbour_keys
    keys = sorted(x for x in tiles_file.read_text().split())
    pick = sorted(np.random.default_rng(SEED).choice(keys, size=5, replace=False).tolist())
    import shutil
    scratch = run / "rebuild"
    if scratch.exists():
        shutil.rmtree(scratch)                                        # a rebuild must recompute, never skip
    (scratch / "glo30-40m").mkdir(parents=True, exist_ok=True)
    (scratch / "tiles.txt").write_text("\n".join(pick) + "\n")
    for f in ("listing.json", "worldcover-listing.json"):              # same source listings as the run
        shutil.copy(cube / "glo30-40m" / f, scratch / "glo30-40m" / f)
    subprocess.run([sys.executable, str(ROOT / "tools/discovery/cube.py"), "--product", "glo30", "--pixel", "40",
                    "--tiles", str(scratch / "tiles.txt"), "--out", str(scratch), "--workers", "5"], check=True)
    manifest = {}
    for line in (cube / "glo30-40m" / "manifest.jsonl").read_text().splitlines():
        r = json.loads(line)
        manifest[r["tile"]] = r
    rebuilt = {json.loads(x)["tile"]: json.loads(x) for x in (scratch / "glo30-40m" / "manifest.jsonl").read_text().splitlines()}
    rows = []
    for k in pick:
        name = tile_name(*(int(v) for v in k.split(",")), "glo30")
        a, b = manifest.get(name, {}).get("outputs"), rebuilt.get(name, {}).get("outputs")
        rows.append({"tile": k, "identical_sha256": a == b and a is not None})
    cells = load_cells(str(run / "cells.parquet"))
    by_cell = {c: i for i, c in enumerate(cells["cell"])}
    same_rows = True
    for k in pick:
        for r in assess_tile(k, str(cube), refs_path, rock_path, {nk: refined[nk] for nk in neighbour_keys(k) if nk in refined}):
            i = by_cell.get(r["cell"])
            if i is None:
                same_rows = False
                continue
            for col, v in r.items():
                if col in cells:
                    w = cells[col][i]
                    if isinstance(v, float) and v == v and (w is None or abs(v - float(w)) > 1e-9):
                        same_rows = False
    ok = all(r["identical_sha256"] for r in rows) and same_rows
    return {"tiles": rows, "identical_cell_rows": same_rows, "pass": ok}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("what", choices=["negatives", "self", "bias", "mc", "repro", "all"])
    ap.add_argument("--run", type=Path, default=Path("/data/run002"))
    ap.add_argument("--cube", type=Path, default=Path("/data/cube"))
    ap.add_argument("--profiles-windows", type=Path, default=Path("/data/profiles/moon"))
    ap.add_argument("--rock", default="/data/add-rock-outcrop/outcrops_200m_3031")
    ap.add_argument("--tiles", type=Path, default=Path("/data/cube/tiles-refine-glo30-40m.txt"))
    ap.add_argument("--refined", nargs="+", default=["/data/cube/tiles-refine-glo30-40m.txt",
                                                      "/data/cube/tiles-refine-glo30-59m.txt"])
    a = ap.parse_args(argv)
    refs = str(a.run / "refs.npz")
    cells = load_cells(str(a.run / "cells.parquet"))
    out_path = a.run / "validation.json"
    out = json.loads(out_path.read_text()) if out_path.exists() else {}
    out["positives"] = {"A": "none: no verified reference names a site (protocol table)", "B": "none (same)",
                        "consequence": "no positive validation for scenarios A and B"}
    steps = ["negatives", "self", "bias", "mc", "repro"] if a.what == "all" else [a.what]
    for s in steps:
        if s == "negatives":
            out["negatives"] = negatives(a.run, cells, a.cube, a.rock)
        elif s == "self":
            out["self_consistency"] = self_consistency(a.profiles_windows)
        elif s == "bias":
            out["bias"] = bias(cells)
        elif s == "mc":
            out["monte_carlo"] = monte_carlo(a.run, cells, a.cube, refs, a.rock)
        elif s == "repro":
            out["reproducibility"] = reproducibility(a.run, a.cube, refs, a.rock, a.tiles, refined_scales(a.refined))
        out_path.write_text(json.dumps(out, indent=1, default=str) + "\n")
        print(s, "done", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
