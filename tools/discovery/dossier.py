"""Dossiers of the top unexpected zones (T43, validation-protocol section 5).

Each dossier gives the zone's data with spread, a hillshade of the Copernicus DEM (no optical imagery is used: the
picture shows relief only), the place name from OpenStreetMap Nominatim (reverse geocoding, at most one request
per second, generic User-Agent), and leaves the literature search and the outcome to be written from recorded
queries. The outcome is one of: plausible, explained artefact, unknown.

    PYTHONPATH=tools python tools/discovery/dossier.py --run /data/run001 --cache /glo30 --out docs/wiki/runs/run-001
"""
from __future__ import annotations

import argparse
import json
import struct
import sys
import time
import zlib
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

UA = "earthmoon-research/1.0"


# --- pure part (tested) ------------------------------------------------------------------------------------

def hillshade(z: np.ndarray, pixel_m: float, azimuth: float = 315.0, altitude: float = 45.0) -> np.ndarray:
    """Lambertian hillshade, 0..255 (missing pixels are 0)."""
    gy, gx = np.gradient(np.asarray(z, float), pixel_m)
    slope = np.arctan(np.hypot(gx, gy))
    aspect = np.arctan2(-gx, gy)
    az, alt = np.radians(azimuth), np.radians(altitude)
    s = np.sin(alt) * np.cos(slope) + np.cos(alt) * np.sin(slope) * np.cos(az - aspect)
    return np.where(np.isfinite(s), np.clip(s, 0, 1) * 255, 0).astype(np.uint8)


def write_png(path: Path, img: np.ndarray) -> None:
    """8-bit greyscale PNG, no dependency."""
    h, w = img.shape
    raw = b"".join(b"\x00" + bytes(img[r]) for r in range(h))

    def chunk(kind: bytes, data: bytes) -> bytes:
        return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", zlib.crc32(kind + data) & 0xFFFFFFFF)

    png = b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 0, 0, 0, 0))
    png += chunk(b"IDAT", zlib.compress(raw, 9)) + chunk(b"IEND", b"")
    Path(path).write_bytes(png)


# --- IO ----------------------------------------------------------------------------------------------------

def place_name(lat: float, lon: float) -> str:
    import urllib.parse
    import urllib.request
    q = urllib.parse.urlencode({"lat": f"{lat:.5f}", "lon": f"{lon:.5f}", "format": "jsonv2", "zoom": 10})
    req = urllib.request.Request(f"https://nominatim.openstreetmap.org/reverse?{q}", headers={"User-Agent": UA})
    time.sleep(1.1)                                                   # Nominatim usage policy: 1 request per second
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.loads(r.read().decode()).get("display_name", "no name returned")
    except OSError as e:
        return f"not resolved ({type(e).__name__})"


def zone_hillshade(zone: dict, cache: Path, out_png: Path, pixel_m: float = 40.0, half_km: float = 15.0) -> None:
    """Hillshade of a square of 2 x half_km around the zone centre, on a local equal-area grid."""
    import rasterio
    from rasterio.transform import from_origin
    from rasterio.warp import Resampling, reproject
    from discovery.copernicus import tile_name
    from discovery.grid import laea
    n = int(2 * half_km * 1000 / pixel_m)
    dst = np.full((n, n), np.nan, "float32")
    crs = laea(zone["lat"], zone["lon"])
    tf = from_origin(-half_km * 1000, half_km * 1000, pixel_m, pixel_m)
    la0, lo0 = int(np.floor(zone["lat"])), int(np.floor(zone["lon"]))
    for la in (la0 - 1, la0, la0 + 1):
        for lo in (lo0 - 1, lo0, lo0 + 1):
            f = cache / f"{tile_name(la, (lo + 180) % 360 - 180, 'glo30')}.tif"
            if not f.exists():
                continue
            with rasterio.open(f) as src:
                part = np.full((n, n), np.nan, "float32")
                reproject(rasterio.band(src, 1), part, src_nodata=0, dst_transform=tf, dst_crs=crs, dst_nodata=np.nan,
                          resampling=Resampling.bilinear)
            dst = np.where(np.isfinite(part), part, dst)
    write_png(out_png, hillshade(dst, pixel_m))


def main(argv=None) -> int:
    from discovery.discover import load_cells
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--run", type=Path, required=True)
    ap.add_argument("--cache", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    a = ap.parse_args(argv)
    zones = json.loads((a.run / "zones.json").read_text())["scenarios"]
    cells = load_cells(str(a.run / "cells.parquet"))
    by_id = {c: i for i, c in enumerate(cells["cell"])}
    (a.out / "zones").mkdir(parents=True, exist_ok=True)
    facts = {}
    for sc, v in zones.items():
        for rank, z in enumerate(v["dossier_zones"], 1):
            zid = f"{sc}-{rank:02d}"
            full = json.loads((a.run / f"zones-{sc}-{z['target']}.json").read_text())
            match = next(x for x in full if abs(x["lat"] - z["lat"]) < 1e-6 and abs(x["lon"] - z["lon"]) < 1e-6)
            idx = [by_id[c] for c in match["cell_ids"] if c in by_id]
            med = [cells[f"{z['target']}:median"][i] for i in idx]
            zone_hillshade(z, a.cache, a.out / "zones" / f"{zid}.png")
            facts[zid] = {**{k: z[k] for k in z if k not in ("tiles",)}, "place": place_name(z["lat"], z["lon"]),
                          "cell_medians": [round(float(m), 4) for m in med if m is not None],
                          "mc_top_decile_share": match.get("mc_top_decile_share")}
            print(zid, facts[zid]["place"][:80], flush=True)
    (a.out / "zones" / "facts.json").write_text(json.dumps(facts, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
