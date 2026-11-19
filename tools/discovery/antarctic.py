"""Antarctic surface mask south of 60°S (T43; catalogue add-rock-outcrop-v7-3, read in T14).

WorldCover has no tile south of 60°S (T40). There, the SCAR rock outcrop polygons (Landsat 8, version 7.3) tell
rock from ice and snow: outside the polygons the ground is hidden by ice. The polygons are rasterised once on the
Antarctic polar stereographic grid (EPSG:3031) at 200 m.

    python tools/discovery/antarctic.py --shp add_rockoutcrop_landsat_v7.3.shp --out /data/add-rock-outcrop
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np

CRS = "EPSG:3031"
PIXEL_M = 200.0
HALF_EXTENT_M = 3_000_000.0                                  # Antarctica fits in +-3000 km


def outcrop_share(lat: np.ndarray, lon: np.ndarray, raster: np.ndarray, tf, radius_m: float = 400.0) -> np.ndarray:
    """Share of rock at each point (mean of a 3 x 3 sample over +-radius_m); NaN north of 60°S."""
    from rasterio.warp import transform
    lat, lon = np.asarray(lat, float), np.asarray(lon, float)
    out = np.full(lat.shape, np.nan)
    south = lat < -60
    if not south.any():
        return out
    x, y = transform("EPSG:4326", CRS, lon[south].tolist(), lat[south].tolist())
    x, y = np.array(x), np.array(y)
    offs = (-radius_m, 0.0, radius_m) if radius_m > 0 else (0.0,)
    acc = np.zeros(x.size)
    for dx in offs:
        for dy in offs:
            col = np.floor(((x + dx) - tf.c) / tf.a).astype(int)
            row = np.floor(((y + dy) - tf.f) / tf.e).astype(int)
            inside = (row >= 0) & (row < raster.shape[0]) & (col >= 0) & (col < raster.shape[1])
            v = np.zeros(x.size)
            v[inside] = raster[row[inside], col[inside]]
            acc += v
    out[south] = acc / len(offs) ** 2
    return out


def tiles_with_outcrops(raster: np.ndarray, tf) -> list[str]:
    """'lat,lon' of every 1° tile (south of 60°S) that holds at least one rock pixel."""
    from rasterio.warp import transform
    rows, cols = np.nonzero(raster)
    x = tf.c + (cols + 0.5) * tf.a
    y = tf.f + (rows + 0.5) * tf.e
    tiles = set()
    for i in range(0, x.size, 500_000):
        lon, lat = transform(CRS, "EPSG:4326", x[i:i + 500_000].tolist(), y[i:i + 500_000].tolist())
        la, lo = np.floor(np.array(lat)).astype(int), np.floor(np.array(lon)).astype(int)
        lo = (lo + 180) % 360 - 180
        tiles |= {f"{a},{b}" for a, b in zip(la, lo) if a < -60}
    return sorted(tiles)


def rasterize(shp: Path) -> tuple[np.ndarray, object]:
    import shapefile
    from rasterio.features import rasterize as rz
    from rasterio.transform import from_origin
    n = int(2 * HALF_EXTENT_M / PIXEL_M)
    tf = from_origin(-HALF_EXTENT_M, HALF_EXTENT_M, PIXEL_M, PIXEL_M)
    r = shapefile.Reader(str(shp))
    shapes = ((s.__geo_interface__, 1) for s in r.iterShapes())
    return rz(shapes, out_shape=(n, n), transform=tf, fill=0, dtype="uint8"), tf


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--shp", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    a = ap.parse_args(argv)
    raster, tf = rasterize(a.shp)
    np.save(a.out / "outcrops_200m_3031.npy", raster)
    (a.out / "outcrops_200m_3031.json").write_text(json.dumps({"crs": CRS, "transform": list(tf)[:6], "pixel_m": PIXEL_M}) + "\n")
    tiles = tiles_with_outcrops(raster, tf)
    (a.out / "outcrop_tiles.json").write_text(json.dumps(tiles) + "\n")
    print(f"rock pixels {int(raster.sum())} ({raster.sum() * PIXEL_M ** 2 / 1e6:.0f} km2), tiles {len(tiles)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
