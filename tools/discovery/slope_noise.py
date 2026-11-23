"""Slope noise of a window from the stated DEM error (protocol mars-v2, decided by David on 23/11/2026).

Rule fixed before measuring: at each comparison pixel, the elevation gets an independent Gaussian error with the
stated relative vertical accuracy of Copernicus DEM (2 m LE90 for slopes up to 20%, catalogue `copernicus-dem-glo30`,
the same for GLO-90), that is sigma 1.216 m. The window slope noise is the root mean square of the change of the
window mean slope (bias included), over the windows of 30 land tiles drawn with seed 20261119, 3 draws per tile,
rounded up to 0.01 degree. Independent errors at the comparison pixel are conservative: the 90 m errors of the
source are averaged when resampled to 115 or 463 m.

    PYTHONPATH=tools python tools/discovery/slope_noise.py --tiles /data/run-mars-001/tiles-refine-glo90-115m-w25.txt \
        --cache /data/copernicus-glo90 --out data/runs/run-mars-001/slope-noise.json
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

SEED, TILES, DRAWS = 20261119, 30, 3
LE90_M = 2.0                                       # relative vertical accuracy, slopes up to 20% (catalogue)
PIXELS = {"glo90-115m-w25": 115.77, "glo90-463m-w25": 463.08}
WINDOW_PX = 25


def sigma_from_le90(le90: float) -> float:
    """Gaussian sigma of a stated 90% linear error."""
    return le90 / 1.6449


def window_slope_noise(z: np.ndarray, pixel_m: float, window_px: int, sigma_z: float, rng, draws: int,
                       margin: int = 1) -> np.ndarray:
    """Change of the mean slope of every valid window when the elevation gets independent Gaussian errors."""
    from discovery.windows import window_metrics_grid
    clean = window_metrics_grid(z, pixel_m, window_px, margin, metrics=("slope_mean",))["slope_mean"]
    out = []
    for _ in range(draws):
        noisy = window_metrics_grid(z + rng.normal(0.0, sigma_z, z.shape), pixel_m, window_px, margin,
                                    metrics=("slope_mean",))["slope_mean"]
        d = (noisy - clean).ravel()
        out.append(d[np.isfinite(d)])
    return np.concatenate(out)


def measure(tiles_file: Path, cache: Path) -> dict:
    from discovery.cube import read_dem
    from discovery.grid import tile_grid
    keys = sorted(tiles_file.read_text().split())
    pick = sorted(np.random.default_rng(SEED).choice(keys, size=TILES, replace=False).tolist())
    have = {tuple(int(v) for v in k.split(",")) for k in keys}       # (lat, lon) of every land tile
    sz = sigma_from_le90(LE90_M)
    out = {"rule": __doc__.split("\n\n")[1].replace("\n", " "), "le90_m": LE90_M, "sigma_z_m": round(sz, 4),
           "tiles": pick, "scales": {}}
    for k, (scale, px) in enumerate(PIXELS.items()):
        rng = np.random.default_rng([SEED, k])
        diffs = []
        for key in pick:
            la, lo = (int(v) for v in key.split(","))
            grid = tile_grid(la, lo, px, px * WINDOW_PX)
            z, _ = read_dem(grid, "glo90", have, cache)
            diffs.append(window_slope_noise(z, px, WINDOW_PX, sz, rng, DRAWS, grid.margin_px))
        d = np.concatenate(diffs)
        rms = float(np.sqrt(np.mean(d ** 2)))
        out["scales"][scale] = {"windows": int(d.size), "rms_deg": round(rms, 4), "mean_deg": round(float(d.mean()), 4),
                                "p95_abs_deg": round(float(np.percentile(np.abs(d), 95)), 4),
                                "sigma_deg": math.ceil(rms * 100) / 100}
    return out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--tiles", type=Path, required=True)
    ap.add_argument("--cache", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    a = ap.parse_args(argv)
    res = measure(a.tiles, a.cache)
    a.out.write_text(json.dumps(res, indent=1) + "\n")
    print(json.dumps(res["scales"], indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
