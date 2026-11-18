"""Lunar processing grid and SLDEM2015 reader (T41).

The grid is the Earth one (`grid.TileGrid`: 1° tile, local Lambert azimuthal equal-area projection, whole windows,
each window owned by the tile containing its centre) on the lunar sphere (R = 1737.4 km, the SLDEM2015 reference).
Longitudes are east, 0 to 360, as in SLDEM2015.

SLDEM2015 512 ppd tiles: 30° x 45°, float32 heights in km above 1737.4 km, simple cylindrical, pixel registered,
first row at the northern edge (labels read on 18/11/2026).
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from discovery.grid import TileGrid

MOON_R = 1737400.0
GEO = f"+proj=longlat +R={MOON_R:.0f} +no_defs"
LAT_BANDS = (-60, -30, 0, 30)


def laea(lat0: float, lon0: float) -> str:
    return f"+proj=laea +lat_0={lat0} +lon_0={lon0} +R={MOON_R:.0f} +units=m +no_defs"


@dataclass(frozen=True)
class MoonTileGrid(TileGrid):
    @property
    def crs(self) -> str:
        return laea(self.lat + 0.5, self.lon + 0.5)

    def window_centres_latlon(self) -> tuple[np.ndarray, np.ndarray]:
        from rasterio.warp import transform
        x, y = self.window_centres_xy()
        lon, lat = transform(self.crs, GEO, x.ravel().tolist(), y.ravel().tolist())
        lon = (np.array(lon) - self.lon + 180) % 360 - 180 + self.lon       # continuous around the tile
        return np.array(lat).reshape(x.shape), lon.reshape(x.shape)


def moon_tile_grid(lat: int, lon: int, pixel_m: float, window_m: float, margin_px: int = 1) -> MoonTileGrid:
    from rasterio.warp import transform
    n = max(int(round(window_m / pixel_m)), 1)
    wm = n * pixel_m
    t = np.linspace(0, 1, 41)
    edge_lat = np.concatenate([lat + t, lat + t, np.full_like(t, lat), np.full_like(t, lat + 1)])
    edge_lon = np.concatenate([np.full_like(t, lon), np.full_like(t, lon + 1), lon + t, lon + t])
    xs, ys = transform(GEO, laea(lat + 0.5, lon + 0.5), edge_lon.tolist(), edge_lat.tolist())
    xmin = math.floor(min(xs) / wm) * wm - wm
    xmax = math.ceil(max(xs) / wm) * wm + wm
    ymin = math.floor(min(ys) / wm) * wm - wm
    ymax = math.ceil(max(ys) / wm) * wm + wm
    return MoonTileGrid(lat, lon, pixel_m, n, margin_px, xmin, ymax,
                        int(round((ymax - ymin) / wm)), int(round((xmax - xmin) / wm)))


def _lat_name(v: int, south_zero: bool) -> str:
    if v == 0:
        return "00S" if south_zero else "00N"
    return f"{abs(v):02d}{'N' if v > 0 else 'S'}"


def tile_file(lat0: int, lon0: int, ppd: int = 512) -> str:
    """File of the 30° x 45° tile whose south-west corner is (lat0, lon0). The 30°S-0° band is named 30S_00S."""
    lat1 = lat0 + 30
    return (f"SLDEM2015_{ppd}_{_lat_name(lat0, False)}_{_lat_name(lat1, lat0 < 0)}_"
            f"{lon0:03d}_{lon0 + 45:03d}_FLOAT.IMG")


class SldemIndex:
    """Reads any latitude-longitude box of SLDEM2015 (metres), across tile edges and the 0°/360° meridian."""

    def __init__(self, folder: Path, ppd: int = 512):
        self.folder, self.ppd = Path(folder), ppd
        self._maps: dict = {}

    def _tile(self, lat0: int, lon0: int) -> np.ndarray:
        key = (lat0, lon0)
        if key not in self._maps:
            self._maps[key] = np.memmap(self.folder / tile_file(lat0, lon0, self.ppd), dtype="<f4", mode="r",
                                        shape=(30 * self.ppd, 45 * self.ppd))
        return self._maps[key]

    def read(self, lat_lo: float, lat_hi: float, lon_lo: float, lon_hi: float) -> tuple[np.ndarray, float, float]:
        """Heights (m) of the pixels whose centres fall in the box, edges snapped to the pixel grid; returns the
        array and its west and north edges (lon_lo may be negative or above 360)."""
        if lat_lo < -60 or lat_hi > 60:
            raise ValueError(f"SLDEM2015 covers 60°S to 60°N, not {lat_lo} to {lat_hi}")
        p = self.ppd
        r0, r1 = round((60 - lat_hi) * p), round((60 - lat_lo) * p)       # global rows from 60°N
        c0, c1 = round(lon_lo * p), round(lon_hi * p)                     # global columns from 0°E (may wrap)
        out = np.empty((r1 - r0, c1 - c0), "float32")
        tile_rows, tile_cols = 30 * p, 45 * p
        for i, lat0 in enumerate(sorted(LAT_BANDS, reverse=True)):        # bands from north to south
            br0 = i * tile_rows
            lo, hi = max(r0, br0), min(r1, br0 + tile_rows)
            if lo >= hi:
                continue
            c = c0
            while c < c1:
                gc = c % (360 * p)
                lon0 = (gc // tile_cols) * 45
                tc = gc - (lon0 // 45) * tile_cols
                w = min(c1 - c, tile_cols - tc)
                out[lo - r0:hi - r0, c - c0:c - c0 + w] = self._tile(lat0, lon0)[lo - br0:hi - br0, tc:tc + w]
                c += w
        return out * 1000.0, c0 / p, 60 - r0 / p
