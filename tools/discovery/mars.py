"""Mars terrain windows (T48, decision E19): MOLA MEGDR grids.

E19 (David, 20/11/2026): windows of 25 x 25 pixels of the planetary grid, as on the Moon (25 x 25 pixels of 40 m):
- polar grids at 512 pixels per degree (about 115.8 m): windows of about 2.9 km;
- the global grid at 128 pixels per degree (about 463 m north-south): windows of about 11.6 km.
The global grid is equirectangular: east-west pixels shrink with the cosine of latitude, so each band of 25 rows is
resampled east-west to square metric pixels before its windows are measured.
MOLA bins are filled by interpolation where no shot fell (55% of bins hold a shot near the equator, per the label):
each window keeps the share of its pixels that hold at least one shot (count grids `megc`).
"""
from __future__ import annotations

import math
import re
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

MARS_R_M = 3396190.0                         # IAU sphere used by the MEGDR labels (a_axis_radius 3396.0 km)
WINDOW_PX = 25                               # E19
DTYPES = {"SignedMSB2": ">i2", "UnsignedMSB2": ">u2", "SignedLSB2": "<i2", "IEEE754MSBSingle": ">f4"}


def read_pds4(img: Path) -> np.ndarray:
    """2-D array of a PDS4 image, from the shape, type and offset in its .xml label."""
    label = Path(img).with_suffix(".xml").read_text(encoding="utf-8")
    dtype = DTYPES[re.search(r"<(?:\w+:)?data_type>([^<]+)<", label).group(1)]
    n = [int(x) for x in re.findall(r"<(?:\w+:)?elements>(\d+)<", label)[:2]]
    m = re.search(r'<(?:\w+:)?offset unit="byte">(\d+)<', label)
    offset = int(m.group(1)) if m else 0
    return np.fromfile(img, dtype=dtype, count=n[0] * n[1], offset=offset).reshape(n[0], n[1]).astype(dtype.replace(">", "").replace("<", "") if dtype[1] != "f" else "f4")


def observed_fraction(counts: np.ndarray) -> float:
    """Share of pixels holding at least one MOLA shot."""
    c = np.asarray(counts)
    return float((c > 0).mean()) if c.size else float("nan")


def band_windows(z: np.ndarray, lats: np.ndarray, ppd: int, window_px: int = WINDOW_PX, counts: np.ndarray | None = None) -> dict:
    """Windows of one band of `window_px` rows of an equirectangular grid: the band is resampled east-west to square
    metric pixels (north-south pixel size), then cut into windows of window_px x window_px pixels."""
    from discovery.windows import ALL_METRICS, window_metrics_grid
    py = 2 * math.pi * MARS_R_M / 360 / ppd
    lat_c = float(np.mean(lats))
    px = py * math.cos(math.radians(lat_c))
    ncol = z.shape[1]
    width = ncol * px
    nsq = int(width // py)
    x_src = (np.arange(ncol) + 0.5) * px
    x_dst = (np.arange(nsq) + 0.5) * py
    zs = np.vstack([np.interp(x_dst, x_src, row.astype(float)) for row in z])
    w = window_metrics_grid(zs, py, window_px, margin=0, metrics=ALL_METRICS)
    out = {k: v.ravel() for k, v in w.items()}
    n = out["slope_mean"].size
    out["col_m"] = (np.arange(n) + 0.5) * window_px * py
    out["lon_frac"] = out["col_m"] / width                                  # position along the band, 0..1
    out["lat"] = np.full(n, lat_c)
    out["width_m"] = window_px * py
    if counts is not None:
        cs = np.vstack([np.interp(x_dst, x_src, (row > 0).astype(float)) for row in counts]) > 0.5
        nw = cs.shape[1] // window_px
        out["observed_frac"] = cs[:window_px, :nw * window_px].reshape(window_px, nw, window_px).mean(axis=(0, 2))[:n]
    return out


def polar_latlon(row: np.ndarray, col: np.ndarray, size: int, pixel_m: float, north: bool = True):
    """Latitude and longitude of pixel centres of a MEGDR polar grid (polar stereographic, pole at the centre; north:
    longitude 0 straight down, 90°E to the right; south: 0 straight up, 90°E to the right, per the MEGDR page)."""
    c = (size - 1) / 2
    x = (np.asarray(col, float) - c) * pixel_m
    y = (np.asarray(row, float) - c) * pixel_m
    rho = np.hypot(x, y)
    lat_abs = 90 - np.degrees(2 * np.arctan(rho / (2 * MARS_R_M)))
    if north:
        lon = np.degrees(np.arctan2(x, y)) % 360
        return lat_abs, lon
    lon = np.degrees(np.arctan2(x, -y)) % 360
    return -lat_abs, lon
