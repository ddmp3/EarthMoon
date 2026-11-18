"""Lunar window cube from SLDEM2015 (T41): every 1 km window between 60°S and 60°N, measured by the Earth code.

Each 1° tile is read from SLDEM2015 (512 ppd, bilinear) onto its local equal-area grid on the lunar sphere
(`moon_grid`), at the SLDEM pixel size (59.225 m), with 17-pixel windows (1006.8 m). For each owned window the
table keeps its centre, the terrain metrics, the Lunar Prospector FeO bin value at the centre, and the geologic unit
of the Unified Geologic Map (majority of 5 x 5 samples, with its share). Profiles select windows from it.

    python tools/discovery/moon_cube.py --sldem /data/sldem2015 --geology GeoUnits.shp --iron ironhd.txt \
        --out /data/moon-cube --workers 12
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "precompute"))
from discovery.moon_grid import GEO, SldemIndex, moon_tile_grid  # noqa: E402
from discovery.windows import ALL_METRICS, window_metrics_grid  # noqa: E402

PIXEL_M = 59.225293836                     # SLDEM2015 512 ppd at the equator (label: 0.0592252938 km)
WINDOW_M = 1000.0
UNITS_PPD = 64
SAMPLES = 5                                # unit samples per window side
CODE_FILES = ("discovery/moon_cube.py", "discovery/moon_grid.py", "discovery/grid.py", "discovery/windows.py",
              "precompute/terrain_metrics.py")


# --- pure part (tested) ------------------------------------------------------------------------------------

def otsu_split(values: np.ndarray, weights: np.ndarray, bins: int = 256) -> float:
    """Two-class split of a weighted histogram that maximises the between-class variance (Otsu)."""
    ok = np.isfinite(values)
    h, edges = np.histogram(values[ok], bins=bins, weights=weights[ok])
    mid = (edges[:-1] + edges[1:]) / 2
    w0 = np.cumsum(h)
    w1 = w0[-1] - w0
    m0 = np.cumsum(h * mid) / np.where(w0 > 0, w0, 1)
    m1 = (np.sum(h * mid) - np.cumsum(h * mid)) / np.where(w1 > 0, w1, 1)
    between = w0 * w1 * (m0 - m1) ** 2
    best = np.flatnonzero(between >= between.max() * (1 - 1e-9))   # a plateau when the classes do not touch
    return float((edges[best[0] + 1] + edges[best[-1] + 1]) / 2)


def grid_lookup(grid: np.ndarray, lat: np.ndarray, lon: np.ndarray, lat_top: float, lon_left: float) -> np.ndarray:
    """Value of the regular latitude-longitude grid cell containing each point (longitudes east or signed)."""
    rows, cols = grid.shape
    dlat, dlon = 180.0 / rows, 360.0 / cols
    r = np.clip(((lat_top - lat) / dlat).astype(int), 0, rows - 1)
    c = np.floor((((lon - lon_left) % 360.0)) / dlon).astype(int) % cols
    return grid[r, c]


def unit_share(samples: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Majority value of each row (ties to the lowest) and its share. 0 means no mapped unit."""
    n = samples.shape[1]
    counts = np.zeros((samples.shape[0], int(samples.max()) + 1), int)
    np.add.at(counts, (np.repeat(np.arange(samples.shape[0]), n), samples.ravel()), 1)
    unit = counts.argmax(axis=1)
    return unit, counts.max(axis=1) / n


# --- inputs ------------------------------------------------------------------------------------------------

def read_iron(path: Path) -> np.ndarray:
    """Lunar Prospector FeO wt% on 0.5° bins: 360 rows from 90°N, 720 columns from 180°W (ironhd.txt)."""
    out = np.full((360, 720), np.nan)
    for line in path.read_text().splitlines():
        if line.startswith("#") or not line.strip():
            continue
        lat0, _, lon0, _, v = (float(x) for x in line.split(","))
        out[int(round((89.5 - lat0) * 2)), int(round((lon0 + 180) * 2))] = v
    return out


def rasterize_units(shp: Path, ppd: int = UNITS_PPD) -> tuple[np.ndarray, list[str]]:
    """Unit index (1..n, 0 = none) on a global grid from 90°N and 180°W; codes[i - 1] is unit i."""
    import shapefile
    from rasterio.features import rasterize
    from rasterio.transform import from_origin
    r = shapefile.Reader(str(shp))
    codes = sorted({rec[0] for rec in r.iterRecords(fields=["FIRST_Unit"])})
    index = {c: i + 1 for i, c in enumerate(codes)}
    k = 1737400.0 * np.pi / 180.0                                        # metres per degree (equidistant)
    shapes = ((sr.shape.__geo_interface__, index[sr.record[0]]) for sr in r.iterShapeRecords(fields=["FIRST_Unit"]))
    px = k / ppd
    grid = rasterize(shapes, out_shape=(180 * ppd, 360 * ppd), transform=from_origin(-180 * k, 90 * k, px, px),
                     fill=0, dtype="uint8")
    return grid, codes


# --- one tile ----------------------------------------------------------------------------------------------

def process(lat: int, lon: int, sldem: Path, units: np.ndarray, iron: np.ndarray, out: Path) -> dict:
    import pyarrow as pa
    import pyarrow.parquet as pq
    from rasterio.transform import from_origin
    from rasterio.warp import Resampling, reproject, transform
    t0 = time.time()
    g = moon_tile_grid(lat, lon, PIXEL_M, WINDOW_M)
    pad = 0.4 / max(np.cos(np.radians(min(abs(lat), abs(lat + 1)) + 0.4)), 0.2)
    lo, hi = max(lat - 0.4, -60.0), min(lat + 1.4, 60.0)
    z_src, west, north = SldemIndex(sldem).read(lo, hi, lon - pad, lon + 1 + pad)
    z = np.full(g.shape, np.nan, "float32")
    reproject(z_src, z, src_transform=from_origin(west, north, 1 / 512, 1 / 512), src_crs=GEO, src_nodata=np.nan,
              dst_transform=g.transform, dst_crs=g.crs, dst_nodata=np.nan, resampling=Resampling.bilinear)
    w = window_metrics_grid(z, PIXEL_M, g.window_px, g.margin_px, metrics=ALL_METRICS)
    own = g.owned()
    clat, clon = g.window_centres_latlon()
    # unit samples: SAMPLES x SAMPLES points per window
    x, y = g.window_centres_xy()
    off = (np.arange(SAMPLES) + 0.5) / SAMPLES - 0.5
    ox, oy = np.meshgrid(off * g.window_m, off * g.window_m)
    sx = (x[own][:, None] + ox.ravel()[None, :]).ravel()
    sy = (y[own][:, None] - oy.ravel()[None, :]).ravel()
    slon, slat = transform(g.crs, GEO, sx.tolist(), sy.tolist())
    samples = grid_lookup(units, np.array(slat), np.array(slon), 90, -180).reshape(-1, SAMPLES * SAMPLES)
    unit, share = unit_share(samples) if samples.size else (np.zeros(0, int), np.zeros(0))
    table = {"lat": clat[own], "lon": clon[own] % 360, "valid_frac": w["valid_frac"][own].astype("float32"),
             "fe": grid_lookup(iron, clat[own], clon[own], 90, -180).astype("float32"),
             "unit": unit.astype("uint8"), "unit_share": share.astype("float32")}
    for k in ALL_METRICS:
        table[k] = w[k][own].astype("float32")
    name = f"moon_{'N' if lat >= 0 else 'S'}{abs(lat):02d}_E{lon:03d}"
    path = out / f"{name}.windows.parquet"
    pq.write_table(pa.table(table), path, compression="zstd")
    return {"tile": name, "lat": lat, "lon": lon, "windows": int(own.sum()),
            "valid_windows": int(np.isfinite(w["slope_mean"][own]).sum()),
            "sha256": hashlib.sha256(path.read_bytes()).hexdigest(), "seconds": round(time.time() - t0, 2)}


def _sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 24), b""):
            h.update(chunk)
    return h.hexdigest()


def code_version(root: Path = Path(__file__).resolve().parents[1]) -> str:
    h = hashlib.sha256()
    for name in CODE_FILES:
        h.update(name.encode() + b"\0" + (root / name).read_bytes().replace(b"\r\n", b"\n") + b"\0")
    return h.hexdigest()


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--sldem", type=Path, required=True)
    ap.add_argument("--geology", type=Path, required=True)
    ap.add_argument("--iron", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--workers", type=int, default=8)
    ap.add_argument("--tiles", default="all", help="all, or lat,lon pairs separated by ';'")
    a = ap.parse_args(argv)
    out = a.out / "sldem2015-59m"
    out.mkdir(parents=True, exist_ok=True)
    units_npy = a.out / f"units_{UNITS_PPD}ppd.npy"
    if not units_npy.exists():
        grid, codes = rasterize_units(a.geology)
        np.save(units_npy, grid)
        (a.out / "units_codes.json").write_text(json.dumps(codes) + "\n")
    inputs_json = a.out / "inputs.json"
    if not inputs_json.exists():                                       # sha256 of every source file, once
        files = sorted(a.sldem.glob("SLDEM2015_512_*_FLOAT.IMG")) + [a.iron] + sorted(a.geology.parent.glob(a.geology.stem + ".*"))
        inputs_json.write_text(json.dumps({f.name: {"size": f.stat().st_size, "sha256": _sha(f)} for f in files},
                                          indent=1) + "\n")
    units = np.load(units_npy, mmap_mode="r")
    iron = read_iron(a.iron)
    tiles = [(la, lo) for la in range(-60, 60) for lo in range(360)] if a.tiles == "all" else \
        [tuple(int(v) for v in t.split(",")) for t in a.tiles.split(";")]
    manifest = out / "manifest.jsonl"
    done = {json.loads(x)["tile"] for x in manifest.read_text().splitlines()} if manifest.exists() else set()
    code = code_version()
    commit = os.environ.get("EARTHMOON_COMMIT", "unknown")
    todo = [t for t in tiles if f"moon_{'N' if t[0] >= 0 else 'S'}{abs(t[0]):02d}_E{t[1]:03d}" not in done]
    print(f"{len(tiles)} tiles, {len(todo)} to run", flush=True)
    t0, n, failed = time.time(), 0, []
    with ProcessPoolExecutor(max_workers=a.workers) as pool, manifest.open("a", encoding="utf-8") as fh:
        futs = {pool.submit(process, la, lo, a.sldem, units, iron, out): (la, lo) for la, lo in todo}
        for f in as_completed(futs):
            try:
                rec = f.result()
            except (OSError, RuntimeError, ValueError) as e:
                failed.append({"tile": futs[f], "error": f"{type(e).__name__}: {e}"})
                continue
            fh.write(json.dumps({**rec, "code": code, "commit": commit}) + "\n")
            fh.flush()
            n += 1
            if n % 500 == 0 or n == len(todo):
                print(f"{n}/{len(todo)} tiles, {(time.time() - t0) / 3600:.2f} h", flush=True)
    (out / "failed.json").write_text(json.dumps(failed, indent=1) + "\n")
    print(f"done {n}, failed {len(failed)}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
