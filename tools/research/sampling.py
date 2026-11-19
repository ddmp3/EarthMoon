"""Sampling experiments of task T22: pilot tiles, scale sensitivity, two-stage screening, spectra, budget.

    python tools/research/sampling.py --ldem /data/lola/ldem_85s_40m.img --cache /data/copernicus \
        --out data/research/sampling-t22.json

Pilot tiles (engineering only, never used to tune similarity):
- 10 Copernicus GLO-30 land tiles drawn with seed 20261117, area-weighted (equal-area on the sphere);
- 3 contrasting tiles: those holding the T21 random windows nearest the 10th, 50th and 95th percentiles of
  slope_mean (exactly flat windows excluded).
Each tile is reprojected (bilinear) to a local Lambert azimuthal equal-area grid at 30, 40 and 90 m.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
import time
import urllib.request
from pathlib import Path
from typing import Callable

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "precompute"))
from terrain_metrics import slope_deg  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
# moved to tools/discovery in T40 (one implementation); re-exported for the T22 and T23 scripts
from discovery.windows import (block_mean, cells_by_coordinate, screening_misses, window_px_m,  # noqa: E402,F401
                               window_slope_means)
from discovery.spectrum import radial_spectrum, spectral_ratio  # noqa: E402,F401  (moved in T41)

BASE = "https://copernicus-dem-30m.s3.amazonaws.com"


# --- pure functions (tested) -------------------------------------------------------------------------------

def pick_land_tiles(seed: int, n: int, exists: Callable[[int, int], bool], max_draws: int = 100_000) -> list[tuple[int, int]]:
    """n distinct 1° tiles (south-west corner), drawn with probability proportional to area, kept if they exist."""
    rng = np.random.default_rng(seed)
    out: list[tuple[int, int]] = []
    for _ in range(max_draws):
        lat = math.floor(math.degrees(math.asin(rng.uniform(-1, 1))))
        lon = int(rng.integers(-180, 180))
        if (lat, lon) not in out and exists(lat, lon):
            out.append((lat, lon))
            if len(out) == n:
                break
    return out


def contrast_rows(rows: list[dict], quantiles=(0.1, 0.5, 0.95)) -> list[dict]:
    """Rows nearest each quantile of slope_mean (exactly flat rows excluded; on a tie the lower value wins)."""
    pool = sorted((r for r in rows if not r.get("flat")), key=lambda r: r["slope_mean"])
    values = np.array([r["slope_mean"] for r in pool])
    picked = []
    for q in quantiles:
        target = np.quantile(values, q)
        picked.append(pool[int(np.argmin(np.abs(values - target)))])
    return picked


# --- data access and run (not unit-tested: network and large files) ---------------------------------------

def tile_name(lat: int, lon: int) -> str:
    ns, ew = ("N" if lat >= 0 else "S"), ("E" if lon >= 0 else "W")
    return f"Copernicus_DSM_COG_10_{ns}{abs(lat):02d}_00_{ew}{abs(lon):03d}_00_DEM"


def tile_exists(lat: int, lon: int) -> bool:
    name = tile_name(lat, lon)
    req = urllib.request.Request(f"{BASE}/{name}/{name}.tif", method="HEAD")
    try:
        with urllib.request.urlopen(req, timeout=30):
            return True
    except urllib.error.HTTPError:
        return False


def count_tiles() -> int:
    """Number of GLO-30 tiles, from the bucket listing (anonymous S3 ListObjectsV2)."""
    import re
    total, token = 0, None
    while True:
        url = f"{BASE}/?list-type=2&delimiter=/" + (f"&continuation-token={urllib.parse.quote(token)}" if token else "")
        body = urllib.request.urlopen(url, timeout=60).read().decode()
        total += len(re.findall(r"<CommonPrefixes><Prefix>Copernicus_DSM", body))
        m = re.search(r"<NextContinuationToken>([^<]+)</NextContinuationToken>", body)
        if not m:
            return total
        token = m.group(1)


def fetch(lat: int, lon: int, cache: Path) -> tuple[Path, str]:
    name = tile_name(lat, lon)
    path = cache / f"{name}.tif"
    if not path.exists():
        urllib.request.urlretrieve(f"{BASE}/{name}/{name}.tif", path)
    return path, hashlib.sha256(path.read_bytes()).hexdigest()


def local_grid(path: Path, lat: int, lon: int, pixel_m: float) -> np.ndarray:
    import rasterio
    from rasterio.transform import from_origin
    from rasterio.warp import Resampling, reproject
    crs = f"+proj=laea +lat_0={lat + 0.5} +lon_0={lon + 0.5} +datum=WGS84 +units=m +no_defs"
    half_y = 0.5 * 111_320.0
    half_x = 0.5 * 111_320.0 * math.cos(math.radians(lat + 0.5))
    ny, nx = int(2 * half_y / pixel_m), int(2 * half_x / pixel_m)
    dst = np.full((ny, nx), np.nan, dtype="float32")
    with rasterio.open(path) as src:
        reproject(rasterio.band(src, 1), dst, dst_transform=from_origin(-half_x, half_y, pixel_m, pixel_m),
                  dst_crs=crs, dst_nodata=np.nan, resampling=Resampling.bilinear)
    dst[dst == 0] = np.nan  # sea level is edited to 0 in GLO-30 tiles: missing, not flat land
    return dst


def run(args) -> dict:
    cache = Path(args.cache)
    cache.mkdir(parents=True, exist_ok=True)
    t0 = time.time()
    n_tiles = count_tiles()
    random_tiles = pick_land_tiles(20261117, 10, tile_exists)
    t21 = json.loads(Path("data/research/redundancy-t21.json").read_text(encoding="utf-8"))["earth_rows"]
    contrast = [(math.floor(r["lat"]), math.floor(r["lon"])) for r in contrast_rows(t21)]
    moon = json.loads(Path("data/reference/moon-south-pole.json").read_text(encoding="utf-8"))
    lunar = moon["terrain_v2"]["params"]["slope_mean"]["distribution"]
    lo, hi = lunar["p25"], lunar["p75"]
    tiles = []
    for kind, (lat, lon) in [("random", t) for t in random_tiles] + [("contrast", t) for t in contrast]:
        tt = time.time()
        path, sha = fetch(lat, lon, cache)
        t_fetch = time.time() - tt
        grids, t_grid = {}, {}
        for px in (30.0, 40.0, 90.0):
            tg = time.time()
            grids[px] = local_grid(path, lat, lon, px)
            t_grid[px] = time.time() - tg
        w = {}
        for px in (30.0, 40.0, 90.0):
            for win in (1000.0, 5000.0):
                tw = time.time()
                w[(px, win)] = window_slope_means(grids[px], px, win)
                t_grid[f"{px}-{win}"] = time.time() - tw
        # Two-stage test on 5 km cells. Fine stage: 1 km windows at 40 m (the lunar scale). Coarse stage: windows
        # at 90 m. Windows are assigned to cells by their centre coordinates (pixel counts differ per scale).
        fine_w = window_px_m(1000.0, 40.0)
        coarse_w = window_px_m(1000.0, 90.0)
        fine = {c: [v for v in vals if np.isfinite(v)] for c, vals in cells_by_coordinate(w[(40.0, 1000.0)], fine_w, 5000.0).items()}
        coarse = cells_by_coordinate(w[(90.0, 1000.0)], coarse_w, 5000.0)
        screen = {}
        rules = {"abs+0": (0.0, 1.0), "abs+1": (1.0, 1.0), "abs+2": (2.0, 1.0), "rel0.75": (0.0, 0.75), "rel0.5": (0.0, 0.5)}
        for label, (margin, factor) in rules.items():
            passed = {c: any(lo * factor - margin <= v <= hi + margin for v in coarse.get(c, []) if np.isfinite(v))
                      for c in fine}
            screen[label] = screening_misses(fine, passed, lo, hi)
        pair = lambda a, b: _paired(w[a], w[b])
        tiles.append({
            "kind": kind, "lat": lat, "lon": lon, "tile": tile_name(lat, lon), "sha256": sha,
            "valid_1km_40m": int(np.isfinite(w[(40.0, 1000.0)]).sum()),
            "median_slope": {f"{int(px)}m_{int(win)}m": _med(w[(px, win)]) for (px, win) in w},
            "paired_30_vs_90_1km": pair((30.0, 1000.0), (90.0, 1000.0)),
            "screening": screen, "seconds": {"fetch": round(t_fetch, 1), **{str(k): round(v, 2) for k, v in t_grid.items()}},
            "bytes": path.stat().st_size,
        })
        print(kind, lat, lon, "valid", tiles[-1]["valid_1km_40m"], flush=True)
    spectra = spectra_experiment(args.ldem, cache, random_tiles + contrast)
    return {"date": time.strftime("%Y-%m-%d"), "copernicus_tiles": n_tiles, "lunar_interval": [lo, hi],
            "tiles": tiles, "spectra": spectra, "h3": h3_areas(), "seconds_total": round(time.time() - t0)}


def _med(a):
    v = a[np.isfinite(a)]
    return None if v.size == 0 else round(float(np.median(v)), 3)


def _paired(a, b):
    """Same windows at two pixel scales (b may be one window smaller): median ratio and Spearman."""
    h, w = min(a.shape[0], b.shape[0]), min(a.shape[1], b.shape[1])
    x, y = a[:h, :w].ravel(), b[:h, :w].ravel()
    ok = np.isfinite(x) & np.isfinite(y) & (x > 0)
    if ok.sum() < 10:
        return None
    x, y = x[ok], y[ok]
    rx, ry = np.argsort(np.argsort(x)), np.argsort(np.argsort(y))
    return {"n": int(ok.sum()), "median_ratio": round(float(np.median(y / x)), 3),
            "spearman": round(float(np.corrcoef(rx, ry)[0, 1]), 3)}


def spectra_experiment(ldem: str, cache: Path, tiles, n_blocks: int = 40, size: int = 128) -> dict:
    """Ratio of power at 160 m to power at 2 km wavelength, on 5 km blocks at 40 m: LOLA vs Copernicus."""
    from lunar_reference import latitude_grid, read_ldem
    rng = np.random.default_rng(20261118)
    z = read_ldem(ldem, 7584)
    inside = latitude_grid(7584, 40.0) <= -85.0
    moon = []
    while len(moon) < n_blocks:
        r, c = rng.integers(0, 7584 - size, 2)
        if inside[r, c] and inside[r + size - 1, c + size - 1] and inside[r, c + size - 1] and inside[r + size - 1, c]:
            b = z[r:r + size, c:c + size].astype("float64")
            k, p = radial_spectrum(b, 40.0)
            moon.append({"ratio": spectral_ratio(k, p, 40.0, 160.0, 2000.0), "slope": float(np.nanmean(slope_deg(b, 40.0)))})
    earth = []
    for lat, lon in tiles:
        g = local_grid(cache / f"{tile_name(lat, lon)}.tif", lat, lon, 40.0)
        for _ in range(4):
            r, c = rng.integers(0, g.shape[0] - size), rng.integers(0, g.shape[1] - size)
            b = g[r:r + size, c:c + size].astype("float64")
            if np.isfinite(b).all():
                k, p = radial_spectrum(b, 40.0)
                earth.append({"ratio": spectral_ratio(k, p, 40.0, 160.0, 2000.0), "slope": float(np.nanmean(slope_deg(b, 40.0)))})
    summ = lambda xs: {"n": len(xs), "median_ratio": float(np.median([x["ratio"] for x in xs])),
                       "median_slope": float(np.median([x["slope"] for x in xs]))}
    return {"moon": summ(moon), "earth": summ(earth), "blocks": {"moon": moon, "earth": earth}}


def h3_areas() -> dict | None:
    try:
        import h3
    except ImportError:
        return None
    out = {"version": h3.__version__ if hasattr(h3, "__version__") else "unknown"}
    rng = np.random.default_rng(1)
    for res in (5, 7):
        areas = []
        for lat, lon in zip(np.degrees(np.arcsin(rng.uniform(-1, 1, 5000))), rng.uniform(-180, 180, 5000)):
            areas.append(h3.cell_area(h3.latlng_to_cell(float(lat), float(lon), res), unit="km^2"))
        out[f"res{res}"] = {"min_km2": round(min(areas), 3), "max_km2": round(max(areas), 3),
                            "max_over_min": round(max(areas) / min(areas), 3)}
    return out


def _plain(o):
    """numpy scalars to plain Python numbers for JSON."""
    return o.item() if hasattr(o, "item") else str(o)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--ldem", required=True)
    ap.add_argument("--cache", required=True)
    ap.add_argument("--out", default="data/research/sampling-t22.json")
    a = ap.parse_args(argv)
    result = run(a)
    Path(a.out).write_text(json.dumps(result, indent=1, default=_plain) +"\n", encoding="utf-8")
    print(json.dumps({k: v for k, v in result.items() if k not in ("tiles", "spectra")}, default=_plain))
    return 0


if __name__ == "__main__":
    sys.exit(main())
