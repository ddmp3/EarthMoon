"""Processing grid of one 1° tile (T22 decision 2): local Lambert azimuthal equal-area projection centred on the
tile, whole windows, a one-pixel margin for central differences. A window belongs to the tile that contains its
centre, so neighbouring tiles never count a window twice."""
from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np


def laea(lat0: float, lon0: float) -> str:
    return f"+proj=laea +lat_0={lat0} +lon_0={lon0} +datum=WGS84 +units=m +no_defs"


@dataclass(frozen=True)
class TileGrid:
    lat: int
    lon: int
    pixel_m: float
    window_px: int
    margin_px: int
    xmin: float
    ymax: float
    rows: int
    cols: int

    @property
    def crs(self) -> str:
        return laea(self.lat + 0.5, self.lon + 0.5)

    @property
    def window_m(self) -> float:
        return self.window_px * self.pixel_m

    @property
    def shape(self) -> tuple[int, int]:
        return self.rows * self.window_px + 2 * self.margin_px, self.cols * self.window_px + 2 * self.margin_px

    @property
    def transform(self):
        from rasterio.transform import from_origin
        m = self.margin_px * self.pixel_m
        return from_origin(self.xmin - m, self.ymax + m, self.pixel_m, self.pixel_m)

    def window_centres_xy(self) -> tuple[np.ndarray, np.ndarray]:
        c, r = np.meshgrid(np.arange(self.cols), np.arange(self.rows))
        return self.xmin + (c + 0.5) * self.window_m, self.ymax - (r + 0.5) * self.window_m

    def window_centres_latlon(self) -> tuple[np.ndarray, np.ndarray]:
        from rasterio.warp import transform
        x, y = self.window_centres_xy()
        lon, lat = transform(self.crs, "EPSG:4326", x.ravel().tolist(), y.ravel().tolist())
        lon = (np.array(lon) + 180) % 360 - 180
        return np.array(lat).reshape(x.shape), lon.reshape(x.shape)

    def owned(self) -> np.ndarray:
        lat, lon = self.window_centres_latlon()
        return (lat >= self.lat) & (lat < self.lat + 1) & (lon >= self.lon) & (lon < self.lon + 1)

    def cells(self, cell_m: float = 5000.0) -> tuple[np.ndarray, np.ndarray]:
        """Cell indices (i east, j north) of every window, by its centre (5 km equal-area cells, T22)."""
        x, y = self.window_centres_xy()
        return np.floor(x / cell_m).astype(int), np.floor(y / cell_m).astype(int)


def tile_grid(lat: int, lon: int, pixel_m: float, window_m: float, margin_px: int = 1) -> TileGrid:
    from rasterio.warp import transform
    n = max(int(round(window_m / pixel_m)), 1)
    wm = n * pixel_m
    t = np.linspace(0, 1, 41)
    edge_lat = np.concatenate([lat + t, lat + t, np.full_like(t, lat), np.full_like(t, lat + 1)])
    edge_lon = np.concatenate([np.full_like(t, lon), np.full_like(t, lon + 1), lon + t, lon + t])
    xs, ys = transform("EPSG:4326", laea(lat + 0.5, lon + 0.5), edge_lon.tolist(), edge_lat.tolist())
    xmin = math.floor(min(xs) / wm) * wm - wm
    xmax = math.ceil(max(xs) / wm) * wm + wm
    ymin = math.floor(min(ys) / wm) * wm - wm
    ymax = math.ceil(max(ys) / wm) * wm + wm
    return TileGrid(lat, lon, pixel_m, n, margin_px, xmin, ymax,
                    int(round((ymax - ymin) / wm)), int(round((xmax - xmin) / wm)))
