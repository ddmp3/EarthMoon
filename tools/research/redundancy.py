"""Redundancy of the terrain parameters on real data, Moon and Earth (task T21, finding L1).

    python tools/research/redundancy.py --ldem ~/earthmoon-data/lola/ldem_85s_40m.img \
        --earth-n 4000 --seed 20261118 --out data/research/redundancy-t21.json

Moon: every 1 km window of LOLA LDEM_85S_40M south of 85°S (the v2 reference, same code).
Earth: points drawn uniformly on the sphere with a fixed seed; at each, one 1 km window of Copernicus GLO-30
resampled to 40 m (the v2 Earth code). Ocean points have no tile and are counted, not scored. Windows with less
than 90% valid pixels are counted as incomplete. Missing is never replaced by a value.

Pearson, Spearman and partial correlations (from the pseudo-inverse of the Pearson matrix) are computed on
complete rows. On Earth, exactly flat windows (edited water bodies, ice sheets, salt flats) are reported, and the
matrices are given with and without them.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Callable

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "precompute"))
from terrain_metrics import METRIC_KEYS, PIXEL_M, WINDOW_PX, slope_deg, window_metrics  # noqa: E402

KEYS = list(METRIC_KEYS)
MARGIN_PX = 1


def complete_rows(rows: list[dict], keys: list[str]) -> tuple[list[dict], int]:
    kept = [r for r in rows if all(r.get(k) is not None and math.isfinite(r[k]) for k in keys)]
    return kept, len(rows) - len(kept)


def _ranks(x: np.ndarray) -> np.ndarray:
    """Average ranks (ties share their mean rank)."""
    order = np.argsort(x, kind="mergesort")
    ranks = np.empty(len(x), dtype="float64")
    ranks[order] = np.arange(len(x), dtype="float64")
    _, inv, counts = np.unique(x, return_inverse=True, return_counts=True)
    sums = np.bincount(inv, weights=ranks)
    return (sums / counts)[inv]


def _corr(m: np.ndarray) -> np.ndarray:
    sd = m.std(axis=0)
    with np.errstate(invalid="ignore", divide="ignore"):
        r = np.corrcoef(m, rowvar=False)
    r[:, sd == 0] = np.nan
    r[sd == 0, :] = np.nan
    np.fill_diagonal(r, 1.0)
    return r


def correlations(rows: list[dict], keys: list[str]) -> dict:
    kept, dropped = complete_rows(rows, keys)
    m = np.array([[r[k] for k in keys] for r in kept], dtype="float64")
    pearson = _corr(m)
    spearman = _corr(np.column_stack([_ranks(m[:, j]) for j in range(m.shape[1])]))
    return {"keys": keys, "n": len(kept), "dropped": dropped, "pearson": _round(pearson),
            "spearman": _round(spearman), "partial": _round(np.array(partial_correlations(pearson)))}


def partial_correlations(r) -> list[list[float]]:
    """Correlation of each pair given all the others, from the pseudo-inverse of the correlation matrix."""
    r = np.nan_to_num(np.asarray(r, dtype="float64"))
    p = np.linalg.pinv(r)
    d = np.sqrt(np.abs(np.diag(p)))
    out = -p / np.outer(d, d)
    np.fill_diagonal(out, 1.0)
    return out.tolist()


def _round(m: np.ndarray) -> list[list[float | None]]:
    return [[None if not np.isfinite(v) else round(float(v), 3) for v in row] for row in np.asarray(m)]


def redundant_pairs(matrix, keys: list[str], threshold: float = 0.8) -> list[tuple[str, str, float]]:
    out = []
    for i in range(len(keys)):
        for j in range(i + 1, len(keys)):
            v = matrix[i][j]
            if v is not None and abs(v) > threshold:
                out.append((keys[i], keys[j], v))
    return out


def random_points(seed: int, n: int) -> list[tuple[float, float]]:
    """Points uniform on the sphere (equal area), reproducible from the seed."""
    rng = np.random.default_rng(seed)
    lat = np.degrees(np.arcsin(rng.uniform(-1, 1, n)))
    lon = rng.uniform(-180, 180, n)
    return [(round(float(a), 5), round(float(o), 5)) for a, o in zip(lat, lon)]


def _one_window(z: np.ndarray) -> dict:
    slope = slope_deg(z, PIXEL_M)
    sl = (slice(MARGIN_PX, MARGIN_PX + WINDOW_PX), slice(MARGIN_PX, MARGIN_PX + WINDOW_PX))
    return window_metrics(z[sl], slope[sl])


def earth_sample(points: list[tuple[float, float]], reader: Callable, workers: int = 1) -> dict:
    def measure(pt):
        try:
            z = reader(pt[0], pt[1], WINDOW_PX + 2 * MARGIN_PX)
        except LookupError:
            return pt, None
        return pt, _one_window(np.asarray(z, dtype="float64"))

    with ThreadPoolExecutor(max_workers=workers) as pool:
        results = list(pool.map(measure, points))
    rows, no_tile, incomplete = [], 0, 0
    for (lat, lon), w in results:
        if w is None:
            no_tile += 1
        elif w["slope_mean"] is None:
            incomplete += 1
        else:
            rows.append({"lat": lat, "lon": lon, **{k: round(w[k], 4) for k in KEYS},
                         "flat": w["slope_max"] < 1e-6})
    return {"attempted": len(points), "no_tile": no_tile, "incomplete": incomplete, "rows": rows}


def moon_rows(path: str) -> tuple[list[dict], str]:
    from lunar_reference import latitude_grid, read_ldem
    from terrain_metrics import grid_metrics
    z = read_ldem(path, 7584)
    windows = grid_metrics(z, PIXEL_M, WINDOW_PX, latitude_grid(7584, PIXEL_M) <= -85.0)
    with open(path, "rb") as fh:
        digest = hashlib.sha256(fh.read()).hexdigest()
    return windows, digest


def _table(m, keys) -> list[str]:
    short = [k.replace("roughness_detrended", "rough_detr").replace("traversable_", "trav_") for k in keys]
    lines = ["| | " + " | ".join(short) + " |", "|---" * (len(keys) + 1) + "|"]
    for name, row in zip(short, m):
        lines.append(f"| {name} | " + " | ".join("" if v is None else f"{v:.2f}" for v in row) + " |")
    return lines


def report(result: dict) -> str:
    lines = ["# Terrain parameter redundancy (T21)", "",
             f"Generated by `tools/research/redundancy.py` on {result['date']}. Data: `data/research/redundancy-t21.json`. "
             "Do not edit by hand.", ""]
    for label, block in result["matrices"].items():
        lines += [f"## {label}", "", f"n = {block['n']} complete windows ({block['dropped']} dropped).", ""]
        for kind in ("spearman", "pearson", "partial"):
            pairs = redundant_pairs(block[kind], block["keys"])
            lines += [f"**{kind.capitalize()}**, pairs with |r| > 0.8: "
                      + (", ".join(f"{a}/{b} {v:+.2f}" for a, b, v in pairs) or "none"), ""]
        lines += ["Spearman matrix:", ""] + _table(block["spearman"], block["keys"]) + [""]
    s = result["earth_sample"]
    lines += ["## Sampling", "",
              f"- Moon: LDEM_85S_40M, SHA-256 `{result['moon_sha256'][:12]}…`, windows south of 85°S.",
              f"- Earth: seed {s['seed']}, {s['attempted']} points uniform on the sphere; {s['no_tile']} without a "
              f"Copernicus tile (ocean), {s['incomplete']} incomplete windows, {s['kept']} windows kept, "
              f"{s['flat']} exactly flat.", ""]
    return "\n".join(lines)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--ldem", required=True)
    ap.add_argument("--earth-n", type=int, default=4000)
    ap.add_argument("--seed", type=int, default=20261118)
    ap.add_argument("--workers", type=int, default=8)
    ap.add_argument("--out", default="data/research/redundancy-t21.json")
    ap.add_argument("--report", default="docs/wiki/methods/redundancy.md")
    a = ap.parse_args(argv)
    os.environ.setdefault("GDAL_DISABLE_READDIR_ON_OPEN", "EMPTY_DIR")
    from site_terrain import read_local_grid

    moon, sha = moon_rows(a.ldem)
    earth = earth_sample(random_points(a.seed, a.earth_n), read_local_grid, a.workers)
    not_flat = [r for r in earth["rows"] if not r["flat"]]
    result = {
        "date": __import__("time").strftime("%Y-%m-%d"), "moon_sha256": sha, "keys": KEYS,
        "earth_sample": {"seed": a.seed, "attempted": earth["attempted"], "no_tile": earth["no_tile"],
                         "incomplete": earth["incomplete"], "kept": len(earth["rows"]),
                         "flat": len(earth["rows"]) - len(not_flat)},
        "matrices": {"Moon, south polar cap (all windows)": correlations(moon, KEYS),
                     "Earth, random land windows": correlations(earth["rows"], KEYS),
                     "Earth, random land windows without exactly flat ones": correlations(not_flat, KEYS)},
        "earth_rows": earth["rows"],
    }
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    Path(a.out).write_text(json.dumps(result, indent=1) + "\n", encoding="utf-8")
    Path(a.report).write_text(report(result), encoding="utf-8")
    print(json.dumps(result["earth_sample"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
