"""Planetary environment profiles (T41, ADR-001 stage `profiles`).

A profile is the distribution of each terrain metric over the windows of one environment, selected by the rule of
its spec (`data/profiles/spec/<id>.yaml`). The window metrics are the Earth ones (`windows.window_metrics_grid`),
so a lunar window and an Earth window are measured by the same code.

    python tools/discovery/profiles.py south-polar-cap --ldem /data/lola/ldem_85s_40m.img --out data/profiles/moon
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "precompute"))
from discovery.windows import ALL_METRICS, window_metrics_grid  # noqa: E402

PERCENTILES = (5, 10, 25, 50, 75, 90, 95)
PROFILE_FILES = ("discovery/profiles.py", "discovery/windows.py", "precompute/terrain_metrics.py",
                 "precompute/lunar_reference.py")
LDEM_85S = {"size": 7584, "pixel_m": 40.0, "window_px": 25}


# --- pure part (tested) ------------------------------------------------------------------------------------

def select_windows(mask: np.ndarray, window_px: int, margin: int = 0) -> np.ndarray:
    """(rows, cols) grid of non-overlapping windows: True when every pixel of the window is inside `mask`."""
    core = mask[margin:mask.shape[0] - margin, margin:mask.shape[1] - margin]
    h, w = (core.shape[0] // window_px) * window_px, (core.shape[1] // window_px) * window_px
    return core[:h, :w].reshape(h // window_px, window_px, w // window_px, window_px).all(axis=(1, 3))


def summarise(values: dict[str, np.ndarray], selected: np.ndarray, metrics: tuple[str, ...]) -> dict:
    """Counts and percentiles of each metric over the selected windows. NaN windows (below 90% valid pixels)
    count as selected but not valid; they never enter a percentile."""
    sel = selected.ravel()
    first = np.asarray(values[metrics[0]]).ravel()[sel]
    out = {"windows": {"selected": int(sel.sum()), "valid": int(np.isfinite(first).sum())}, "metrics": {}}
    for k in metrics:
        v = np.asarray(values[k], dtype="float64").ravel()[sel]
        v = v[np.isfinite(v)]
        row = {"n": int(v.size)}
        for p in PERCENTILES:
            row[f"p{p}"] = round(float(np.percentile(v, p)), 3) if v.size else None
        out["metrics"][k] = row
    return out


def window_fraction(pixels: np.ndarray, window_px: int, margin: int = 0) -> np.ndarray:
    """Mean of a 0..1 pixel layer per window, over known pixels; NaN when the window has none."""
    core = pixels[margin:pixels.shape[0] - margin, margin:pixels.shape[1] - margin].astype("float64")
    h, w = (core.shape[0] // window_px) * window_px, (core.shape[1] // window_px) * window_px
    b = core[:h, :w].reshape(h // window_px, window_px, w // window_px, window_px)
    with np.errstate(invalid="ignore"):
        n = np.isfinite(b).sum(axis=(1, 3))
        s = np.nansum(b, axis=(1, 3))
    return np.where(n > 0, s / np.maximum(n, 1), np.nan)


def threshold(frac: np.ndarray, at_most: float | None = None, at_least: float | None = None) -> np.ndarray:
    """Windows whose fraction is <= at_most or >= at_least. Unknown (NaN) is never selected."""
    ok = np.isfinite(frac)
    f = np.where(ok, frac, 0.0)
    if at_most is not None:
        return ok & (f <= at_most)
    return ok & (f >= at_least)


def lit_areas(illumination: np.ndarray, q: float, min_pixels: int) -> np.ndarray:
    """Pixels of connected areas (8-connected) with average illumination >= q and at least min_pixels pixels."""
    from rasterio.features import sieve
    above = np.isfinite(illumination) & (np.nan_to_num(illumination) >= q)
    kept = sieve(above.astype("uint8"), size=min_pixels, connectivity=8).astype(bool)
    return kept & above              # sieving never adds a pixel below q


def code_version(root: Path = Path(__file__).resolve().parents[1]) -> str:
    """sha256 of the profile sources, line endings normalised (as the Earth cube, ADR-009)."""
    h = hashlib.sha256()
    for name in PROFILE_FILES:
        h.update(name.encode() + b"\0" + (root / name).read_bytes().replace(b"\r\n", b"\n") + b"\0")
    return h.hexdigest()


def file_input(path: Path) -> dict:
    return {"file": path.name, "size": path.stat().st_size, "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}


# --- environments ------------------------------------------------------------------------------------------

def south_polar_cap(ldem: Path, max_lat: float = -85.0) -> dict:
    """moon-south-polar-cap-v2: every 1 km window of LDEM_85S_40M entirely south of max_lat (v2 anchor)."""
    from lunar_reference import latitude_grid, read_ldem
    g = LDEM_85S
    z = read_ldem(str(ldem), g["size"])
    lat = latitude_grid(g["size"], g["pixel_m"])
    w = window_metrics_grid(z, g["pixel_m"], g["window_px"], margin=0, metrics=ALL_METRICS)
    sel = select_windows(lat <= max_lat, g["window_px"])
    return summarise(w, sel, ALL_METRICS)


def read_polar(path: Path, size: int, pixel_m: float, psr: bool = False) -> np.ndarray:
    """A PGDA polar stereographic product (int16 with scale and offset) on the LDEM grid, nearest neighbour.
    Nodata and, for the PSR map, any value other than 0 or 1 are unknown (NaN)."""
    import rasterio
    from rasterio.transform import from_origin
    from rasterio.warp import Resampling, reproject
    half = size * pixel_m / 2
    out = np.full((size, size), np.nan, "float32")
    with rasterio.open(path) as src:
        a = src.read(1).astype("float64")
        a = np.where(a == src.nodata, np.nan, a * src.scales[0] + src.offsets[0]) if src.nodata is not None \
            else a * src.scales[0] + src.offsets[0]
        if psr:
            a = np.where(np.isin(a, (0.0, 1.0)), a, np.nan)
        reproject(a.astype("float32"), out, src_transform=src.transform, src_crs=src.crs, src_nodata=np.nan,
                  dst_transform=from_origin(-half, half, pixel_m, pixel_m), dst_crs=src.crs, dst_nodata=np.nan,
                  resampling=Resampling.nearest)
    return out


def polar_windows(ldem: Path, psr_path: Path, ill_path: Path, window_px: int = 25, max_lat: float = -85.0):
    """Metrics, permanent-shadow fraction and mean illumination of every window of LDEM_85S_40M south of max_lat."""
    from lunar_reference import latitude_grid, read_ldem
    g = LDEM_85S
    z = read_ldem(str(ldem), g["size"])
    lat = latitude_grid(g["size"], g["pixel_m"])
    w = window_metrics_grid(z, g["pixel_m"], window_px, margin=0, metrics=ALL_METRICS)
    w["psr_fraction"] = window_fraction(read_polar(psr_path, g["size"], g["pixel_m"], psr=True), window_px)
    w["mean_illumination"] = window_fraction(read_polar(ill_path, g["size"], g["pixel_m"]), window_px)
    return w, select_windows(lat <= max_lat, window_px)


def record(spec_id: str, summary: dict, inputs: dict, params: dict) -> dict:
    return {"id": spec_id, "body": "moon", "spec": f"data/profiles/spec/{spec_id}.yaml", "inputs": inputs,
            "code": code_version(), "commit": os.environ.get("EARTHMOON_COMMIT", "unknown"), "params": params,
            "percentiles": list(PERCENTILES), **summary}


def write_windows(path: Path, w: dict, sel: np.ndarray, cols: tuple[str, ...], pixel_m: float, window_px: int,
                  size: int) -> str:
    """Parquet of the selected windows (row, col, polar stereographic centre x and y, metrics); returns sha256."""
    import pyarrow as pa
    import pyarrow.parquet as pq
    r, c = np.nonzero(sel)
    half = size * pixel_m / 2
    t = {"row": r.astype("int32"), "col": c.astype("int32"),
         "x_m": (-half + (c + 0.5) * window_px * pixel_m).astype("float64"),
         "y_m": (half - (r + 0.5) * window_px * pixel_m).astype("float64")}
    for k in cols:
        t[k] = np.asarray(w[k])[sel].astype("float32")
    path.parent.mkdir(parents=True, exist_ok=True)
    pq.write_table(pa.table(t), path, compression="zstd")
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write(path: Path, rec: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(rec, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("what", choices=["south-polar-cap", "polar"])
    ap.add_argument("--psr", type=Path)
    ap.add_argument("--illumination", type=Path)
    ap.add_argument("--windows-out", type=Path, default=Path("/data/profiles/moon"))
    ap.add_argument("--ldem", type=Path)
    ap.add_argument("--out", type=Path, default=Path("data/profiles/moon"))
    a = ap.parse_args(argv)
    if a.what == "south-polar-cap":
        s = south_polar_cap(a.ldem)
        rec = record("moon-south-polar-cap-v2", s, {"lro-lola-ldem-85s-40m": file_input(a.ldem)},
                     {"max_lat": -85.0, "pixel_m": 40.0, "window_px": 25, "margin_px": 0, "min_valid": 0.9})
        write(a.out / "moon-south-polar-cap-v2.json", rec)
        print(json.dumps(rec["windows"]), json.dumps(rec["metrics"]["slope_mean"]))
    elif a.what == "polar":
        polar(a)
    return 0


POLAR_METRICS = ALL_METRICS + ("mean_illumination",)


def polar(a) -> None:
    """moon-polar-lit-highlands and moon-psr. Nominal thresholds are the middle of the spec sensitivity lists
    (expert choice, T41); every listed value is computed and reported."""
    inputs = {"lro-lola-ldem-85s-40m": file_input(a.ldem), "lola-polar-illumination/psr": file_input(a.psr),
              "lola-polar-illumination/average": file_input(a.illumination)}
    g = LDEM_85S
    runs = {}
    for px in (25, 12, 5):
        runs[px] = polar_windows(a.ldem, a.psr, a.illumination, window_px=px)
    w, base = runs[25]
    specs = {"moon-polar-lit-highlands": ("f_lit", "at_most", 0.05, (0.0, 0.05, 0.10), (25,)),
             "moon-psr": ("f_psr", "at_least", 0.75, (0.5, 0.75, 0.9), (25, 12, 5))}
    for sid, (name, side, nominal, values, sizes) in specs.items():
        sens = []
        for px in sizes:
            wp, bp = runs[px]
            for v in values:
                sel = bp & threshold(wp["psr_fraction"], **{side: v})
                s = summarise(wp, sel, ("slope_mean",))
                sens.append({name: v, "window_m": px * g["pixel_m"], **s["windows"], "slope_mean": s["metrics"]["slope_mean"]})
        sel = base & threshold(w["psr_fraction"], **{side: nominal})
        rec = record(sid, summarise(w, sel, POLAR_METRICS), inputs,
                     {name: nominal, "nominal_rule": "middle of the spec sensitivity list (expert choice, T41)",
                      "max_lat": -85.0, "pixel_m": g["pixel_m"], "window_px": 25, "window_m": 1000.0, "min_valid": 0.9})
        rec["sensitivity"] = sens
        rec["outputs"] = {"windows_parquet": write_windows(a.windows_out / f"{sid}.windows.parquet", w, sel,
                                                           POLAR_METRICS + ("psr_fraction",), g["pixel_m"], 25, g["size"])}
        rec["not_computed"] = {"reason": "thermal, volatile and radar layers (Diviner, LAMP, Mini-RF) belong to T47"}
        write(a.out / f"{sid}.json", rec)
        print(sid, json.dumps(rec["windows"]), json.dumps(rec["metrics"]["slope_mean"]))


if __name__ == "__main__":
    sys.exit(main())
