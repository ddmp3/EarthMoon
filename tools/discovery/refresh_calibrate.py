"""Calibration of the refresh (T52 step 7). Rule written before running (23/11/2026); 10 tiles decided by David.

Simulated update: 10 land tiles of run-mars-001 (seed 20261119) are recomputed with their elevation perturbed by an
independent Gaussian error within the stated Copernicus accuracy (sigma 1.216 m, 2 m LE90): a re-release that changes
nothing real. Mars is used because its cube reads the local GLO-90 copy (no download); the lunar 30 m cube streams
GLO-30. The steps rerun as the planner says (tools/discovery/refresh_plan.py):
- features: the 10 tiles at both Mars scales;
- assess: the cells of these tiles and of their neighbours (their neighbours' windows are read from the real cube);
- zones: only the zones that touch a cell whose candidacy changed (tools/discovery/zones_local.py; David, 23/11:
  recompute the neighbours and nothing else). The candidate list of the run is read once as the starting state.
Measured: seconds per step and per unit; among the reassessed cells, the share whose coverage state changes and the
share whose candidacy at tau 0.5 changes, per target; zones that appear or disappear.
Threshold rule: the 1% of ADR-009 stays if the state-change share is under 1% for every target; otherwise it becomes
the smallest whole percent above the largest measured share. The zone rule is reported, not changed here.

    EARTHMOON_BODY=mars PYTHONPATH=tools python -m discovery.refresh_calibrate --out data/runs/t52-calibration.json
"""
from __future__ import annotations

import argparse
import json
import math
import shutil
import sys
import time
from pathlib import Path

import numpy as np

SEED, N_TILES = 20261119, 10
SIGMA_Z_M = 2.0 / 1.6449                       # Copernicus relative accuracy, 2 m LE90 (as protocol mars-v2)
SCALES = {"glo90-115m-w25": 115.77, "glo90-463m-w25": 463.08}


def sample(keys: list[str], n: int, seed: int) -> list[str]:
    return sorted(np.random.default_rng(seed).choice(sorted(keys), size=n, replace=False).tolist())


def ring(tiles: set, have: set, k: int) -> set:
    out = set(tiles)
    for _ in range(k):
        out |= {(la + i, lo + j) for la, lo in out for i in (-1, 0, 1) for j in (-1, 0, 1) if (la + i, lo + j) in have}
    return out


def perturb(z: np.ndarray, rng) -> np.ndarray:
    return z + rng.normal(0.0, SIGMA_Z_M, z.shape).astype(z.dtype)      # NaN voids stay NaN


def change_shares(old: dict, new: dict) -> dict:
    """Shares of the same cells whose state and candidacy differ between the two assessments."""
    o = {c: (s, k) for c, s, k in zip(old["cell"].tolist(), old["state"], old["candidate"])}
    n = {c: (s, k) for c, s, k in zip(new["cell"].tolist(), new["state"], new["candidate"])}
    common = sorted(set(o) & set(n))
    if not common:
        return {"cells": 0, "state_changed": 0.0, "candidate_changed": 0.0}
    return {"cells": len(common),
            "state_changed": round(sum(o[c][0] != n[c][0] for c in common) / len(common), 6),
            "candidate_changed": round(sum(bool(o[c][1]) != bool(n[c][1]) for c in common) / len(common), 6)}


def threshold(state_shares: dict) -> float:
    worst = max(state_shares.values(), default=0.0)
    return 0.01 if worst < 0.01 else math.ceil(worst * 100 + 1e-9) / 100


def _features(tiles: list, real_cube: Path, cube: Path, cache: Path) -> dict:
    from discovery import cube as cb
    real_read = cb.read_dem

    def noisy(grid, product, have, cache_):
        z, shas = real_read(grid, product, have, cache_)
        rng = np.random.default_rng([SEED, grid.lat + 90, grid.lon + 180, int(grid.pixel_m)])
        return perturb(z, rng), shas

    cb.read_dem = noisy
    secs = {}
    try:
        for scale, px in SCALES.items():
            src, out = real_cube / scale, cube / scale
            listing = {tuple(map(int, k.split(","))): v for k, v in json.loads((src / "listing.json").read_text()).items()}
            wc = json.loads((src / "worldcover-listing.json").read_text())
            t0 = time.time()
            for la, lo in tiles:
                cb.process(la, lo, "glo90", px, out, listing, "calibration", wc, cache, "calibration", px * 25)
            secs[scale] = round(time.time() - t0, 1)
    finally:
        cb.read_dem = real_read
    return secs


def lambda_assess(args) -> int:
    from discovery.discover import assess_tile_to_file
    return assess_tile_to_file(*args)


def _states(cells: dict, targets: list[str]) -> dict:
    from discovery.discover import _candidate_index
    from discovery.release import coverage_class
    out = {}
    for t in targets:
        cand = np.zeros(len(cells["cell"]), bool)
        cand[_candidate_index(cells, "D", t, 0.5)] = True
        out[t] = {"cell": np.asarray(cells["cell"]).astype(np.int64), "state": coverage_class(cells, t), "candidate": cand}
    return out


def main(argv=None) -> int:
    import pyarrow.compute as pc
    import pyarrow.parquet as pq
    from discovery import discover as d
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--run", type=Path, default=Path("/data/run-mars-001"))
    ap.add_argument("--cube", type=Path, default=Path("/data/cube"))
    ap.add_argument("--cache", type=Path, default=Path("/data/copernicus-glo90"))
    ap.add_argument("--rock", default="/data/add-rock-outcrop/outcrops_200m_3031")
    ap.add_argument("--work", type=Path, default=Path("/data/calib-t52"))
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--workers", type=int, default=8)
    a = ap.parse_args(argv)
    keys = (a.run / "tiles-refine-glo90-463m-w25.txt").read_text().split()
    have = {tuple(map(int, k.split(","))) for k in keys}
    picked = sample(keys, N_TILES, SEED)
    tiles = [tuple(map(int, k.split(","))) for k in picked]
    report = {"rule": __doc__.split("\n\n")[1].replace("\n", " "), "tiles": picked, "seconds": {}}
    if a.work.exists():
        shutil.rmtree(a.work)
    cube, run = a.work / "cube", a.work / "run"
    t0 = time.time()
    from discovery.copernicus import tile_name
    for scale in SCALES:                                          # real files of two rings: what assess reads
        (cube / scale).mkdir(parents=True)
        for la, lo in ring(set(tiles), have, 2):
            for kind in ("windows", "cells"):
                f = a.cube / scale / f"{tile_name(la, lo, 'glo90')}.{kind}.parquet"
                if f.exists():
                    shutil.copy2(f, cube / scale / f.name)
    report["seconds"]["copy"] = round(time.time() - t0, 1)
    report["seconds"]["features"] = _features(tiles, a.cube, cube, a.cache)
    run.mkdir(parents=True)
    t0 = time.time()
    # every tile of the run is refined at both scales: the neighbours read their own neighbours as the run did
    refined = {f"{la},{lo}": sorted(SCALES) for la, lo in ring(set(tiles), have, 2)}
    assessed = sorted(f"{la},{lo}" for la, lo in ring(set(tiles), have, 1))
    import pyarrow as pa
    from concurrent.futures import ProcessPoolExecutor
    parts = run / "cells-parts"
    parts.mkdir(parents=True)
    with ProcessPoolExecutor(max_workers=a.workers) as pool:
        n_cells = sum(pool.map(lambda_assess, [(k, str(cube), str(a.run / "refs.npz"), a.rock, str(parts),
                                                {nk: refined[nk] for nk in d.neighbour_keys(k) if nk in refined})
                                               for k in assessed]))
    with pq.ParquetWriter(run / "cells.parquet", d.CELL_SCHEMA, compression="zstd") as w:
        for f in sorted(parts.glob("*.parquet")):
            w.write_table(pq.read_table(f, schema=d.CELL_SCHEMA))
    report["seconds"]["assess"] = round(time.time() - t0, 1)
    report["assess"] = {"tiles": len(assessed), "cells": n_cells}
    targets = sorted(d.TARGET_SCALE)
    cols = list(dict.fromkeys(list(d.LOAD_COLUMNS) + ["windows", "cover_unknown", "masked_share", "confidence"]
                              + [f"{t}:{k}" for t in targets for k in ("windows", "valid", "screened_out")]))
    new = d.load_cells(str(run / "cells.parquet"), cols)
    ids = new["cell"].astype(np.int64)
    real_t = pq.read_table(a.run / "cells.parquet", columns=cols)
    old_t = real_t.filter(pc.is_in(real_t.column("cell"), value_set=pa.array(new["cell"]).cast(real_t.column("cell").type)))
    old = {k: old_t.column(k).to_numpy(zero_copy_only=False) for k in old_t.column_names}
    so, sn = _states(old, targets), _states(new, targets)
    report["change"] = {t: change_shares(so[t], sn[t]) for t in targets}
    from discovery.zones_local import update_zones
    t0 = time.time()                                              # the run's candidate ids: the starting state
    cand_cols = ["cell", "masked_share", "confidence"] + [f"{t}:median" for t in targets]
    ct = real_t.select(cand_cols)
    del real_t
    allc = {k: ct.column(k).to_numpy(zero_copy_only=False) for k in ct.column_names}
    report["seconds"]["read_candidates"] = round(time.time() - t0, 1)
    zones, t0 = {}, time.time()
    for t in targets:
        cand_old = np.sort(np.asarray(allc["cell"])[d._candidate_index(allc, "D", t, d.TAU)].astype(np.int64))
        changed = {int(c): bool(n) for c, o, n in zip(so[t]["cell"].tolist(), so[t]["candidate"], sn[t]["candidate"])
                   if bool(o) != bool(n)}
        seen = set(so[t]["cell"].tolist())
        changed.update({int(c): bool(n) for c, n in zip(sn[t]["cell"].tolist(), sn[t]["candidate"]) if int(c) not in seen})
        old_z = json.loads((a.run / f"zones-D-{t}.json").read_text())
        old_z = old_z["zones"] if isinstance(old_z, dict) else old_z
        tz = time.time()
        old_ids = [[int(c) for c in z["cell_ids"]] for z in old_z]
        newz, _, st = update_zones(old_ids, cand_old, changed, d.MIN)
        before, after = {frozenset(z) for z in old_ids}, {frozenset(z) for z in newz}
        zones[t] = {"before": len(before), "changed_cells": len(changed), "appear": len(after - before),
                    "disappear": len(before - after), "seconds": round(time.time() - tz, 2), **st}
    report["seconds"]["zones_local"] = round(time.time() - t0, 1)
    report["zones"] = zones
    report["threshold"] = threshold({t: c["state_changed"] for t, c in report["change"].items()})
    a.out.write_text(json.dumps(report, indent=1) + "\n")
    print(json.dumps({k: report[k] for k in ("seconds", "change", "zones", "threshold")}, indent=1))
    return 0


if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    sys.exit(main())
