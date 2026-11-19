"""Effective resolution of the LOLA polar grid (T41, finding L3; design in docs/wiki/methods/profiles.md).

LDEM_85S_40M is interpolated between laser tracks. The 5 m south pole mosaic (87°S to 90°S) ships a count of laser
returns per pixel. The experiment compares, on the same ground:
  1. the LOLA 40 m terrain and the 5 m mosaic averaged to 40 m (same windows, same code): what interpolation
     does to the metrics actually compared;
  2. the short-wave power (160 m against 2 km) as a function of the share of 40 m pixels with a laser return;
  3. the Gaussian smoothing of Copernicus that gives Earth the same short-wave power (input to T42).

    python tools/discovery/resolution.py --ldem /data/lola/ldem_85s_40m.img --dem5 /data/lola/pgda/ldem_87s_5mpp.tif \
        --count5 /data/lola/pgda/ldec_87s_5mpp.tif --out data/profiles/moon/effective-resolution.json
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "precompute"))
from discovery.spectrum import radial_spectrum, spectral_ratio  # noqa: E402

SHORT_M, LONG_M = 160.0, 2000.0


# --- pure part (tested) ------------------------------------------------------------------------------------

def gaussian_smooth(z: np.ndarray, sigma_px: float) -> np.ndarray:
    """Gaussian smoothing by FFT with reflected edges (no new dependency). sigma 0 returns z unchanged."""
    if sigma_px <= 0:
        return z
    n0, n1 = z.shape
    p = np.pad(z, ((n0 // 2, n0 // 2), (n1 // 2, n1 // 2)), mode="reflect")
    f0, f1 = np.fft.fftfreq(p.shape[0]), np.fft.rfftfreq(p.shape[1])
    g = np.exp(-2 * (np.pi * sigma_px) ** 2 * (f0[:, None] ** 2 + f1[None, :] ** 2))
    s = np.fft.irfft2(np.fft.rfft2(p) * g, s=p.shape)
    return s[n0 // 2:n0 // 2 + n0, n1 // 2:n1 // 2 + n1]


def compare_pairs(a: np.ndarray, b: np.ndarray) -> dict:
    """Same windows measured two ways: median ratio b/a, Spearman rank correlation, |b - a| quantiles."""
    ok = np.isfinite(a) & np.isfinite(b) & (a > 0)
    x, y = a[ok], b[ok]
    rx, ry = np.argsort(np.argsort(x)), np.argsort(np.argsort(y))
    d = np.abs(y - x)
    return {"n": int(x.size), "median_ratio": round(float(np.median(y / x)), 3),
            "spearman": round(float(np.corrcoef(rx, ry)[0, 1]), 4),
            "abs_diff": {"median": round(float(np.median(d)), 3), "p95": round(float(np.percentile(d, 95)), 3)}}


def ratio(block: np.ndarray, pixel_m: float) -> float:
    k, p = radial_spectrum(block, pixel_m)
    return spectral_ratio(k, p, pixel_m, SHORT_M, LONG_M)


def match_sigma(blocks: list[np.ndarray], target: float, sigmas: tuple[float, ...], pixel_m: float) -> dict:
    """Smallest Gaussian sigma (pixels) whose median short-wave ratio over `blocks` is at or below `target`."""
    rows = []
    for s in sigmas:
        rows.append({"sigma_px": s, "median_ratio": float(np.median([ratio(gaussian_smooth(b, s), pixel_m) for b in blocks]))})
        if rows[-1]["median_ratio"] <= target:
            return {"sigma_px": s, "target": target, "steps": rows}
    return {"sigma_px": None, "target": target, "steps": rows}


# --- run (large files, not unit-tested) --------------------------------------------------------------------

LDEM_SIZE, LDEM_PX, MOSAIC_HALF_M, MOSAIC_PX = 7584, 40.0, 100_000.0, 5.0
WIN, BLOCK = 25, 125                     # 1 km windows and 5 km spectral blocks at 40 m


def mosaic_on_ldem(dem5: Path, count5: Path, start: int, n: int):
    """5 m elevation averaged to the 40 m LDEM pixels [start, start + n) in both axes, the share of 5 m pixels
    with a laser return in each 40 m pixel, and the 5 m pixel offset used."""
    import rasterio
    from rasterio.windows import Window
    f = int(LDEM_PX / MOSAIC_PX)
    off = int((LDEM_SIZE * LDEM_PX / 2 - MOSAIC_HALF_M) / MOSAIC_PX)       # 10336 five-metre pixels
    r0 = start * f - off
    z40 = np.full((n, n), np.nan, "float32")
    c40 = np.full((n, n), np.nan, "float32")
    with rasterio.open(dem5) as dz, rasterio.open(count5) as dc:
        nod = dz.nodata
        step = BLOCK                                                       # 125 LDEM rows = 1000 five-metre rows
        for i in range(0, n, step):
            h = min(step, n - i)
            win = Window(r0, r0 + i * f, n * f, h * f)
            z = dz.read(1, window=win).astype("float64")
            if nod is not None:
                z[z == nod] = np.nan
            c = dc.read(1, window=win).astype("float64")
            zb = z.reshape(h, f, n, f)
            ok = np.isfinite(zb).all(axis=(1, 3))
            with np.errstate(invalid="ignore"):
                z40[i:i + h] = np.where(ok, zb.mean(axis=(1, 3)), np.nan)
            c40[i:i + h] = (c.reshape(h, f, n, f) > 0).mean(axis=(1, 3))
    return z40, c40, off


def run(a) -> dict:
    from lunar_reference import latitude_grid, read_ldem
    from discovery.windows import STORED_METRICS, window_metrics_grid
    from discovery.profiles import file_input, select_windows, summarise, window_fraction
    start, stop = 1300, 6275                                               # multiples of 25 inside the mosaic
    n = stop - start
    z = read_ldem(str(a.ldem), LDEM_SIZE)[start:stop, start:stop]
    lat = latitude_grid(LDEM_SIZE, LDEM_PX)[start:stop, start:stop]
    z5, c40, off = mosaic_on_ldem(a.dem5, a.count5, start, n)
    inside = np.isfinite(z5) & (lat <= -85.0)
    wl = window_metrics_grid(z, LDEM_PX, WIN, margin=0)
    wm = window_metrics_grid(z5, LDEM_PX, WIN, margin=0)
    sel = select_windows(inside, WIN) & np.isfinite(wl["slope_mean"]) & np.isfinite(wm["slope_mean"])
    cov = window_fraction(c40, WIN)
    out = {"inputs": {"lro-lola-ldem-85s-40m": file_input(a.ldem), "lola-south-pole-5m-mosaic/elevation": file_input(a.dem5),
                      "lola-south-pole-5m-mosaic/count": file_input(a.count5)},
           "grid": {"ldem_rows_cols": [start, stop], "mosaic_offset_px": off, "window_px": WIN, "block_px": BLOCK},
           "windows_compared": int(sel.sum()),
           "coverage": {f"p{p}": round(float(np.percentile(cov[sel], p)), 3) for p in (5, 25, 50, 75, 95)}}
    # 1. what interpolation does to the compared metrics (same windows, same code)
    out["metrics_ldem_vs_mosaic"] = {k: compare_pairs(wm[k][sel], wl[k][sel]) for k in STORED_METRICS}
    out["slope_mean_percentiles"] = {"ldem": summarise(wl, sel, ("slope_mean",))["metrics"]["slope_mean"],
                                     "mosaic_at_40m": summarise(wm, sel, ("slope_mean",))["metrics"]["slope_mean"]}
    q = np.percentile(cov[sel], (0, 20, 40, 60, 80, 100))
    by_cov = []
    for lo, hi in zip(q[:-1], q[1:]):
        s = sel & (cov >= lo) & (cov <= hi)
        r = wl["slope_mean"][s] / wm["slope_mean"][s]
        by_cov.append({"coverage": [round(float(lo), 3), round(float(hi), 3)], "windows": int(s.sum()),
                       "median_slope_ratio_ldem_over_mosaic": round(float(np.nanmedian(r)), 3)})
    out["slope_ratio_by_coverage"] = by_cov
    # 2. short-wave power per 5 km block
    blocks = []
    for r in range(0, n - BLOCK + 1, BLOCK):
        for c in range(0, n - BLOCK + 1, BLOCK):
            bl, bm = z[r:r + BLOCK, c:c + BLOCK].astype("float64"), z5[r:r + BLOCK, c:c + BLOCK].astype("float64")
            if not (inside[r:r + BLOCK, c:c + BLOCK].all() and np.isfinite(bl).all()):
                continue
            blocks.append({"ldem": ratio(bl, LDEM_PX), "mosaic": ratio(bm, LDEM_PX),
                           "coverage": float(c40[r:r + BLOCK, c:c + BLOCK].mean()),
                           "slope": float(np.nanmean(wm["slope_mean"][r // WIN:(r + BLOCK) // WIN, c // WIN:(c + BLOCK) // WIN]))})
    out["blocks"] = len(blocks)
    spec = []
    for lo, hi in ((0.0, 3.0), (3.0, 8.0), (8.0, 90.0)):
        b = [x for x in blocks if lo <= x["slope"] < hi]
        if b:
            spec.append({"slope": [lo, hi], "blocks": len(b),
                         "median_ratio_ldem": float(np.median([x["ldem"] for x in b])),
                         "median_ratio_mosaic": float(np.median([x["mosaic"] for x in b])),
                         "median_coverage": round(float(np.median([x["coverage"] for x in b])), 3)})
    out["short_wave_ratio_160m_over_2km"] = spec
    out["_blocks"] = blocks
    return out


def earth_match(listing: Path, tiles: Path, targets: list[dict], sigmas=(0.0, 0.5, 1.0, 1.5, 2.0, 3.0, 4.0)) -> list[dict]:
    """Step 3: Gaussian sigma (40 m pixels) that brings Copernicus GLO-30 blocks (5 km, read at 40 m on the pilot
    tiles) down to the LOLA short-wave ratio of the same slope class."""
    import os
    from discovery.cube import GDAL_ENV, read_dem
    from discovery.grid import tile_grid
    from terrain_metrics import slope_deg
    os.environ.update(GDAL_ENV)
    have = {tuple(map(int, k.split(","))) for k in json.loads(listing.read_text())}
    blocks: list[tuple[float, np.ndarray]] = []
    for line in tiles.read_text().split():
        la, lo = (int(v) for v in line.split(","))
        g = tile_grid(la, lo, LDEM_PX, 1000.0)
        z, _ = read_dem(g, "glo30", have, None)
        for r in range(1, z.shape[0] - BLOCK, BLOCK):
            for c in range(1, z.shape[1] - BLOCK, BLOCK):
                b = z[r:r + BLOCK, c:c + BLOCK].astype("float64")
                if np.isfinite(b).all() and np.ptp(b) > 0:
                    blocks.append((float(np.mean(slope_deg(b, LDEM_PX))), b))
    out = []
    for t in targets:
        lo, hi = t["slope"]
        sel = [b for s, b in blocks if lo <= s < hi]
        if len(sel) < 5:
            out.append({"slope": t["slope"], "earth_blocks": len(sel), "sigma_px": None, "reason": "fewer than 5 Earth blocks"})
            continue
        m = match_sigma(sel, t["median_ratio_ldem"], sigmas, LDEM_PX)
        raw = np.array([np.mean(slope_deg(b, LDEM_PX)) for b in sel])
        for step in m["steps"]:                              # what the smoothing does to the compared metric
            sm = np.array([np.mean(slope_deg(gaussian_smooth(b, step["sigma_px"]), LDEM_PX)) for b in sel])
            step["median_slope_ratio_smoothed_over_raw"] = round(float(np.median(sm / raw)), 3)
        out.append({"slope": t["slope"], "earth_blocks": len(sel),
                    "earth_ratio_unsmoothed": m["steps"][0]["median_ratio"], "lola_ratio": t["median_ratio_ldem"],
                    "sigma_px": m["sigma_px"], "sigma_m": None if m["sigma_px"] is None else m["sigma_px"] * LDEM_PX,
                    "steps": m["steps"]})
    return out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--ldem", type=Path, required=True)
    ap.add_argument("--dem5", type=Path, required=True)
    ap.add_argument("--count5", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--earth-listing", type=Path)
    ap.add_argument("--earth-tiles", type=Path)
    a = ap.parse_args(argv)
    out = run(a)
    out.pop("_blocks")
    if a.earth_listing:
        out["earth_match"] = earth_match(a.earth_listing, a.earth_tiles, [t for t in out["short_wave_ratio_160m_over_2km"] if t["slope"][0] >= 3])
    a.out.write_text(json.dumps(out, indent=1) + "\n", encoding="utf-8")
    print(json.dumps({k: v for k, v in out.items() if k != "inputs"}, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
