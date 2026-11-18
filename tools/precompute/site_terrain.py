"""Earth terrain metrics on the same grid as the lunar reference (methodology v2).

For each site, Copernicus DEM GLO-30 is resampled (bilinear) to a local metric grid of 40 m pixels centred on
the site (azimuthal equidistant projection), i.e. the pixel size of LRO LOLA LDEM_85S_40M. Metrics are then
computed by `terrain_metrics` on 1 km windows (25 x 25 pixels), exactly as for the Moon.

Output per site (block "terrain_v2"):
    value        metrics of the central 1 km window (the site itself)
    sigma        robust spread (1.4826 x MAD) of each metric over the 3 x 3 windows around the site: how much
                 the value changes if the site coordinate is off by 1 km. Used as the representativeness
                 uncertainty of the terrain criteria. None if fewer than 3 valid windows.
    neighbours   number of valid windows among the 9
    flags        data-quality flags, e.g. "flat_artifact" when the DEM is exactly flat (edited water body or
                 salt flat: the zero slope is an editing artefact, not a measurement)

    python site_terrain.py ../../data/candidates-precomputed.json            # rewrites in place
    python site_terrain.py ../../data/candidates-precomputed.json --only uyuni haughton
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from datetime import datetime, timezone

import numpy as np

from point_geometry import tile_url
from terrain_metrics import METRIC_KEYS, PIXEL_M, WINDOW_PX, grid_metrics, robust_sigma

NEIGHBOURHOOD = 3  # windows per side
MARGIN_PX = 1      # extra pixels so that window edges use central differences
SOURCE = "Copernicus DEM GLO-30 resampled to a 40 m local metric grid (bilinear), 1 km windows"


def local_crs(lat: float, lon: float) -> str:
    return f"+proj=aeqd +lat_0={lat} +lon_0={lon} +datum=WGS84 +units=m +no_defs"


def tiles_for(lat: float, lon: float, half_m: float) -> list[str]:
    """URLs of the 1 x 1 degree tiles touched by the square of half-size `half_m` around the point."""
    dlat = math.degrees(half_m / 6_371_000.0)
    dlon = dlat / max(math.cos(math.radians(lat)), 0.01)
    urls = []
    for la in sorted({math.floor(lat - dlat), math.floor(lat + dlat)}):
        for lo in sorted({math.floor(lon - dlon), math.floor(lon + dlon)}):
            urls.append(tile_url(la + 0.5, lo + 0.5))
    return urls


def read_local_grid(lat: float, lon: float, size_px: int, pixel_m: float = PIXEL_M) -> np.ndarray:
    """Elevation (m) on a size_px x size_px local grid centred on the point; NaN where no tile has data."""
    import rasterio
    from rasterio.errors import RasterioIOError
    from rasterio.transform import from_origin
    from rasterio.warp import Resampling, reproject

    half = size_px * pixel_m / 2
    dst = np.full((size_px, size_px), np.nan, dtype="float64")
    transform = from_origin(-half, half, pixel_m, pixel_m)
    opened = 0
    for url in tiles_for(lat, lon, half):
        try:
            src = rasterio.open(url)
        except RasterioIOError:
            continue  # ocean tile: stays NaN
        with src:
            opened += 1
            part = np.full_like(dst, np.nan)
            reproject(rasterio.band(src, 1), part, dst_transform=transform, dst_crs=local_crs(lat, lon),
                      dst_nodata=np.nan, resampling=Resampling.bilinear)
            dst = np.where(np.isfinite(part), part, dst)
    if opened == 0:
        raise LookupError(f"no Copernicus DEM tile for ({lat}, {lon})")
    return dst


def summarize(windows: list[dict]) -> dict:
    """Central-window value, neighbourhood spread and flags from the 9 windows (row-major, centre = index 4)."""
    centre = windows[len(windows) // 2]
    value = {k: (None if centre[k] is None else round(centre[k], 3)) for k in METRIC_KEYS}
    sigma = {}
    for k in METRIC_KEYS:
        s = robust_sigma([w[k] for w in windows])
        sigma[k] = None if s is None else round(s, 3)
    flags = []
    if value["slope_max"] is not None and value["slope_max"] < 1e-6:
        flags.append("flat_artifact")
    return {"value": value, "sigma": sigma, "neighbours": sum(w["slope_mean"] is not None for w in windows),
            "valid_frac": centre["valid_frac"], "flags": flags}


def site_terrain(lat: float, lon: float, reader=read_local_grid) -> dict:
    core = NEIGHBOURHOOD * WINDOW_PX
    z = reader(lat, lon, core + 2 * MARGIN_PX)
    # grid_metrics computes slope on the full array; windows are taken inside the margin.
    from terrain_metrics import slope_deg, window_metrics
    slope = slope_deg(z, PIXEL_M)
    windows = []
    for r in range(NEIGHBOURHOOD):
        for c in range(NEIGHBOURHOOD):
            sl = (slice(MARGIN_PX + r * WINDOW_PX, MARGIN_PX + (r + 1) * WINDOW_PX),
                  slice(MARGIN_PX + c * WINDOW_PX, MARGIN_PX + (c + 1) * WINDOW_PX))
            windows.append(window_metrics(z[sl], slope[sl]))
    return summarize(windows)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("candidates")
    ap.add_argument("-o", "--output", default=None)
    ap.add_argument("--only", nargs="*", help="site ids to (re)compute")
    a = ap.parse_args(argv)
    with open(a.candidates, encoding="utf-8") as fh:
        sites = json.load(fh)
    failed = []
    for s in sites:
        if a.only and s["id"] not in a.only:
            continue
        try:
            block = site_terrain(float(s["lat"]), float(s["lon"]))
        except Exception as e:  # noqa: BLE001 - one bad site must not stop the batch; the error is recorded
            block = {"error": f"{type(e).__name__}: {e}"}
            failed.append(s["id"])
        block.update({"source": SOURCE, "pixel_m": PIXEL_M, "window_m": PIXEL_M * WINDOW_PX,
                      "computed_at": datetime.now(timezone.utc).isoformat(timespec="seconds")})
        s["terrain_v2"] = block
        v = block.get("value", {})
        print(f"  {s['id']}: " + (block.get("error") or " ".join(f"{k}={v[k]}" for k in ("slope_mean", "slope_p95", "roughness_detrended", "traversable_15")) + f" flags={block['flags']}"), flush=True)
    with open(a.output or a.candidates, "w", encoding="utf-8") as fh:
        json.dump(sites, fh, ensure_ascii=False, indent=2)
        fh.write("\n")
    print(f"failed: {failed}" if failed else "all sites computed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
