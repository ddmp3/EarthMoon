"""v2 regression anchor for the v3 window metrics (T40).

`build` (network) stores, for the 37 v2 sites, the exact 77 x 77 local grids v2 read (Copernicus GLO-30 on a
40 m azimuthal equidistant grid, tools/precompute/site_terrain.py) in data/fixtures/v2-site-grids.npz.
The test test_anchor_v2.py then recomputes the v2 values and sigmas from these grids with the v3 code, offline.

    python tools/discovery/anchor_v2.py build
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
FIXTURE = ROOT / "data" / "fixtures" / "v2-site-grids.npz"
DATASET = ROOT / "data" / "dataset-v2.json"
GRID_PX = 77          # 3 x 3 windows of 25 px plus a 1 px margin, as in site_terrain.py


def v2_values(site: dict) -> dict:
    return {k: v for k, v in site["values"].items()}


def recompute(z: np.ndarray) -> dict:
    """v2 'value' (central window) and 'sigma' (1.4826 MAD over the 9 windows) with the v3 window code."""
    sys.path.insert(0, str(ROOT / "tools"))
    from discovery.windows import ALL_METRICS, window_metrics_grid
    w = window_metrics_grid(z.astype("float64"), 40.0, 25, margin=1, metrics=ALL_METRICS)
    out = {}
    for k in ALL_METRICS:
        v = w[k].ravel()
        centre = v[4]
        finite = v[np.isfinite(v)]
        sigma = float(1.4826 * np.median(np.abs(finite - np.median(finite)))) if finite.size >= 3 else None
        out[k] = {"value": None if not np.isfinite(centre) else round(float(centre), 3),
                  "sigma": None if sigma is None else round(sigma, 3)}
    return out


def build() -> int:
    sys.path.insert(0, str(ROOT / "tools" / "precompute"))
    from site_terrain import read_local_grid
    sites = json.loads(DATASET.read_text(encoding="utf-8"))["sites"]
    grids = {}
    for sid, s in sites.items():
        grids[sid] = read_local_grid(float(s["lat"]), float(s["lon"]), GRID_PX).astype("float32")
        print(sid, flush=True)
    FIXTURE.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(FIXTURE, **grids)
    print(FIXTURE, FIXTURE.stat().st_size, "bytes")
    return 0


if __name__ == "__main__":
    sys.exit(build() if sys.argv[1:] == ["build"] else 2)
