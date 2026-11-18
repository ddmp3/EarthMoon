"""Negative controls of the v3 validation protocol (task T25).

    python tools/research/controls.py          # writes data/validation/negatives.yaml

Rule (docs/VALIDATION_PROTOCOL.md): points drawn uniformly on the sphere with seed 20261119, in draw order,
kept when their ESA WorldCover 2021 class is one where vegetation, buildings or water hide the ground; 3 per
class. Classes from the legend stored in the WorldCover files themselves. No point is chosen by hand.
"""
from __future__ import annotations

import math
import sys
from pathlib import Path
from typing import Callable

import numpy as np

SEED = 20261119
NEGATIVE_CLASSES = {10: "Tree cover", 40: "Cropland", 50: "Built-up", 80: "Permanent water bodies", 90: "Herbaceous wetland", 95: "Mangroves"}
BASE = "https://esa-worldcover.s3.eu-central-1.amazonaws.com/v200/2021/map"


def worldcover_tile(lat: float, lon: float) -> str:
    la, lo = math.floor(lat / 3) * 3, math.floor(lon / 3) * 3
    return f"{'N' if la >= 0 else 'S'}{abs(la):02d}{'E' if lo >= 0 else 'W'}{abs(lo):03d}"


def draw_negatives(points, classify: Callable[[float, float], int | None], per_class: int = 3,
                   workers: int = 1, batch: int = 64) -> list[dict]:
    """Keep points in draw order; classification may run in parallel batches (the result is the same)."""
    from concurrent.futures import ThreadPoolExecutor
    out, count = [], {c: 0 for c in NEGATIVE_CLASSES}
    with ThreadPoolExecutor(max_workers=workers) as pool:
        for start in range(0, len(points), batch):
            chunk = points[start:start + batch]
            classes = list(pool.map(lambda p: classify(*p), chunk))
            for (lat, lon), c in zip(chunk, classes):
                if c in count and count[c] < per_class:
                    count[c] += 1
                    out.append({"lat": lat, "lon": lon, "class": c, "class_name": NEGATIVE_CLASSES[c]})
                    if all(v == per_class for v in count.values()):
                        return out
            print(start + len(chunk), count, flush=True)
    return out


def classify_remote(lat: float, lon: float) -> int | None:
    import rasterio
    from rasterio.errors import RasterioIOError
    try:
        with rasterio.open(f"{BASE}/ESA_WorldCover_10m_2021_v200_{worldcover_tile(lat, lon)}_Map.tif") as src:
            row, col = src.index(lon, lat)
            return int(src.read(1, window=((row, row + 1), (col, col + 1)))[0, 0])
    except RasterioIOError:
        return None  # no tile: ocean


def main() -> int:
    import os
    import yaml
    os.environ.setdefault("GDAL_DISABLE_READDIR_ON_OPEN", "EMPTY_DIR")
    os.environ.setdefault("CPL_VSIL_CURL_ALLOWED_EXTENSIONS", ".tif")
    rng = np.random.default_rng(SEED)
    n = 100000
    pts = [(round(float(a), 5), round(float(o), 5))
           for a, o in zip(np.degrees(np.arcsin(rng.uniform(-1, 1, n))), rng.uniform(-180, 180, n))]
    negatives = draw_negatives(pts, classify_remote, workers=32)
    out = {"rule": "uniform points on the sphere, seed 20261119, draw order, ESA WorldCover 2021 class in "
                   + ", ".join(f"{k} {v}" for k, v in NEGATIVE_CLASSES.items()) + "; 3 per class",
           "source": f"{BASE} (legend read from the file metadata)", "negatives": negatives}
    Path("data/validation").mkdir(parents=True, exist_ok=True)
    Path("data/validation/negatives.yaml").write_text(yaml.safe_dump(out, sort_keys=False, allow_unicode=True), encoding="utf-8")
    print(len(negatives), "negatives")
    return 0


if __name__ == "__main__":
    sys.exit(main())
