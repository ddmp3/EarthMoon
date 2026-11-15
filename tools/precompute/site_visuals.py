"""Real images of each candidate site and of its "lunar twin", at the same scale (12 km, 40 m grid).

For each site of data/candidates.json, writes to apps/web/public/sites/<id>/:
    earth.jpg         real satellite view (cloudless Sentinel-2 2016; else Landsat WELD, NASA GIBS; absent if none is fine enough)
    earth-relief.jpg  shaded relief of the site (Copernicus DEM GLO-30 resampled to 40 m)
    earth-match.png   transparent amber overlay: pixels whose slope is in the typical lunar south pole range
    moon-relief.jpg   shaded relief of the lunar twin (LRO LOLA LDEM_85S_40M)
    moon-match.png    same overlay, Moon side
and apps/web/public/sites/manifest.json (sources, twin coordinates, share of matching slopes).

Lunar twin: the 1 km window of the south pole (south of 85°S) whose mean slope and roughness are closest
to the site's (distance normalized by the lunar interquartile range), surrounded by 12 km of context.
Both reliefs are shaded with the same lighting: the comparison shows relief, not real light.

Usage:
    python site_visuals.py ../../data/candidates-precomputed.json ~/data/lola/ldem_85s_40m.img
    python site_visuals.py ... --only haughton,tunnunik --force
"""
from __future__ import annotations
import argparse
import io
import json
import math
import os
import sys
import time
import urllib.parse
import urllib.request

import numpy as np

from lunar_reference import MOON_RADIUS_M, latitude_grid, read_ldem, window_stats
from point_geometry import BASE_URL, slope_deg, tile_name

EXTENT_M = 12_000.0
PIXEL_M = 40.0
N = int(EXTENT_M / PIXEL_M)          # 300 pixels
OUT_PX = 600
R_EARTH = 6_371_000.0
HIGHLIGHT = (255, 196, 87)            # ambre : pentes concordantes
S2_WMS = "https://tiles.maps.eox.at/wms"
GIBS_WMS = "https://gibs.earthdata.nasa.gov/wms/epsg4326/best/wms.cgi"
PHOTO_SOURCES = [
    ("sentinel-2", S2_WMS, "s2cloudless", None,
     "Sentinel-2 cloudless 2016 by EOX IT Services GmbH (contains modified Copernicus Sentinel data 2016), CC BY 4.0"),
    ("landsat-weld", GIBS_WMS, "Landsat_WELD_CorrectedReflectance_TrueColor_Global_Annual", "1999-12-01",
     "Landsat WELD true color, annual composite 2000, NASA GIBS"),
]


# ----------------------------------------------------------------- pure functions (tested)
def bbox_square(lat: float, lon: float, extent_m: float = EXTENT_M) -> tuple[float, float, float, float]:
    """(west, south, east, north) of a square of extent_m centered on the point."""
    dlat = math.degrees(extent_m / 2 / R_EARTH)
    dlon = dlat / max(math.cos(math.radians(lat)), 0.02)
    return lon - dlon, lat - dlat, lon + dlon, lat + dlat


def hillshade(z: np.ndarray, pixel_m: float, azimuth: float = 315.0, altitude: float = 35.0) -> np.ndarray:
    """Shaded relief 0-255 (uint8). NaN -> 0."""
    zf = np.where(np.isfinite(z), z, np.nanmean(z) if np.isfinite(z).any() else 0.0)
    gy, gx = np.gradient(zf, pixel_m)
    slope = np.arctan(np.hypot(gx, gy))
    aspect = np.arctan2(gy, -gx)
    az, alt = math.radians(360.0 - azimuth + 90.0), math.radians(altitude)
    shade = np.sin(alt) * np.cos(slope) + np.cos(alt) * np.sin(slope) * np.cos(az - aspect)
    return (np.clip(shade, 0, 1) * 255).astype("uint8")


def match_mask(z: np.ndarray, pixel_m: float, lo: float, hi: float) -> np.ndarray:
    """True where the local slope (°) is within [lo, hi]."""
    s = slope_deg(np.asarray(z, dtype="float64"), pixel_m, pixel_m)
    return np.isfinite(s) & (s >= lo) & (s <= hi)


def find_twin(slope_mean: np.ndarray, roughness: np.ndarray, valid: np.ndarray, site_slope: float, site_rough: float,
              iqr_slope: float, iqr_rough: float) -> tuple[int, int, float]:
    """Index (row, column) of the lunar window closest to the site, and the normalized distance."""
    d = ((slope_mean - site_slope) / iqr_slope) ** 2 + ((roughness - site_rough) / iqr_rough) ** 2
    d = np.where(valid, d, np.inf)
    i = int(np.argmin(d))
    r, c = divmod(i, d.shape[1])
    return r, c, float(math.sqrt(d[r, c]))


def polar_latlon(row: float, col: float, size: int, pixel_m: float, radius_m: float = MOON_RADIUS_M) -> tuple[float, float]:
    """(lat, lon) of a pixel of a south polar stereographic grid centered on the pole (LOLA convention)."""
    offset = (size - 1) / 2.0
    x, y = (col - offset) * pixel_m, (offset - row) * pixel_m
    lat = math.degrees(2 * math.atan(math.hypot(x, y) / (2 * radius_m)) - math.pi / 2)
    return lat, math.degrees(math.atan2(x, y))


# ----------------------------------------------------------------- network access
def fetch_photo(lat: float, lon: float, px: int = 800) -> tuple[bytes, str, str] | None:
    """First source that returns a real (non-empty) image: (jpeg, source id, credit)."""
    from PIL import Image

    w, s, e, n = bbox_square(lat, lon)
    for key, base, layer, when, credit in PHOTO_SOURCES:
        params = {"SERVICE": "WMS", "REQUEST": "GetMap", "VERSION": "1.1.1", "LAYERS": layer, "STYLES": "",
                  "SRS": "EPSG:4326", "BBOX": f"{w},{s},{e},{n}", "WIDTH": px, "HEIGHT": px, "FORMAT": "image/jpeg"}
        if when:
            params["TIME"] = when
        try:
            req = urllib.request.Request(f"{base}?{urllib.parse.urlencode(params)}", headers={"User-Agent": "cyberspace-precompute"})
            with urllib.request.urlopen(req, timeout=90) as res:
                raw = res.read()
            arr = np.asarray(Image.open(io.BytesIO(raw)).convert("L"), dtype="float32")
        except Exception:
            continue
        if arr.std() >= 4.0 and (arr > 8).mean() > 0.9:      # neither uniform nor full of black holes
            return raw, key, credit
    return None


def read_earth_dem(lat: float, lon: float) -> np.ndarray:
    """Copernicus DEM elevations (m) over the 12 km square, N x N grid (40 m). Stitches up to 4 tiles."""
    import rasterio
    from rasterio.errors import RasterioIOError
    from rasterio.transform import from_bounds
    from rasterio.warp import Resampling, reproject

    w, s, e, n = bbox_square(lat, lon)
    dst_transform = from_bounds(w, s, e, n, N, N)
    out = np.full((N, N), np.nan, dtype="float32")
    tiles = {tile_name(la, lo) for la in (s, n - 1e-9) for lo in (w, e - 1e-9)}
    for name in sorted(tiles):
        try:
            with rasterio.open(f"{BASE_URL}/{name}/{name}.tif") as src:
                part = np.full((N, N), np.nan, dtype="float32")
                reproject(rasterio.band(src, 1), part, dst_transform=dst_transform, dst_crs="EPSG:4326",
                          resampling=Resampling.bilinear, dst_nodata=np.nan)
                out = np.where(np.isfinite(out), out, part)
        except RasterioIOError:
            continue          # tile missing (ocean)
    return out


# ----------------------------------------------------------------- writing the images
def save_relief(z: np.ndarray, path: str) -> None:
    from PIL import Image
    Image.fromarray(hillshade(z, PIXEL_M)).resize((OUT_PX, OUT_PX), Image.BICUBIC).save(path, quality=84, optimize=True)


def save_mask(mask: np.ndarray, path: str) -> None:
    """Transparent amber overlay at the original grid (300 px, a few KB): the browser upscales it smoothly."""
    from PIL import Image
    rgba = np.zeros((*mask.shape, 4), dtype="uint8")
    rgba[..., :3] = HIGHLIGHT
    rgba[..., 3] = np.where(mask, 255, 0)
    Image.fromarray(rgba, "RGBA").save(path, optimize=True)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("candidates", help="data/candidates-precomputed.json (with slope_mean and roughness)")
    ap.add_argument("ldem", help="ldem_85s_40m.img (LRO LOLA, PDS)")
    ap.add_argument("--out", default=os.path.join(os.path.dirname(__file__), "..", "..", "apps", "web", "public", "sites"))
    ap.add_argument("--only", default="", help="comma-separated ids")
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--refetch-photos", action="store_true", help="also re-downloads the satellite views")
    args = ap.parse_args(argv)

    with open(args.candidates, encoding="utf-8") as f:
        sites = json.load(f)
    only = {s for s in args.only.split(",") if s}
    os.makedirs(args.out, exist_ok=True)
    manifest_path = os.path.join(args.out, "manifest.json")
    manifest = json.load(open(manifest_path, encoding="utf-8")) if os.path.exists(manifest_path) else {"sites": {}}

    print("Lecture de LOLA…", file=sys.stderr)
    moon = read_ldem(args.ldem)
    size = moon.shape[0]
    south = latitude_grid(size, PIXEL_M) <= -85.0
    stats = window_stats(moon, PIXEL_M, 1000.0)
    n_win = stats["window_px"]
    rows = size // n_win
    sm = stats["slope_mean"].reshape(rows, rows)
    rg = stats["roughness"].reshape(rows, rows)
    smax = stats["slope_max"].reshape(rows, rows)
    centre = (np.arange(rows) * n_win + n_win // 2)
    half = N // 2
    fits = (centre >= half) & (centre < size - half)
    valid = fits[:, None] & fits[None, :] & south[np.ix_(centre, centre)]
    in_region = sm[valid]
    iqr_s = float(np.percentile(in_region, 75) - np.percentile(in_region, 25))
    iqr_r = float(np.percentile(rg[valid], 75) - np.percentile(rg[valid], 25))
    # Typical local slope range (per 40 m pixel) south of 85°S: used for the overlay on both sides.
    pixel_slope = slope_deg(moon[::2, ::2].astype("float64"), PIXEL_M * 2, PIXEL_M * 2)[south[::2, ::2]]
    lo, hi = (round(float(np.percentile(pixel_slope, p)), 1) for p in (25, 75))
    manifest.update({"extent_km": EXTENT_M / 1000, "pixel_m": PIXEL_M, "slope_band_deg": [lo, hi],
                     "moon_source": "LRO LOLA LDEM_85S_40M (NASA PDS Geosciences Node)",
                     "earth_relief_source": "Copernicus DEM GLO-30 (ESA / European Union), resampled to 40 m"})
    print(f"Typical local slope at the south pole: {lo} to {hi}°", file=sys.stderr)

    for s in sites:
        sid = s["id"]
        if only and sid not in only:
            continue
        folder = os.path.join(args.out, sid)
        if not args.force and sid in manifest["sites"] and os.path.exists(os.path.join(folder, "moon-relief.jpg")):
            print(f"  skip  {sid}")
            continue
        pre = s.get("precomputed") or {}
        if pre.get("slope_mean") is None or pre.get("roughness") is None:
            print(f"  FAIL  {sid}: no precomputed relief")
            continue
        os.makedirs(folder, exist_ok=True)
        entry: dict = {}
        try:
            previous = manifest["sites"].get(sid, {}).get("photo")
            photo_path = os.path.join(folder, "earth.jpg")
            if previous and os.path.exists(photo_path) and not args.refetch_photos:
                entry["photo"] = previous          # photo already downloaded: only the relief and the masks are redone
                photo = None
            else:
                photo = fetch_photo(float(s["lat"]), float(s["lon"]))
            if photo:
                with open(os.path.join(folder, "earth.jpg"), "wb") as f:
                    f.write(photo[0])
                entry["photo"] = {"source": photo[1], "credit": photo[2]}
            z = read_earth_dem(float(s["lat"]), float(s["lon"]))
            if np.isfinite(z).mean() < 0.5:
                raise ValueError("Earth relief unavailable over more than half of the square")
            save_relief(z, os.path.join(folder, "earth-relief.jpg"))
            earth_mask = match_mask(z, PIXEL_M, lo, hi)
            save_mask(earth_mask, os.path.join(folder, "earth-match.png"))
            r, c, dist = find_twin(sm, rg, valid, float(pre["slope_mean"]), float(pre["roughness"]), iqr_s, iqr_r)
            cy, cx = int(centre[r]), int(centre[c])
            patch = moon[cy - half:cy + half, cx - half:cx + half]
            save_relief(patch, os.path.join(folder, "moon-relief.jpg"))
            moon_mask = match_mask(patch, PIXEL_M, lo, hi)
            save_mask(moon_mask, os.path.join(folder, "moon-match.png"))
            lat, lon = polar_latlon(cy, cx, size, PIXEL_M)
            entry.update({
                "earth": {"slope_mean": pre["slope_mean"], "slope_max": pre.get("slope_max"), "roughness": pre["roughness"],
                          "match_share": round(float(earth_mask.mean()), 3)},
                "twin": {"lat": round(lat, 3), "lon": round(lon, 3), "slope_mean": round(float(sm[r, c]), 2),
                         "slope_max": round(float(smax[r, c]), 2), "roughness": round(float(rg[r, c]), 2),
                         "distance": round(dist, 3), "match_share": round(float(moon_mask.mean()), 3)},
            })
            manifest["sites"][sid] = entry
            print(f"  ok    {sid}: photo={entry.get('photo', {}).get('source')} jumeau=({lat:.2f}, {lon:.1f}) "
                  f"pente {sm[r, c]:.1f}° (site {pre['slope_mean']}°) dist={dist:.2f}")
        except Exception as e:
            print(f"  FAIL  {sid}: {type(e).__name__}: {e}")
        time.sleep(0.2)

    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=1)
        f.write("\n")
    print(f"{len(manifest['sites'])} sites in {manifest_path}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
