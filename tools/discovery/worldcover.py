"""ESA WorldCover 2021 v200 (catalogue id esa-worldcover) as a mask source (map spec, state "masked").

Read per 1° tile at the overview closest to the pixel size, nearest neighbour (the resampling ESA used to build
the overviews is not stated in the file metadata: not verified). Classes and legend from the file metadata.
"""
from __future__ import annotations

import numpy as np

from discovery.copernicus import s3_list

BUCKET = "https://esa-worldcover.s3.eu-central-1.amazonaws.com"
PREFIX = "v200/2021/map/"
NATIVE_M = 10.0
OVERVIEWS = (2, 4, 8, 16, 32, 64)           # read from the files (18/11/2026)
# Classes where the ground is hidden (validation-protocol-v2): the negatives of the protocol are drawn in 10, 40, 50,
# 80, 90 and 95; snow and ice (70) hide rock too. v1 of the engine masked only 10, 50, 70 and 80 (T43 finding).
MASK_CLASSES = {10: "tree", 40: "cropland", 50: "built", 70: "snow_ice", 80: "water", 90: "wetland", 95: "mangroves"}


def tile3(lat: int, lon: int) -> str:
    a, o = (lat // 3) * 3, (lon // 3) * 3
    return f"{'N' if a >= 0 else 'S'}{abs(a):02d}{'E' if o >= 0 else 'W'}{abs(o):03d}"


def tiles_around(lat: int, lon: int) -> list[str]:
    """WorldCover 3° tiles touched by a 1° tile and its 1° margin."""
    return sorted({tile3(lat + da, (lon + do + 180) % 360 - 180) for da in (-1, 0, 1) for do in (-1, 0, 1)
                   if -90 <= lat + da <= 89})


def overview_level(pixel_m: float) -> int | None:
    """Index of the coarsest overview not coarser than the target pixel (None: full resolution)."""
    best = None
    for i, f in enumerate(OVERVIEWS):
        if NATIVE_M * f <= pixel_m:
            best = i
    return best


def key(name: str) -> str:
    return f"{PREFIX}ESA_WorldCover_10m_2021_v200_{name}_Map.tif"


def listing() -> dict:
    return {o["key"]: o for o in s3_list(BUCKET, PREFIX) if o["key"].endswith("_Map.tif")}


def read(grid, signals: dict) -> tuple[dict[str, np.ndarray], dict]:
    """Per-pixel class indicators on the grid, and the input signals of the files read."""
    import rasterio
    from rasterio.warp import Resampling, reproject
    cls = np.zeros(grid.shape, dtype="uint8")
    used = {}
    level = overview_level(grid.pixel_m)
    for name in tiles_around(grid.lat, grid.lon):
        k = key(name)
        if k not in signals:
            continue  # no WorldCover tile: open ocean
        opts = {} if level is None else {"overview_level": level}
        with rasterio.open(f"{BUCKET}/{k}", **opts) as src:
            part = np.zeros(grid.shape, dtype="uint8")
            reproject(rasterio.band(src, 1), part, src_nodata=0, dst_transform=grid.transform, dst_crs=grid.crs,
                      dst_nodata=0, resampling=Resampling.nearest)
        used[k] = {x: signals[k][x] for x in ("etag", "size", "last_modified")}
        cls = np.where(part > 0, part, cls)
    return fractions(cls), used


def fractions(cls: np.ndarray) -> dict[str, np.ndarray]:
    """Per-pixel indicator of each mask class; NaN where WorldCover has no value (0: outside its coverage, such
    as south of 60°S, or open ocean). `covered` is 1 where a class is known. Unknown is never "not this class"."""
    known = cls > 0
    out = {n: np.where(known, cls == c, np.nan).astype("float32") for c, n in MASK_CLASSES.items()}
    out["covered"] = known.astype("float32")
    return out
