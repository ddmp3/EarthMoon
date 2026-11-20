"""Raster XYZ map tiles of a release, zoom 0 to 7 (T44, ADR-002, docs/wiki/ui/map-spec.md).

Each pixel shows the HEALPix cell that holds its centre, so tiles of every zoom agree with the cells served at zoom
8 and above. The states are drawn into the tile, so the browser needs no library beyond Leaflet:
- value layer: cividis colour on evaluated cells, pastel hatching over partial cells, grey dots where nothing was
  evaluated, an outline only where the ground is hidden;
- coverage overlay: transparent where the cell is evaluated, a pattern per class elsewhere.
Patterns follow global pixel coordinates, so neighbouring tiles join without a seam.

    PYTHONPATH=tools python tools/discovery/tiles.py --run /data/run002 --release /data/releases/<id>
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from discovery.healpix import NSIDE, ang2pix  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
SIZE = 256
MAX_ZOOM = 7
PASTEL = (185, 198, 232)                                      # #b9c6e8, the v2 hatching colour
GREY = (128, 128, 128)
OUTLINE = (210, 210, 210)
CLASS_CODE = {"evaluated": 1, "low_confidence": 2, "partial": 3, "ground_hidden": 4, "no_data": 5, "screened_out": 6}
CIVIDIS = np.array(json.loads((ROOT / "data/ui/cividis.json").read_text(encoding="utf-8"))["rgb"], np.uint8)


def pixel_latlon(z: int, x: int, y: int) -> tuple[np.ndarray, np.ndarray]:
    """Latitude and longitude of the centre of each pixel of tile z/x/y (Web Mercator)."""
    n = SIZE * 2 ** z
    gx = (x * SIZE + np.arange(SIZE) + 0.5) / n
    gy = (y * SIZE + np.arange(SIZE) + 0.5) / n
    lon = gx * 360.0 - 180.0
    lat = np.degrees(np.arctan(np.sinh(np.pi * (1 - 2 * gy))))
    return np.repeat(lat[:, None], SIZE, 1), np.repeat(lon[None, :], SIZE, 0)


def pixel_cells(z: int, x: int, y: int) -> np.ndarray:
    lat, lon = pixel_latlon(z, x, y)
    return ang2pix(NSIDE, lat.ravel(), lon.ravel()).reshape(SIZE, SIZE)


def cell_codes(classes: np.ndarray) -> np.ndarray:
    return np.array([CLASS_CODE[c] for c in classes], np.uint8)


def _lookup(cells: np.ndarray, ids: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    k = np.clip(np.searchsorted(ids, cells), 0, max(ids.size - 1, 0))
    return k, (ids[k] == cells) if ids.size else np.zeros(cells.shape, bool)


def _global(z: int, x: int, y: int) -> tuple[np.ndarray, np.ndarray]:
    gx = x * SIZE + np.arange(SIZE)[None, :]
    gy = y * SIZE + np.arange(SIZE)[:, None]
    return np.broadcast_to(gx, (SIZE, SIZE)), np.broadcast_to(gy, (SIZE, SIZE))


def _edges(cells: np.ndarray) -> np.ndarray:
    e = np.zeros(cells.shape, bool)
    e[:, :-1] |= cells[:, :-1] != cells[:, 1:]
    e[:-1, :] |= cells[:-1, :] != cells[1:, :]
    return e


def _codes(cells: np.ndarray, ids: np.ndarray, codes: np.ndarray, land: np.ndarray | None) -> tuple[np.ndarray, np.ndarray]:
    k, hit = _lookup(cells, ids)
    code = np.where(hit, codes[k] if codes.size else 0, 0).astype(np.uint8)
    if land is not None and land.size:
        _, on_land = _lookup(cells, land)
        code[~hit & on_land] = CLASS_CODE["screened_out"]      # land outside every assessed cell
    return code, k


def render_value(cells: np.ndarray, ids: np.ndarray, value: np.ndarray, codes: np.ndarray, z: int, x: int, y: int,
                 land: np.ndarray | None = None) -> np.ndarray:
    """RGBA tile of one value layer (typicality 0..1)."""
    code, k = _codes(cells, ids, codes, land)
    v = np.asarray(value, float)[k] if ids.size else np.full(cells.shape, np.nan)
    gx, gy = _global(z, x, y)
    img = np.zeros((SIZE, SIZE, 4), np.uint8)
    coloured = np.isin(code, [1, 2, 3]) & np.isfinite(v)
    img[coloured, :3] = CIVIDIS[np.clip((np.nan_to_num(v[coloured]) * 255).round().astype(int), 0, 255)]
    img[coloured, 3] = 255
    hatch = coloured & (code == 3) & ((gx + gy) % 6 == 0)
    img[hatch] = (*PASTEL, 255)
    none = (np.isin(code, [5, 6]) | (np.isin(code, [1, 2, 3]) & ~np.isfinite(v))) & (gx % 4 == 0) & (gy % 4 == 0)
    img[none] = (*GREY, 255)
    outline = (code == 4) & _edges(cells)
    img[outline] = (*OUTLINE, 180)
    return img


def render_coverage(cells: np.ndarray, ids: np.ndarray, codes: np.ndarray, z: int, x: int, y: int,
                    land: np.ndarray | None = None) -> np.ndarray:
    """RGBA tile of the coverage overlay: nothing on evaluated cells, a pattern on every other class."""
    code, _ = _codes(cells, ids, codes, land)
    gx, gy = _global(z, x, y)
    img = np.zeros((SIZE, SIZE, 4), np.uint8)
    img[(code == 5) & ((gx + gy) % 3 == 0)] = (*PASTEL, 230)                   # no data: dense hatching
    img[(code == 4) & ((gx - gy) % 4 == 0)] = (*PASTEL, 230)                   # ground hidden: other angle
    img[(code == 3) & ((gx + gy) % 6 == 0)] = (*PASTEL, 200)                   # partial: light hatching
    img[(code == 6) & (gx % 4 == 0) & (gy % 4 == 0)] = (*GREY, 230)           # screened out: grey dots
    img[(code == 2) & _edges(cells)] = (*PASTEL, 160)                          # low confidence: thin outline
    return img


def tiles_with_cells(ids: np.ndarray, zoom: int) -> set[tuple[int, int, int]]:
    """Tiles of one zoom that hold a cell centre, or a point 0.05° (about 5 km) from it."""
    from discovery.healpix import pix2ang
    lat, lon = pix2ang(NSIDE, np.asarray(ids, np.int64))
    n = 2 ** zoom
    out = set()
    for dlat, dlon in ((0, 0), (0.05, 0), (-0.05, 0), (0, 0.05), (0, -0.05)):
        la = np.clip(lat + dlat, -85.05, 85.05)
        lo = (lon + dlon + 180) % 360 - 180
        tx = np.clip(np.floor((lo + 180) / 360 * n).astype(int), 0, n - 1)
        ty = np.clip(np.floor((1 - np.log(np.tan(np.radians(la)) + 1 / np.cos(np.radians(la))) / np.pi) / 2 * n).astype(int), 0, n - 1)
        out |= {(zoom, int(a), int(b)) for a, b in set(zip(tx.tolist(), ty.tolist()))}
    return out


def write_png(path: Path, img: np.ndarray) -> int:
    from PIL import Image
    path.parent.mkdir(parents=True, exist_ok=True)
    Image.fromarray(img, "RGBA").save(path, optimize=True)
    return path.stat().st_size


# T46 geology: Okabe-Ito colours (colour-blind safe); unresolved or no map is hatched, never a "no match" colour
GEO_COLOURS = {1: (0, 158, 115), 2: (86, 180, 233), 3: (120, 126, 140)}


def geology_class(match, partial, no_match) -> np.ndarray:
    """1 match, 2 partial, 3 no match (majority of the 9 samples), 4 unresolved or no map, 0 not assessed."""
    m, p, n = (np.asarray(a, float) for a in (match, partial, no_match))
    out = np.full(m.shape, 4, np.uint8)
    out[n >= 0.5] = 3
    out[m + p >= 0.5] = 2
    out[m >= 0.5] = 1
    out[~np.isfinite(m)] = 0
    return out


def render_geology(cells: np.ndarray, ids: np.ndarray, gclass: np.ndarray, z: int, x: int, y: int) -> np.ndarray:
    """RGBA tile of the geology layer of one target."""
    k, hit = _lookup(cells, ids)
    g = np.where(hit, np.asarray(gclass)[k] if ids.size else 0, 0)
    gx, gy = _global(z, x, y)
    img = np.zeros((SIZE, SIZE, 4), np.uint8)
    for code, rgb in GEO_COLOURS.items():
        img[g == code] = (*rgb, 255 if code != 3 else 170)
    img[(g == 4) & ((gx + gy) % 3 == 0)] = (*PASTEL, 230)
    return img


_LAYERS: dict = {}


def _init(work: str, names: list[str], has_land: bool) -> None:
    """Per worker: the layer arrays, memory-mapped (never copied into each task)."""
    w = Path(work)
    ids = np.load(w / "ids.npy", mmap_mode="r")
    land = np.load(w / "land.npy", mmap_mode="r") if has_land else None
    for name in names:
        key = name.replace("/", "__")
        codes = np.load(w / f"{key}.codes.npy", mmap_mode="r")
        value = np.load(w / f"{key}.value.npy", mmap_mode="r") if (w / f"{key}.value.npy").exists() else None
        _LAYERS[name] = (ids, value, codes, land)


def _render_job(args) -> tuple[int, int]:
    """One tile of every layer (cells of the tile computed once). Returns (files, bytes)."""
    z, x, y, out = args
    cells = pixel_cells(z, x, y)
    files = size = 0
    for name, (ids, value, codes, land) in _LAYERS.items():
        if name.endswith("/geology"):
            img = render_geology(cells, ids, codes, z, x, y)
        elif value is None:
            img = render_coverage(cells, ids, codes, z, x, y, land)
        else:
            img = render_value(cells, ids, value, codes, z, x, y, land)
        if img[..., 3].any():
            size += write_png(Path(out) / name / str(z) / str(x) / f"{y}.png", img)
            files += 1
    return files, size


def render_release(run: Path, release: Path, land_path: Path | None, workers: int) -> dict:
    """Value and coverage layers for every target of the release, zoom 0 to 7 (they do not depend on the scenario)."""
    import shutil
    from concurrent.futures import ProcessPoolExecutor
    from discovery.discover import SCENARIO_TARGETS, load_cells
    from discovery.release import coverage_class
    targets = sorted({t for ts in SCENARIO_TARGETS.values() for t in ts})
    cols = ["cell", "windows", "masked_share", "cover_unknown", "confidence"]
    for t in targets:
        cols += [f"{t}:{k}" for k in ("windows", "valid", "screened_out", "median")]
    cells = load_cells(str(run / "cells.parquet"), cols)
    ids = np.asarray(cells["cell"]).astype(np.int64)
    order = np.argsort(ids)
    work = release / "layers" / "_work"
    work.mkdir(parents=True, exist_ok=True)
    np.save(work / "ids.npy", ids[order])
    land = np.load(land_path) if land_path else None
    if land is not None:
        np.save(work / "land.npy", np.sort(land.astype(np.int64)))
    names = []
    for t in targets:
        codes = cell_codes(coverage_class(cells, t)[order])
        for kind in ("typicality", "coverage"):
            key = f"{t}__{kind}"
            np.save(work / f"{key}.codes.npy", codes)
            if kind == "typicality":
                np.save(work / f"{key}.value.npy", np.asarray(cells[f"{t}:median"], float)[order].astype("float32"))
            names.append(f"{t}/{kind}")
    from discovery.geology import TARGET_GROUP
    from discovery.release import _geology
    geo = _geology(run, cells)                                    # T46: one geology layer per target when assessed
    for t in targets if geo else []:
        g = TARGET_GROUP.get(t)
        if g and f"geo:{g}:match" in geo:
            np.save(work / f"{t}__geology.codes.npy",
                    geology_class(geo[f"geo:{g}:match"], geo[f"geo:{g}:partial"], geo[f"geo:{g}:no_match"])[order])
            names.append(f"{t}/geology")
    del cells
    jobs = sorted({tile for zoom in range(MAX_ZOOM + 1) for tile in tiles_with_cells(land if land is not None else ids[order], zoom)})
    files = size = 0
    with ProcessPoolExecutor(max_workers=workers, initializer=_init, initargs=(str(work), names, land is not None)) as pool:
        for f, s in pool.map(_render_job, [(z, x, y, str(release / "layers")) for z, x, y in jobs], chunksize=16):
            files, size = files + f, size + s
    shutil.rmtree(work)
    summary = {"layers": names, "zoom": [0, MAX_ZOOM], "tiles": files, "bytes": size,
               "mb_per_layer": round(size / len(names) / 1e6, 1)}
    (release / "layers" / "layers.json").write_text(json.dumps(summary, indent=1) + "\n")
    return summary


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--run", type=Path, required=True)
    ap.add_argument("--release", type=Path, required=True)
    ap.add_argument("--land", type=Path, help="sorted HEALPix ids of land cells (.npy), from the 90 m cube")
    ap.add_argument("--workers", type=int, default=12)
    a = ap.parse_args(argv)
    print(json.dumps(render_release(a.run, a.release, a.land, a.workers)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
