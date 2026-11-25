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


def outcome(windows: int, cells: int, masked_share: float, literature_match) -> tuple[str, str]:
    """Outcome of a dossier, by a rule fixed before writing any dossier (T43), in this order:
    1. under 10 windows per cell on average: explained artefact (cells cut by 1° tile edges, a few windows each);
    2. at least 20% of windows masked: explained artefact (the typical windows are remnants between hidden ground);
    3. otherwise plausible when the literature describes matching relief, unknown when it says nothing."""
    if windows / max(cells, 1) < 10:
        return "explained artefact", "tile-edge fragments: cells cut by the 1° tile edges keep a few windows each"
    if masked_share >= 0.2:
        return "explained artefact", "remnants between hidden ground: the compared windows lie between masked fields, forest, water or buildings"
    if literature_match:
        return "plausible", "relief described in the literature matches the measured slope distribution"
    return "unknown", "no literature found on the relief of this place"


PALETTE = {0: (255, 255, 255), 1: (225, 225, 225), 2: (150, 150, 150), 3: (200, 30, 30)}   # sea, hidden, evaluated, zone


def write_png_rgb(path: Path, img: np.ndarray) -> None:
    """8-bit RGB PNG, no dependency."""
    h, w, _ = img.shape
    raw = b"".join(b"\x00" + img[r].astype(np.uint8).tobytes() for r in range(h))

    def chunk(kind: bytes, data: bytes) -> bytes:
        return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", zlib.crc32(kind + data) & 0xFFFFFFFF)

    png = b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0))
    png += chunk(b"IDAT", zlib.compress(raw, 9)) + chunk(b"IEND", b"")
    Path(path).write_bytes(png)


def world_map(lat: np.ndarray, lon: np.ndarray, cls: np.ndarray, deg: float = 0.1) -> np.ndarray:
    """Equirectangular map; each cell paints its pixel with the highest class seen there
    (1 hidden or screened out, 2 evaluated, 3 in a candidate zone)."""
    h, w = int(round(180 / deg)), int(round(360 / deg))
    grid = np.zeros((h, w), np.uint8)
    r = np.clip(((90 - lat) / deg).astype(int), 0, h - 1)
    c = np.clip((((lon + 180) % 360) / deg).astype(int), 0, w - 1)
    np.maximum.at(grid, (r, c), cls.astype(np.uint8))
    img = np.zeros((h, w, 3), np.uint8)
    for k, col in PALETTE.items():
        img[grid == k] = col
    return img


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


def known_place(earlier: list[dict], lat: float, lon: float) -> str | None:
    """Place name of a zone with the same centre in the facts of an earlier run (Nominatim: never query twice)."""
    for facts in earlier:
        for f in facts.values():
            if abs(f.get("lat", 1e9) - lat) < 1e-6 and abs(f.get("lon", 1e9) - lon) < 1e-6 and f.get("place"):
                return str(f["place"])
    return None


def zone_hillshade(zone: dict, cache: Path, out_png: Path, pixel_m: float = 40.0, half_km: float = 15.0) -> None:
    """Hillshade of a square of 2 x half_km around the zone centre, on a local equal-area grid."""
    import rasterio
    from rasterio.transform import from_origin
    from rasterio.warp import Resampling, reproject
    from discovery.copernicus import tile_name
    from discovery.discover import PRODUCT                       # glo30 for the Moon, glo90 for the Mars run (T48)
    from discovery.grid import laea
    n = int(2 * half_km * 1000 / pixel_m)
    dst = np.full((n, n), np.nan, "float32")
    crs = laea(zone["lat"], zone["lon"])
    tf = from_origin(-half_km * 1000, half_km * 1000, pixel_m, pixel_m)
    la0, lo0 = int(np.floor(zone["lat"])), int(np.floor(zone["lon"]))
    for la in (la0 - 1, la0, la0 + 1):
        for lo in (lo0 - 1, lo0, lo0 + 1):
            f = cache / f"{tile_name(la, (lo + 180) % 360 - 180, PRODUCT)}.tif"
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
    ap.add_argument("--reuse", type=Path, nargs="*", default=[], help="facts.json of earlier runs: their names are reused")
    a = ap.parse_args(argv)
    earlier = [json.loads(p.read_text(encoding="utf-8")) for p in a.reuse if p.exists()]
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
            facts[zid] = {**{k: z[k] for k in z if k not in ("tiles",)}, "place": known_place(earlier, z["lat"], z["lon"]) or place_name(z["lat"], z["lon"]),
                          "cell_medians": [round(float(m), 4) for m in med if m is not None],
                          "mc_top_decile_share": match.get("mc_top_decile_share")}
            print(zid, facts[zid]["place"][:80], flush=True)
    (a.out / "zones" / "facts.json").write_text(json.dumps(facts, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    # one world map per scenario and target: hidden or mostly masked (1), evaluated (2), in a default zone (3);
    # white is sea, or land screened out at 90 m (no refined cell)
    lat = np.array([np.nan if v is None else v for v in cells["lat"]], float)
    lon = np.array([np.nan if v is None else v for v in cells["lon"]], float)
    ms = np.array([1.0 if v is None else v for v in cells["masked_share"]], float)
    ok = np.isfinite(lat) & np.isfinite(lon)
    pos = {c: i for i, c in enumerate(cells["cell"])}              # built once: np.isin on text ids is very slow
    for sc, v in zones.items():
        for t in v["targets"]:
            med = np.array([np.nan if x is None else x for x in cells.get(f"{t}:median", [None] * lat.size)], float)
            cls = np.where(ms >= 0.5, 1, np.where(np.isfinite(med), 2, 1))
            zfile = a.run / f"zones-{sc}-{t}.json"
            in_zone = np.zeros(lat.size, bool)
            in_zone[[pos[c] for z in json.loads(zfile.read_text()) for c in z["cell_ids"] if c in pos]] = True
            cls = np.where(in_zone, 3, cls)
            write_png_rgb(a.out / f"map-{sc}-{t}.png", world_map(lat[ok], lon[ok], cls[ok], deg=0.1))
            print("map", sc, t, flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
