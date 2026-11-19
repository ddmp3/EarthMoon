"""Bias checks of validation protocol section 4 on the top zones of a run (T43).

- Single source: every terrain value comes from Copernicus. The top 100 zones of each scenario are recomputed from
  NASADEM (60°N to 56°S, Microsoft Planetary Computer, no account) at the target's pixel scale.
- Resolution: the same zones are recomputed from Copernicus GLO-30 at 30 m (its native spacing), against the
  planetary pixel of the run.
For a fair comparison, the zone median is recomputed the same way for every source: the median over its cells of
the cell median typicality of all their windows (masks are not recomputed for the alternative sources).

    PYTHONPATH=tools python tools/discovery/checks.py --run /data/run001 --cache /glo30
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

TOP = 100


def compare_rankings(nominal: np.ndarray, other: np.ndarray, top: int = 20) -> dict:
    """Spearman correlation of zone values and the share of the nominal top `top` kept in the other top `top`."""
    ok = np.isfinite(nominal) & np.isfinite(other)
    x, y = np.asarray(nominal)[ok], np.asarray(other)[ok]
    rx, ry = np.argsort(np.argsort(-x)), np.argsort(np.argsort(-y))
    k = min(top, x.size)
    keep = len(set(np.flatnonzero(rx < k)) & set(np.flatnonzero(ry < k))) / k if k else float("nan")
    return {"zones": int(x.size), "spearman": float(np.corrcoef(rx, ry)[0, 1]) if x.size > 2 else float("nan"),
            "top": k, "top_overlap": float(keep)}


def _nasadem(grid, la: int, lo: int) -> np.ndarray:
    import planetary_computer
    import pystac_client
    import rasterio
    from rasterio.warp import Resampling, reproject
    cat = pystac_client.Client.open("https://planetarycomputer.microsoft.com/api/stac/v1",
                                    modifier=planetary_computer.sign_inplace)
    z = np.full(grid.shape, np.nan, "float32")
    items = cat.search(collections=["nasadem"], bbox=[lo - 1, la - 1, lo + 2, la + 2]).items()
    for it in items:
        with rasterio.open(it.assets["elevation"].href) as src:
            part = np.full(grid.shape, np.nan, "float32")
            reproject(rasterio.band(src, 1), part, src_nodata=src.nodata, dst_transform=grid.transform,
                      dst_crs=grid.crs, dst_nodata=np.nan, resampling=Resampling.bilinear)
        z = np.where(np.isfinite(part), part, z)
    return z


def zone_values(zone: dict, target: str, ref: np.ndarray, source: str, pixel: float, have: set, cache: Path) -> float:
    from discovery.compare import cell_medians, percentile_typicality
    from discovery.copernicus import tile_name
    from discovery.cube import compute_tile, read_dem
    from discovery.grid import tile_grid
    cells = set(zone["cell_ids"])
    meds = []
    for key in zone["tiles"]:
        la, lo = (int(v) for v in key.split(","))
        g = tile_grid(la, lo, pixel, 1000.0)
        z = _nasadem(g, la, lo) if source == "nasadem" else read_dem(g, "glo30", have, cache)[0]
        w, _ = compute_tile(z, g)
        name = tile_name(la, lo, "glo30")
        cid = np.array([f"{name}:{i}:{j}" for i, j in zip(w["i"], w["j"])])
        keep = np.isin(cid, list(cells))
        if keep.any():
            _, m = cell_medians(percentile_typicality(np.asarray(w["slope_mean"])[keep], ref), cid[keep])
            meds.extend(m[np.isfinite(m)].tolist())
    return float(np.median(meds)) if meds else float("nan")


def main(argv=None) -> int:
    from discovery.cube import GDAL_ENV
    from discovery.discover import SCALES, TARGET_SCALE, dossier_zones
    os.environ.update(GDAL_ENV)
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--run", type=Path, required=True)
    ap.add_argument("--cache", type=Path, required=True)
    ap.add_argument("--cube", type=Path, default=Path("/data/cube"))
    a = ap.parse_args(argv)
    refs = dict(np.load(a.run / "refs.npz"))
    have = {tuple(map(int, k.split(","))) for k in json.loads((a.cube / "glo30-40m" / "listing.json").read_text())}
    summary = json.loads((a.run / "zones.json").read_text())
    out = {}
    for sc, v in summary["scenarios"].items():
        allz = [z for t in v["targets"] for z in json.loads((a.run / f"zones-{sc}-{t}.json").read_text())]
        top = dossier_zones([{**z, "cell_ids": z["cell_ids"]} for z in allz], top=TOP)
        res = {"nominal": [], "nasadem": [], "glo30_30m": []}
        for z in top:
            t, px = z["target"], SCALES[TARGET_SCALE[z["target"]]]
            res["nominal"].append(zone_values(z, t, refs[t], "glo30", px, have, a.cache))
            inside = -56 <= z["lat"] <= 60
            res["nasadem"].append(zone_values(z, t, refs[t], "nasadem", px, have, a.cache) if inside else float("nan"))
            res["glo30_30m"].append(zone_values(z, t, refs[t], "glo30", 30.0, have, a.cache))
            print(sc, t, round(res["nominal"][-1], 3), round(res["nasadem"][-1], 3), round(res["glo30_30m"][-1], 3), flush=True)
        nom = np.array(res["nominal"])
        out[sc] = {"zones": len(top),
                   "nasadem": compare_rankings(nom, np.array(res["nasadem"])),
                   "resolution_30m": compare_rankings(nom, np.array(res["glo30_30m"])),
                   "values": [{"lat": z["lat"], "lon": z["lon"], "target": z["target"], "nominal": n, "nasadem": s, "glo30_30m": r}
                              for z, n, s, r in zip(top, res["nominal"], res["nasadem"], res["glo30_30m"])]}
    (a.run / "checks.json").write_text(json.dumps(out, indent=1) + "\n")
    print(json.dumps({sc: {k: v[k] for k in ("zones", "nasadem", "resolution_30m")} for sc, v in out.items()}, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
