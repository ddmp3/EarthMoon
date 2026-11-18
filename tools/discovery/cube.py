"""Earth feature cube, topography (T40, ADR-001/002/007/009).

For one 1° tile and one pixel scale: read the Copernicus DEM tile and its existing neighbours onto the tile's
local equal-area grid (bilinear; sea is 0 m in the product and is read as missing), compute the 1 km window
metrics, the ESA WorldCover class fractions of each window, and the 5 km cell statistics. Write two Parquet
tables and one manifest line keyed by sha256(input keys + code commit + parameters).

    python tools/discovery/cube.py --product glo90 --pixel 90 --tiles all --out /data/cube --workers 8
    python tools/discovery/cube.py --product glo30 --pixel 40 --tiles pilot --out /data/cube
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
from discovery.cells import cell_table  # noqa: E402
from discovery import worldcover  # noqa: E402
from discovery.copernicus import PRODUCTS, list_tiles, local_copy, neighbours, tile_name, tile_url  # noqa: E402
from discovery.grid import TileGrid, tile_grid  # noqa: E402
from discovery.keys import content_key  # noqa: E402
from discovery.windows import STORED_METRICS, window_metrics_grid  # noqa: E402

WINDOW_M = 1000.0
CELL_M = 5000.0
GDAL_ENV = {"GDAL_DISABLE_READDIR_ON_OPEN": "EMPTY_DIR", "CPL_VSIL_CURL_ALLOWED_EXTENSIONS": ".tif",
            "GDAL_HTTP_MAX_RETRY": "5", "GDAL_HTTP_RETRY_DELAY": "2", "GDAL_HTTP_MULTIRANGE": "YES",
            "VSI_CACHE": "TRUE", "VSI_CACHE_SIZE": "50000000"}


# --- pure part (tested) ------------------------------------------------------------------------------------

def compute_tile(z: np.ndarray, grid: TileGrid, classes: dict[str, np.ndarray] | None = None):
    """Windows and cells of one tile from its elevation grid (NaN = missing). `classes`: per-pixel fractions
    (0..1) of each mask class on the same grid, or None when the mask is not read."""
    w = window_metrics_grid(z, grid.pixel_m, grid.window_px, grid.margin_px)
    owned = grid.owned()
    lat, lon = grid.window_centres_latlon()
    ci, cj = grid.cells(CELL_M)
    if classes:
        n, m = grid.window_px, grid.margin_px
        for name, frac in classes.items():
            core = frac[m:m + grid.rows * n, m:m + grid.cols * n]
            w[f"wc_{name}"] = core.reshape(grid.rows, n, grid.cols, n).mean(axis=(1, 3))
    cell_id = (ci - ci.min()) * 100_000 + (cj - cj.min())
    cells = cell_table(w, cell_id, owned, STORED_METRICS)
    # cell centres: mean of the owned window centres; mask fractions: mean over owned windows
    for cid, row in cells.items():
        sel = owned & (cell_id == cid)
        row.update({"i": int(ci[sel][0]), "j": int(cj[sel][0]), "lat": float(lat[sel].mean()), "lon": float(lon[sel].mean()),
                    "area_km2": float(sel.sum() * (grid.window_m / 1000) ** 2),
                    "flat_windows": int(w["flat"][sel].sum())})
        for name in (classes or {}):
            row[f"wc_{name}"] = float(np.nanmean(w[f"wc_{name}"][sel]))
    windows = {"row": np.indices(owned.shape)[0][owned], "col": np.indices(owned.shape)[1][owned],
               "lat": lat[owned], "lon": lon[owned], "i": ci[owned], "j": cj[owned]}
    for k, v in w.items():
        windows[k] = v[owned]
    return windows, cells


def coverage(cells: dict) -> dict:
    out = {"evaluated": 0, "partial": 0, "missing": 0}
    for row in cells.values():
        out[row["state"]] += 1
    return out


# --- data access (network) ---------------------------------------------------------------------------------

def read_dem(grid: TileGrid, product: str, have: set, cache: Path | None) -> tuple[np.ndarray, dict]:
    """Elevation on the grid from the tile and its existing neighbours; sha256 of local copies."""
    import rasterio
    from rasterio.warp import Resampling, reproject
    dst = np.full(grid.shape, np.nan, dtype="float32")
    shas = {}
    for la, lo in neighbours(grid.lat, grid.lon, have):
        src_path = cache / f"{tile_name(la, lo, product)}.tif" if cache else tile_url(la, lo, product)
        if cache:
            shas[(la, lo)] = json.loads((cache / f"{tile_name(la, lo, product)}.json").read_text())["sha256"]
        part = np.full(grid.shape, np.nan, dtype="float32")
        with rasterio.open(src_path) as src:
            reproject(rasterio.band(src, 1), part, src_nodata=0.0, dst_transform=grid.transform, dst_crs=grid.crs,
                      dst_nodata=np.nan, resampling=Resampling.bilinear)
        dst = np.where(np.isfinite(part), part, dst)
    return dst, shas


CODE_FILES = ("discovery/windows.py", "discovery/cells.py", "discovery/grid.py", "discovery/cube.py",
              "discovery/copernicus.py", "discovery/worldcover.py", "discovery/keys.py", "precompute/terrain_metrics.py")


def code_version(root: Path = Path(__file__).resolve().parents[1]) -> str:
    """sha256 of the source files that compute the cube (line endings normalised). A commit that touches only
    tests or docs leaves it unchanged, so it does not force a recompute (ADR-009)."""
    h = hashlib.sha256()
    for name in CODE_FILES:
        h.update(name.encode() + b"\0" + (root / name).read_bytes().replace(b"\r\n", b"\n") + b"\0")
    return h.hexdigest()


def git_commit() -> str:
    """The commit the run started from, for provenance only."""
    import subprocess
    try:
        out = subprocess.run(["git", "describe", "--always", "--dirty", "--abbrev=40"], capture_output=True, text=True,
                             cwd=Path(__file__).resolve().parent, check=True).stdout.strip()
        return out or "unknown"
    except (OSError, subprocess.CalledProcessError):
        return os.environ.get("EARTHMOON_COMMIT", "unknown")


def _write(path: Path, table: dict) -> str:
    import pyarrow as pa
    import pyarrow.parquet as pq
    cols = {}
    for k, v in table.items():
        a = np.asarray(v)
        cols[k] = pa.array(a.astype("float32") if a.dtype.kind == "f" and k not in ("lat", "lon") else a)
    pq.write_table(pa.table(cols), path, compression="zstd")
    return hashlib.sha256(path.read_bytes()).hexdigest()


def process(lat: int, lon: int, product: str, pixel: float, out: Path, listing: dict, commit: str,
            wc: dict | None, cache: Path | None) -> dict:
    os.environ.update(GDAL_ENV)
    t0 = time.time()
    grid = tile_grid(lat, lon, pixel, WINDOW_M)
    have = set(listing)
    inputs = {listing[n]["key"]: {k: listing[n][k] for k in ("etag", "size", "last_modified")}
              for n in neighbours(lat, lon, have)}
    params = {"product": product, "pixel_m": pixel, "window_m": WINDOW_M, "cell_m": CELL_M, "mask": wc is not None,
              "metrics": list(STORED_METRICS)}
    z, shas = read_dem(grid, product, have, cache)
    for t, sha in shas.items():
        inputs[listing[t]["key"]]["sha256"] = sha
    t_read = time.time() - t0
    classes, used = worldcover.read(grid, wc) if wc is not None else ({}, {})
    inputs.update(used)
    t_mask = time.time() - t0 - t_read
    windows, cells = compute_tile(z, grid, classes)
    name = tile_name(lat, lon, product)
    out.mkdir(parents=True, exist_ok=True)
    cell_cols: dict = {"cell": [f"{name}:{r['i']}:{r['j']}" for r in cells.values()]}
    for k in next(iter(cells.values()), {}):
        cell_cols[k] = [r[k] for r in cells.values()]
    sha_w = _write(out / f"{name}.windows.parquet", windows)
    sha_c = _write(out / f"{name}.cells.parquet", cell_cols)
    return {"tile": name, "lat": lat, "lon": lon, "key": content_key(inputs, commit, params), "inputs": inputs,
            "code": commit, "commit": git_commit(), "params": params, "outputs": {"windows": sha_w, "cells": sha_c},
            "windows": int(len(windows["row"])), "valid_windows": int(np.isfinite(windows["slope_mean"]).sum()),
            "cells": coverage(cells), "seconds": {"read": round(t_read, 2), "mask": round(t_mask, 2),
                                                  "total": round(time.time() - t0, 2)}}


def done_keys(manifest: Path) -> dict:
    out = {}
    if manifest.exists():
        for line in manifest.read_text(encoding="utf-8").splitlines():
            if line.strip():
                rec = json.loads(line)
                out[rec["tile"]] = rec
    return out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--product", choices=sorted(PRODUCTS), required=True)
    ap.add_argument("--pixel", type=float, required=True)
    ap.add_argument("--tiles", default="all", help="'all', or a file of 'lat,lon' lines")
    ap.add_argument("--out", required=True)
    ap.add_argument("--workers", type=int, default=8)
    ap.add_argument("--no-mask", action="store_true")
    ap.add_argument("--cache", help="download tiles once into this folder, with SHA-256 (GLO-90); else stream")
    a = ap.parse_args(argv)
    os.environ.update(GDAL_ENV)
    out = Path(a.out) / f"{a.product}-{int(a.pixel)}m"
    out.mkdir(parents=True, exist_ok=True)
    listing = {tuple(map(int, k.split(","))): v for k, v in _cached(out / "listing.json", lambda: {
        f"{k[0]},{k[1]}": v for k, v in sorted(list_tiles(a.product).items())}).items()}
    wc = None if a.no_mask else _cached(out / "worldcover-listing.json", worldcover.listing)
    tiles = sorted(listing) if a.tiles == "all" else [
        t for t in (tuple(int(x) for x in line.split(",")) for line in Path(a.tiles).read_text().split()) if t in listing]
    commit = code_version()
    manifest = out / "manifest.jsonl"
    done = done_keys(manifest)
    todo = [t for t in tiles if not _up_to_date(done.get(tile_name(*t, a.product)), t, listing, commit, out, a.product)]
    print(f"{len(tiles)} tiles, {len(tiles) - len(todo)} unchanged and done with this code, {len(todo)} to run", flush=True)
    cache = Path(a.cache) if a.cache else None
    if cache:
        cache.mkdir(parents=True, exist_ok=True)
        need = sorted({n for t in todo for n in neighbours(*t, set(listing))})
        t0 = time.time()
        from concurrent.futures import ThreadPoolExecutor
        with ThreadPoolExecutor(max_workers=16) as tp:
            for i, _ in enumerate(tp.map(lambda t: local_copy(*t, a.product, cache, listing[t]), need), 1):
                if i % 500 == 0 or i == len(need):
                    print(f"download {i}/{len(need)}, {(time.time() - t0) / 3600:.2f} h", flush=True)
    t0, n, failed = time.time(), 0, []
    with ProcessPoolExecutor(max_workers=a.workers) as pool, manifest.open("a", encoding="utf-8") as fh:
        futs = {pool.submit(process, la, lo, a.product, a.pixel, out, listing, commit, wc, cache): (la, lo)
                for la, lo in todo}
        for f in as_completed(futs):
            try:
                rec = f.result()
            except (OSError, RuntimeError, ValueError) as e:  # one failing tile is recorded and retried next run
                failed.append({"tile": futs[f], "error": f"{type(e).__name__}: {e}"})
                continue
            fh.write(json.dumps(rec) + "\n")
            fh.flush()
            n += 1
            if n % 100 == 0 or n == len(todo):
                el = time.time() - t0
                print(f"{n}/{len(todo)} tiles, {el / 3600:.2f} h, {n / el * 3600:.0f} tiles/h", flush=True)
    (out / "failed.json").write_text(json.dumps(failed, indent=1))
    print(f"done {n}, failed {len(failed)}", flush=True)
    return 1 if failed else 0


def _cached(path: Path, build):
    if path.exists():
        return json.loads(path.read_text())
    data = build()
    path.write_text(json.dumps(data))
    return data


def _up_to_date(rec: dict | None, tile, listing: dict, commit: str, out: Path, product: str) -> bool:
    """Done with the same code and the same DEM signals (ETags), and its outputs are still there (ADR-009)."""
    if not rec or rec["code"] != commit:
        return False
    for n in neighbours(*tile, set(listing)):
        k = listing[n]["key"]
        if rec["inputs"].get(k, {}).get("etag") != listing[n]["etag"]:
            return False
    name = tile_name(*tile, product)
    return all((out / f"{name}.{t}.parquet").exists() for t in ("windows", "cells"))


if __name__ == "__main__":
    sys.exit(main())
