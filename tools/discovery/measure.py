"""Measurements of T40 before any global run (ADR-007).

    python tools/discovery/measure.py tiles --listing L.json --out tiles-100.txt     # 100 random land tiles
    python tools/discovery/measure.py pilot --out tiles-pilot.txt                     # the 13 T22 pilot tiles
    python tools/discovery/measure.py timing --manifest M.jsonl --listing L.json --pass-share 0.48 --workers 8
    python tools/discovery/measure.py summary --manifest M.jsonl                       # run report numbers
    python tools/discovery/measure.py equivalence --a DIR_GLO90 --b DIR_GLO30_AT_90 --tiles tiles-pilot.txt
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
SEED_100 = 20261120


def pick(seed: int, n: int, have: set) -> list[tuple[int, int]]:
    """n distinct existing 1° tiles drawn with probability proportional to area (as T22)."""
    rng = np.random.default_rng(seed)
    out: list[tuple[int, int]] = []
    while len(out) < n:
        t = (math.floor(math.degrees(math.asin(rng.uniform(-1, 1)))), int(rng.integers(-180, 180)))
        if t in have and t not in out:
            out.append(t)
    return out


def projection(records: list[dict], workers: int, n_tiles: int, share: float) -> dict:
    """Hours for n_tiles x share from the measured per-tile wall time with `workers` parallel processes."""
    total = np.array([r["seconds"]["total"] for r in records])
    per_tile = float(np.median(total))
    hours = n_tiles * share * per_tile / workers / 3600
    return {"tiles_measured": len(records), "median_s": round(per_tile, 2), "p90_s": round(float(np.percentile(total, 90)), 2),
            "read_median_s": round(float(np.median([r["seconds"]["read"] for r in records])), 2),
            "mask_median_s": round(float(np.median([r["seconds"]["mask"] for r in records])), 2),
            "workers": workers, "tiles": n_tiles, "share": share, "projected_hours": round(hours, 1)}


def summary(records: list[dict]) -> dict:
    """Run report of a manifest: the latest record per tile (a rerun appends), coverage counts and shares, timings."""
    last = {r["tile"]: r for r in records}
    recs = list(last.values())
    cells = {k: sum(r["cells"][k] for r in recs) for k in ("evaluated", "partial", "missing")}
    total = sum(cells.values())
    t = np.array([r["seconds"]["total"] for r in recs]) if recs else np.array([np.nan])
    return {"tiles": len(recs), "code": sorted({r["code"] for r in recs}),
            "commits": sorted({r.get("commit", "") for r in recs}),
            "cells": {**cells, "total": total},
            "cell_shares": {k: round(v / total, 4) if total else None for k, v in cells.items()},
            "windows": {"total": sum(r["windows"] for r in recs), "valid": sum(r["valid_windows"] for r in recs)},
            "seconds": {"median_total": round(float(np.median(t)), 2), "p90_total": round(float(np.percentile(t, 90)), 2),
                        "sum_total_h": round(float(t.sum()) / 3600, 2)}}


def equivalence(a: Path, b: Path, names: list[tuple[str, str]]) -> dict:
    """Same windows, slope_mean from two products on the same grid: median ratio, Spearman, |diff| quantiles."""
    import pyarrow.parquet as pq
    xs, ys = [], []
    for na, nb in names:
        ta = pq.read_table(a / f"{na}.windows.parquet", columns=["row", "col", "slope_mean"]).to_pydict()
        tb = pq.read_table(b / f"{nb}.windows.parquet", columns=["row", "col", "slope_mean"]).to_pydict()
        mb = {(r, c): v for r, c, v in zip(tb["row"], tb["col"], tb["slope_mean"])}
        for r, c, v in zip(ta["row"], ta["col"], ta["slope_mean"]):
            w = mb.get((r, c))
            if w is not None and np.isfinite(v) and np.isfinite(w) and w > 0:
                xs.append(w)
                ys.append(v)
    x, y = np.array(xs), np.array(ys)
    rx, ry = np.argsort(np.argsort(x)), np.argsort(np.argsort(y))
    d = np.abs(y - x)
    return {"windows": int(x.size), "median_ratio_glo90_over_glo30": round(float(np.median(y / x)), 3),
            "spearman": round(float(np.corrcoef(rx, ry)[0, 1]), 4),
            "abs_diff_deg": {"median": round(float(np.median(d)), 3), "p95": round(float(np.percentile(d, 95)), 3)}}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("what", choices=["tiles", "pilot", "timing", "equivalence", "summary"])
    ap.add_argument("--listing")
    ap.add_argument("--manifest")
    ap.add_argument("--out")
    ap.add_argument("--workers", type=int, default=8)
    ap.add_argument("--pass-share", type=float, default=0.48)
    ap.add_argument("--a")
    ap.add_argument("--b")
    ap.add_argument("--tiles")
    a = ap.parse_args(argv)
    if a.what == "tiles":
        have = {tuple(map(int, k.split(","))) for k in json.loads(Path(a.listing).read_text())}
        Path(a.out).write_text("\n".join(f"{la},{lo}" for la, lo in pick(SEED_100, 100, have)) + "\n")
    elif a.what == "pilot":
        t22 = json.loads((ROOT / "data/research/sampling-t22.json").read_text(encoding="utf-8"))
        Path(a.out).write_text("\n".join(f"{t['lat']},{t['lon']}" for t in t22["tiles"]) + "\n")
    elif a.what == "summary":
        recs = [json.loads(x) for x in Path(a.manifest).read_text().splitlines() if x.strip()]
        print(json.dumps(summary(recs), indent=1))
    elif a.what == "timing":
        recs = [json.loads(x) for x in Path(a.manifest).read_text().splitlines() if x.strip()]
        n = len(json.loads(Path(a.listing).read_text()))
        print(json.dumps(projection(recs, a.workers, n, a.pass_share), indent=1))
    else:
        sys.path.insert(0, str(ROOT / "tools"))
        from discovery.copernicus import tile_name
        tiles = [tuple(map(int, x.split(","))) for x in Path(a.tiles).read_text().split()]
        names = [(tile_name(*t, "glo90"), tile_name(*t, "glo30")) for t in tiles]
        print(json.dumps(equivalence(Path(a.a), Path(a.b), names), indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
