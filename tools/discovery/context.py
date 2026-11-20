"""Earth context layers (T47, decision E18): frozen ground and aridity, per 5 km cell.

They are not similarities with the Moon: lunar temperatures and dryness have no Earth equivalent. They say what an
Earth place offers for a test (frozen ground for a drill, a dry climate), each labelled with its class and its limits.
Surface thermal cycling waits for MODIS (data improvement D1, Earthdata account).

    PYTHONPATH=tools python tools/discovery/context.py --run /data/run002 \
        --magt /data/permafrost/MAGTM.tif --magtsd /data/permafrost/MAGTSTD.tif --perprob /data/permafrost/PERPROB.tif \
        --aridity /data/aridity/ai_v31_yr.tif
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

LAYERS = {
    "frozen_ground": {
        "class": "model", "comparable_with_moon": False, "elevation_correction": False,
        "says": "modelled mean annual ground temperature at the top of the permafrost, 2000 to 2016, and permafrost probability",
        "not_meaning": "not lunar ice, not ice content, not a measurement at the site; Northern Hemisphere north of 25°N only",
        "threshold": "E4: frozen ground for drilling at -6 °C or colder; partial between -6 and 0 °C",
        "interannual_sigma": False, "sigma": "standard deviation of the model (MAGTSTD), not interannual",
        "source": "obu-permafrost-2018",
    },
    "aridity": {
        "class": "model", "comparable_with_moon": False, "elevation_correction": False,
        "says": "aridity index: mean annual precipitation over reference evapotranspiration, 1970 to 2000",
        "not_meaning": "not the water content of the ground; not lunar dryness (the Moon has no atmosphere)",
        "threshold": "UNEP classes: hyper-arid < 0.03, arid < 0.2, semi-arid < 0.5, dry sub-humid < 0.65, humid",
        "interannual_sigma": False, "sigma": "none: a 1970 to 2000 climatology",
        "no_data": "0 in the file (sea, or an index below 0.0001: not told apart) is treated as no data",
        "source": "global-aridity-index-v3",
    },
}
E4_FROZEN_C = -6.0
ARIDITY_CLASSES = ((0.03, "hyper-arid"), (0.2, "arid"), (0.5, "semi-arid"), (0.65, "dry sub-humid"))


def frozen_state(magt, covered) -> np.ndarray:
    """E4 state of each cell from its modelled mean annual ground temperature (°C)."""
    magt = np.asarray(magt, float)
    out = np.full(magt.shape, "not covered", dtype=object)
    ok = np.asarray(covered, bool) & np.isfinite(magt)
    out[ok & (magt <= E4_FROZEN_C)] = "met"
    out[ok & (magt > E4_FROZEN_C) & (magt <= 0)] = "partial"
    out[ok & (magt > 0)] = "failed"
    return out


def aridity_class(ai) -> np.ndarray:
    ai = np.asarray(ai, float)
    out = np.full(ai.shape, "humid", dtype=object)
    for limit, name in ARIDITY_CLASSES[::-1]:
        out[ai < limit] = name
    out[~np.isfinite(ai)] = "no data"
    return out


def aridity_from_raw(raw) -> np.ndarray:
    """Aridity index from the v3.1 integers (x 10,000). 0 is no data: the file writes 0 over the sea and states no
    nodata value, so 0 cannot be told from an index below 0.0001 (data improvement D11)."""
    raw = np.asarray(raw, float)
    return np.where(raw > 0, raw * 1e-4, np.nan)


def sample_stat(values: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Median of the valid samples of each cell (rows), and their count."""
    v = np.asarray(values, float)
    n = np.isfinite(v).sum(axis=1)
    med = np.full(v.shape[0], np.nan)
    ok = n > 0
    if ok.any():
        med[ok] = np.nanmedian(v[ok], axis=1)
    return med, n


def _sample_raster(path: Path, lat: np.ndarray, lon: np.ndarray, scale: float = 1.0) -> np.ndarray:
    """Values of a raster at points (lat, lon in degrees), NaN for nodata or outside; read once, indexed in numpy."""
    import rasterio
    from rasterio.warp import transform
    with rasterio.open(path) as src:
        flat_lat, flat_lon = lat.ravel(), lon.ravel()
        if src.crs and src.crs.to_epsg() != 4326:
            xs, ys = transform("EPSG:4326", src.crs, flat_lon.tolist(), flat_lat.tolist())
            xs, ys = np.asarray(xs), np.asarray(ys)
        else:
            xs, ys = flat_lon, flat_lat
        rows, cols = rasterio.transform.rowcol(src.transform, xs, ys)
        rows, cols = np.asarray(rows), np.asarray(cols)
        inside = (rows >= 0) & (rows < src.height) & (cols >= 0) & (cols < src.width)
        out = np.full(flat_lat.size, np.nan)
        order = np.argsort(rows[inside], kind="stable")
        idx = np.flatnonzero(inside)[order]
        r_sorted = rows[idx]
        # read in bands of rows, so a 40,000-column grid is never held whole
        band = 512
        for r0 in range(int(r_sorted.min()) if idx.size else 0, int(r_sorted.max()) + 1 if idx.size else 0, band):
            sel = idx[(r_sorted >= r0) & (r_sorted < r0 + band)]
            if sel.size == 0:
                continue
            win = rasterio.windows.Window(0, r0, src.width, min(band, src.height - r0))
            data = src.read(1, window=win).astype(float)
            vals = data[rows[sel] - r0, cols[sel]]
            if src.nodata is not None:
                vals[vals == src.nodata] = np.nan
            out[sel] = vals * scale
    return out.reshape(lat.shape)


def assess(run: Path, magt: Path, magtsd: Path, perprob: Path, aridity: Path) -> dict:
    import pyarrow as pa
    import pyarrow.parquet as pq
    from discovery.geology import sample_points
    t = pq.read_table(run / "cells.parquet", columns=["cell", "lat", "lon"])
    lat = t.column("lat").to_numpy(zero_copy_only=False).astype(float)
    lon = t.column("lon").to_numpy(zero_copy_only=False).astype(float)
    slat, slon = sample_points(lat, lon)
    m, n_m = sample_stat(_sample_raster(magt, slat, slon))
    sd, _ = sample_stat(_sample_raster(magtsd, slat, slon))
    pp, _ = sample_stat(_sample_raster(perprob, slat, slon))
    ai, n_ai = sample_stat(aridity_from_raw(_sample_raster(aridity, slat, slon)))
    covered = (lat >= 25) & (n_m > 0)
    cols = {"cell": t.column("cell"),
            "ctx:magt_c": pa.array(np.where(covered, m, np.nan).astype(np.float32)),
            "ctx:magt_sd_c": pa.array(np.where(covered, sd, np.nan).astype(np.float32)),
            "ctx:permafrost_prob": pa.array(np.where(covered, np.nan_to_num(pp, nan=0.0), np.nan).astype(np.float32)),
            "ctx:frozen_e4": pa.array(frozen_state(m, covered).tolist()),
            "ctx:aridity_index": pa.array(ai.astype(np.float32)),
            "ctx:aridity_class": pa.array(aridity_class(ai).tolist())}
    pq.write_table(pa.table(cols), run / "context.parquet", compression="zstd")
    fz = frozen_state(m, covered)
    ac = aridity_class(ai)
    summary = {"cells": int(lat.size), "layers": LAYERS,
               "frozen_e4": {s: round(float(np.mean(fz == s)), 4) for s in ("met", "partial", "failed", "not covered")},
               "aridity": {c: round(float(np.mean(ac == c)), 4) for c in ("hyper-arid", "arid", "semi-arid", "dry sub-humid", "humid", "no data")}}
    (run / "context.json").write_text(json.dumps(summary, indent=1) + "\n")
    return summary


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--run", type=Path, required=True)
    for k in ("magt", "magtsd", "perprob", "aridity"):
        ap.add_argument(f"--{k}", type=Path, required=True)
    a = ap.parse_args(argv)
    s = assess(a.run, a.magt, a.magtsd, a.perprob, a.aridity)
    print(json.dumps({k: v for k, v in s.items() if k != "layers"}, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
