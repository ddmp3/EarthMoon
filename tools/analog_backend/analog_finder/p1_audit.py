"""Phase 1 - Rapid metadata audit. Reads only headers (lazy / OPeNDAP-friendly): no bulk download.

CLI:  python -m analog_finder.p1_audit file1.nc https://.../granule.nc4 --out audit.csv
"""
from __future__ import annotations
import argparse
import numpy as np
import pandas as pd
import xarray as xr
from .config import VARIABLE_ALIASES

LAT_NAMES = ("lat", "latitude", "y", "south_north")
LON_NAMES = ("lon", "longitude", "x", "west_east")


def _find_coord(ds: xr.Dataset, names) -> str | None:
    for n in list(ds.coords) + list(ds.dims):
        if n.lower() in names:
            return n
    return None


def _step(values: np.ndarray) -> float | None:
    if values.size < 2:
        return None
    d = np.abs(np.diff(values.astype("float64")))
    return float(np.median(d))


def match_alias(varname: str, attrs: dict) -> str | None:
    text = f"{varname} {attrs.get('long_name', '')} {attrs.get('standard_name', '')}".lower()
    for canon, keys in VARIABLE_ALIASES.items():
        if any(k in text for k in keys):
            return canon
    return None


def audit_dataset(path: str, sample_stride: int = 8) -> tuple[dict, pd.DataFrame]:
    """Return (summary_dict, variables_df). Opens lazily; the optional NaN probe reads a strided subsample only."""
    ds = xr.open_dataset(path, chunks={}, decode_times=True, mask_and_scale=True)
    lat_n, lon_n = _find_coord(ds, LAT_NAMES), _find_coord(ds, LON_NAMES)
    summ = {"source": path, "dims": dict(ds.sizes), "lat_name": lat_n, "lon_name": lon_n}
    if lat_n and lon_n:
        la, lo = ds[lat_n].values, ds[lon_n].values
        if la.ndim == 1 and lo.ndim == 1:
            summ.update(lat_res=_step(la), lon_res=_step(lo),
                        bbox=(float(lo.min()), float(la.min()), float(lo.max()), float(la.max())))
    if "time" in ds.coords and ds["time"].size > 0:
        t = ds["time"].values
        summ["n_time"] = int(t.size)
        summ["t_start"], summ["t_end"] = str(t.min()), str(t.max())
        if t.size > 1:
            summ["t_step"] = str(pd.Series(pd.to_datetime(t)).diff().median())
        else:
            summ["t_step"] = "single-step granule -> take temporal resolution from collection metadata"
    rows = []
    for name, da in ds.data_vars.items():
        a = da.attrs
        canon = match_alias(name, a)
        nan_frac = np.nan
        try:  # cheap probe on a strided subsample
            sub = da.isel({d: slice(None, None, sample_stride) for d in da.dims if d not in ("time",)})
            if "time" in sub.dims:
                sub = sub.isel(time=slice(0, 1))
            nan_frac = float(sub.isnull().mean().compute())
        except Exception:
            pass
        rows.append(dict(var=name, canonical=canon, units=a.get("units"), long_name=a.get("long_name"),
                         dims=",".join(da.dims), shape=tuple(da.shape), dtype=str(da.dtype),
                         nan_frac_probe=nan_frac))
    df = pd.DataFrame(rows)
    ds.close()
    return summ, df


def audit_raster(path: str) -> dict:
    """Header-only audit of a GeoTIFF (LOLA / Diviner / RCM): CRS, pixel size, bounds, dtype, nodata, scale/offset."""
    import rasterio
    with rasterio.open(path) as r:
        return {"source": path, "driver": r.driver, "crs": r.crs.to_string() if r.crs else None, "shape": (r.height, r.width),
                "bands": r.count, "pixel_size": (abs(r.transform.a), abs(r.transform.e)), "bounds": tuple(r.bounds),
                "dtype": r.dtypes[0], "nodata": r.nodata, "scale": r.scales[0], "offset": r.offsets[0],
                "units": r.units[0], "tags": {k: v for k, v in list(r.tags().items())[:8]}}


def value_score(summ: dict, df: pd.DataFrame, need=("skin_temp", "sw_net", "lw_net", "soil_moist"),
                nice=("wind_u", "pressure", "albedo", "snow_depth")) -> dict:
    """Crude 0-100 'is it worth downloading?' score + reasons."""
    have = set(df["canonical"].dropna())
    s_need = len(have & set(need)) / len(need)
    s_nice = len(have & set(nice)) / len(nice) if nice else 0.0
    res_ok = 1.0 if (summ.get("lat_res") or 9) <= 0.25 else 0.4
    nan_pen = 1 - float(np.nan_to_num(df["nan_frac_probe"].mean(), nan=0.0))
    score = 100 * (0.55 * s_need + 0.15 * s_nice + 0.15 * res_ok + 0.15 * nan_pen)
    return dict(score=round(score, 1), has=sorted(have), missing_needed=sorted(set(need) - have))


def search_granules(short_name: str, bbox, start: str, end: str, version: str | None = None, count: int = 5):
    """Optional: list granule metadata on NASA CMR WITHOUT downloading (needs `pip install earthaccess`).
    NLDAS Noah hourly: short_name='NLDAS_NOAH0125_H', version='2.0'; forcing: 'NLDAS_FORA0125_H'."""
    import earthaccess
    earthaccess.login()  # reads ~/.netrc or env EARTHDATA_USERNAME/PASSWORD
    kw = dict(short_name=short_name, bounding_box=bbox, temporal=(start, end), count=count)
    if version:
        kw["version"] = version
    res = earthaccess.search_data(**kw)
    return res  # then: earthaccess.open(res[:1]) streams a granule lazily -> pass file object to audit_dataset


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("paths", nargs="+")
    ap.add_argument("--out", default="audit.csv")
    a = ap.parse_args()
    frames = []
    for p in a.paths:
        s, d = audit_dataset(p)
        v = value_score(s, d)
        print(f"\n== {p}\n{s}\nvalue={v}")
        d.insert(0, "source", p)
        frames.append(d)
    pd.concat(frames).to_csv(a.out, index=False)
    print(f"\nsaved {a.out}")
