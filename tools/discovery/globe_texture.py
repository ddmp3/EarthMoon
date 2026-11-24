"""Texture of the Mars globe of the interface (T45c part 2): MOLA relief, shaded, in simple cylindrical projection.

No verified whole-Mars colour map was found at NASA or USGS for this use (24/11/2026), so the globe shows our own
rendering of MOLA elevation, which is data the project already uses: the 128 ppd MEGDR tiles between 88°N and 88°S,
and the 512 ppd polar grids above. Colours are a hypsometric ramp (low: dark, high: light rust) with a hillshade;
they are not Mars's true colours, and the interface says so.

    PYTHONPATH=tools python -m discovery.globe_texture --mola /data/mola --out apps/web/public/img/planet-mars.jpg
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np

W, H = 2048, 1024
RAMP = np.array([[38, 18, 12], [110, 52, 30], [176, 98, 58], [222, 162, 112], [246, 222, 196]], float)


def shade(z: np.ndarray, deg_per_px: float, radius_m: float = 3396190.0) -> np.ndarray:
    """RGB (uint8) of an elevation grid: hypsometric ramp times a hillshade from the north-west."""
    zf = np.where(np.isfinite(z), z, np.nanmedian(z))
    lo, hi = np.percentile(zf, [1, 99])
    t = np.clip((zf - lo) / max(hi - lo, 1.0), 0, 1) * (len(RAMP) - 1)
    k = np.minimum(t.astype(int), len(RAMP) - 2)
    f = (t - k)[..., None]
    rgb = RAMP[k] * (1 - f) + RAMP[k + 1] * f
    step = np.radians(deg_per_px) * radius_m
    gy, gx = np.gradient(zf, step, step)
    gx = gx * 20.0
    gy = gy * 20.0                                               # vertical exaggeration of the shading only
    n = np.sqrt(gx ** 2 + gy ** 2 + 1)
    light = (-gx * -0.7 + -gy * 0.7 + 1.0) / n / np.sqrt(0.49 + 0.49 + 1.0)
    hs = np.clip(0.35 + 0.75 * light, 0, 1.25)[..., None]
    return np.clip(rgb * hs, 0, 255).astype("uint8")


def equirect(mola: Path) -> np.ndarray:
    """Elevation on a W x H simple cylindrical grid (90°N at the top row, 0°E at the left)."""
    from discovery.mars import POLAR_R_M, read_pds4
    lat = 90 - (np.arange(H) + 0.5) * 180 / H
    lon = (np.arange(W) + 0.5) * 360 / W
    out = np.full((H, W), np.nan, "float32")
    for top in (88, 44, 0, -44):
        for west in (0, 90, 180, 270):
            name = f"megt{abs(top):02d}{'n' if top >= 0 else 's'}{west:03d}hb.img"
            z = read_pds4(mola / name)
            rows = np.flatnonzero((lat <= top) & (lat > top - 44))
            cols = np.flatnonzero((lon >= west) & (lon < west + 90))
            r = np.clip(((top - lat[rows]) * 128).astype(int), 0, z.shape[0] - 1)
            c = np.clip(((lon[cols] - west) * 128).astype(int), 0, z.shape[1] - 1)
            out[np.ix_(rows, cols)] = z[np.ix_(r, c)]
    for north in (True, False):
        g = read_pds4(mola / f"megt_{'n' if north else 's'}_512_1.img")
        size = g.shape[0]
        px = 2 * np.pi * POLAR_R_M / 360 / 512
        rows = np.flatnonzero(lat > 88) if north else np.flatnonzero(lat < -88)
        la, lo = np.meshgrid(np.radians(np.abs(lat[rows])), np.radians(lon), indexing="ij")
        rho = 2 * POLAR_R_M * np.tan(np.pi / 4 - la / 2)
        x, y = rho * np.sin(lo), (rho * np.cos(lo) if north else -rho * np.cos(lo))
        cc = np.clip((x / px + (size - 1) / 2).round().astype(int), 0, size - 1)
        rr = np.clip((y / px + (size - 1) / 2).round().astype(int), 0, size - 1)
        out[rows, :] = g[rr, cc]
    return out


def main(argv=None) -> int:
    from PIL import Image
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--mola", type=Path, default=Path("/data/mola"))
    ap.add_argument("--out", type=Path, required=True)
    a = ap.parse_args(argv)
    Image.fromarray(shade(equirect(a.mola), 360 / W)).save(a.out, quality=88, progressive=True)
    print(a.out)
    return 0


if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    sys.exit(main())
