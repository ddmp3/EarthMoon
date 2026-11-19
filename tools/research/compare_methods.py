"""Comparison methods benchmark of task T23 (protocol in docs/wiki/methods/comparison.md, fixed before the run).

    python tools/research/compare_methods.py --ldem /data/lola/ldem_85s_40m.img --cache /data/copernicus

Every candidate gives a typicality in [0, 1]: 1 for a window like the median planetary window, near 0 for a
window that almost no planetary window resembles. Missing values are never scored.
"""
from __future__ import annotations

import argparse
import json
import math
import sys
import time
from pathlib import Path

import numpy as np

SEED = 20261119

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from discovery.compare import interval_score, percentile_typicality  # noqa: E402,F401  (moved in T42)


# --- candidates (tested) ----------------------------------------------------------------------------------

def robust_location_scatter(ref: np.ndarray, keep: float = 0.75, steps: int = 10) -> tuple[np.ndarray, np.ndarray]:
    """Location and scatter of the `keep` most central reference points (concentration steps, as in MCD)."""
    x = np.asarray(ref, dtype="float64")
    loc, cov = np.median(x, axis=0), np.cov(x, rowvar=False)
    for _ in range(steps):
        d = _maha(x, loc, cov)
        sub = x[d <= np.quantile(d, keep)]
        loc, cov = sub.mean(axis=0), np.cov(sub, rowvar=False)
    return loc, cov


def _maha(x, loc, cov):
    inv = np.linalg.pinv(np.atleast_2d(cov))
    diff = np.atleast_2d(x) - loc
    return np.sqrt(np.einsum("ij,jk,ik->i", diff, inv, diff))


def mahalanobis_typicality(x, ref, loc, cov) -> np.ndarray:
    """Share of reference points farther from the centre than x."""
    dref = np.sort(_maha(ref, loc, cov))
    return 1 - np.searchsorted(dref, _maha(x, loc, cov), "right") / len(dref)


def _scale(ref):
    med = np.median(ref, axis=0)
    iqr = np.subtract(*np.percentile(ref, [75, 25], axis=0))
    return med, np.where(iqr > 0, iqr, 1.0)


def _kdist(q, ref, k, chunk=2000):
    out = np.empty(len(q))
    for i in range(0, len(q), chunk):
        d = np.sqrt(((q[i:i + chunk, None, :] - ref[None, :, :]) ** 2).sum(-1))
        out[i:i + chunk] = np.partition(d, k - 1, axis=1)[:, k - 1]
    return out


def knn_typicality(x, ref, calib, k: int = 10) -> np.ndarray:
    """Share of calibration (held-out planetary) points whose k-th neighbour distance is larger than x's."""
    med, iqr = _scale(ref)
    z = lambda a: (np.atleast_2d(a) - med) / iqr
    dcal = np.sort(_kdist(z(calib), z(ref), k))
    return 1 - np.searchsorted(dcal, _kdist(z(x), z(ref), k), "right") / len(dcal)


def wasserstein_1d(a, b, n: int = 200) -> float:
    q = (np.arange(n) + 0.5) / n
    return float(np.mean(np.abs(np.quantile(a, q) - np.quantile(b, q))))


def energy_distance(a, b) -> float:
    a, b = np.atleast_2d(a).astype(float), np.atleast_2d(b).astype(float)
    if a.shape[0] == 1 and a.shape[1] > 1 and b.shape[1] == 1:
        a = a.T
    d = lambda u, v: np.sqrt(((u[:, None, :] - v[None, :, :]) ** 2).sum(-1)).mean()
    return float(2 * d(a, b) - d(a, a) - d(b, b))


def ks_uniform(t) -> float:
    t = np.sort(np.asarray(t))
    n = len(t)
    return float(max(np.max(np.arange(1, n + 1) / n - t), np.max(t - np.arange(n) / n)))


def auc(pos, neg) -> float:
    """P(pos > neg) + 0.5 P(pos = neg)."""
    allv = np.concatenate([pos, neg])
    order = allv.argsort(kind="mergesort")
    ranks = np.empty(len(allv))
    ranks[order] = np.arange(1, len(allv) + 1)
    _, inv, cnt = np.unique(allv, return_inverse=True, return_counts=True)
    ranks = (np.bincount(inv, weights=ranks) / cnt)[inv]
    return float((ranks[: len(pos)].sum() - len(pos) * (len(pos) + 1) / 2) / (len(pos) * len(neg)))


def spearman(a, b) -> float:
    ra, rb = np.argsort(np.argsort(a)), np.argsort(np.argsort(b))
    return float(np.corrcoef(ra, rb)[0, 1])


# --- features from data -----------------------------------------------------------------------------------

def features_from_grid(z: np.ndarray, valid: np.ndarray | None = None, block_offset: int = 0) -> np.ndarray:
    """Rows (slope_mean 1 km at 40 m, slope_regional 5 km at 200 m, block id) for a 40 m grid.
    The 5 km window encloses exactly 5 x 5 windows of 1 km (25 px of 40 m = 5 px of 200 m)."""
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from sampling import block_mean, window_slope_means
    s1 = window_slope_means(z, 40.0, 1000.0)
    s5 = window_slope_means(block_mean(z, 5), 200.0, 5000.0)
    rows = []
    for r in range(s5.shape[0] * 5):
        for c in range(s5.shape[1] * 5):
            if r >= s1.shape[0] or c >= s1.shape[1]:
                continue
            if valid is not None and not valid[r, c]:
                continue
            a, b = s1[r, c], s5[r // 5, c // 5]
            if np.isfinite(a) and np.isfinite(b):
                rows.append((a, b, block_offset + (r // 5) * 1000 + (c // 5)))
    return np.array(rows)


def run(args) -> dict:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "precompute"))
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from lunar_reference import latitude_grid, read_ldem
    from sampling import contrast_rows, local_grid, pick_land_tiles, tile_name
    rng = np.random.default_rng(SEED)

    z = read_ldem(args.ldem, 7584)
    lat = latitude_grid(7584, 40.0)
    n1 = 7584 // 25
    inside = (lat[: n1 * 25, : n1 * 25] <= -85.0).reshape(n1, 25, n1, 25).all(axis=(1, 3))
    moon = features_from_grid(z.astype("float64"), inside)
    perm = rng.permutation(len(moon))
    ref, held = moon[perm[: len(moon) // 2]], moon[perm[len(moon) // 2:]]

    cache = Path(args.cache)
    tiles = sorted(p for p in cache.glob("*.tif"))
    earth_parts = []
    for ti, p in enumerate(tiles):
        import re
        m = re.search(r"_([NS])(\d{2})_00_([EW])(\d{3})_00_DEM", p.stem)
        la = int(m.group(2)) * (1 if m.group(1) == "N" else -1)
        lo = int(m.group(4)) * (1 if m.group(3) == "E" else -1)
        earth_parts.append(features_from_grid(local_grid(p, la, lo, 40.0).astype("float64"), block_offset=(ti + 1) * 10_000_000))
    earth_all = np.vstack(earth_parts)
    earth = earth_all[rng.choice(len(earth_all), size=min(20000, len(earth_all)), replace=False)]
    t21 = json.loads(Path("data/research/redundancy-t21.json").read_text(encoding="utf-8"))["earth_rows"]
    earth_random_1d = np.array([r["slope_mean"] for r in t21])

    q = {f"p{p}": float(np.percentile(ref[:, 0], p)) for p in (5, 25, 75, 95)}
    loc, cov = robust_location_scatter(ref[:, :2])
    ref_knn = ref[rng.choice(len(ref), 5000, replace=False), :2]
    calib = held[rng.choice(len(held), 5000, replace=False), :2]
    held_eval = held[rng.choice(len(held), 5000, replace=False)]

    methods = {
        "interval_v2_1d": lambda x: interval_score(x[:, 0], q),
        "percentile_1d": lambda x: percentile_typicality(x[:, 0], ref[:, 0]),
        "mahalanobis_2d": lambda x: mahalanobis_typicality(x[:, :2], ref[:, :2], loc, cov),
        "knn_2d": lambda x: knn_typicality(x[:, :2], ref_knn, calib, 10),
    }
    out = {"seed": SEED, "moon_windows": len(moon), "earth_pilot_windows": len(earth_all),
           "redundancy_spearman": {"moon": round(spearman(moon[:, 0], moon[:, 1]), 3),
                                   "earth_pilot": round(spearman(earth_all[:, 0], earth_all[:, 1]), 3)},
           "methods": {}}
    for name, f in methods.items():
        t0 = time.time()
        th = f(held_eval)
        te = f(earth)
        dt = (time.time() - t0) / (len(held_eval) + len(earth)) * 1e6
        noisy = {s: round(spearman(te, f(earth + np.column_stack([rng.normal(0, s, len(earth)), np.zeros(len(earth)), np.zeros(len(earth))]))), 3)
                 for s in (0.5, 1.0)}
        res = {"held_mean": round(float(np.mean(th)), 3), "ks_uniform": round(ks_uniform(th), 3),
               "auc_vs_pilot": round(auc(th, te), 3), "earth_mean": round(float(np.mean(te)), 3),
               "noise_spearman": noisy, "seconds_per_million": round(dt, 2)}
        if name.endswith("_1d"):
            res["auc_vs_t21_random"] = round(auc(th, f(np.column_stack([earth_random_1d, np.zeros_like(earth_random_1d), np.zeros_like(earth_random_1d)]))), 3)
        if name.endswith("_2d"):
            drop = earth.copy()
            drop[:, 1] = np.median(ref[:, 1])  # regional feature removed: replaced by the reference median
            res["missing_regional_spearman"] = round(spearman(te, f(drop)), 3)
        out["methods"][name] = res
        print(name, res, flush=True)

    # zone methods: 5 km blocks of at least 20 windows. Split by block (not by window) into three groups:
    # reference windows, calibration blocks and held-out blocks, so no window is shared.
    def blocks(rows):
        ids, inv = np.unique(rows[:, 2], return_inverse=True)
        counts = np.bincount(inv)
        return {ids[i]: rows[inv == i, 0] for i in np.nonzero(counts >= 20)[0]}
    mblocks = blocks(moon)
    keys = rng.permutation(list(mblocks))
    third = len(keys) // 3
    ref_sample = np.concatenate([mblocks[k] for k in keys[:third]])
    ref_sample = ref_sample[rng.choice(len(ref_sample), 1000, replace=False)]
    cal_keys = keys[third:2 * third][:300]
    held_keys = keys[2 * third:][:300]
    eblocks = blocks(earth_all)
    ekeys = rng.permutation(list(eblocks))[:300]
    mb = [mblocks[k] for k in cal_keys] + [mblocks[k] for k in held_keys]
    eb = [eblocks[k] for k in ekeys]
    for name, dist in (("wasserstein_zone", lambda b: wasserstein_1d(b, ref_sample)),
                       ("energy_zone", lambda b: energy_distance(b[:, None], ref_sample[:, None]))):
        t0 = time.time()
        half = len(cal_keys)
        cal = np.sort([dist(b) for b in mb[:half]])
        typ = lambda bs: 1 - np.searchsorted(cal, [dist(b) for b in bs], "right") / len(cal)
        th, te = typ(mb[half:]), typ(eb)
        dt = (time.time() - t0) / (len(mb) + len(eb)) * 1e6
        res = {"held_mean": round(float(np.mean(th)), 3), "ks_uniform": round(ks_uniform(th), 3),
               "auc_vs_pilot": round(auc(th, te), 3), "earth_mean": round(float(np.mean(te)), 3),
               "noise_spearman": {s: round(spearman(te, typ([b + rng.normal(0, s, len(b)) for b in eb])), 3) for s in (0.5, 1.0)},
               "seconds_per_million": round(dt, 2), "blocks": {"moon_calibration": half, "moon_held": len(mb) - half, "earth": len(eb)}}
        out["methods"][name] = res
        print(name, res, flush=True)
    out["date"] = time.strftime("%Y-%m-%d")
    return out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--ldem", required=True)
    ap.add_argument("--cache", required=True)
    ap.add_argument("--out", default="data/research/comparison-t23.json")
    a = ap.parse_args(argv)
    res = run(a)
    Path(a.out).write_text(json.dumps(res, indent=1, default=lambda o: o.item() if hasattr(o, "item") else str(o)) + "\n",
                           encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
