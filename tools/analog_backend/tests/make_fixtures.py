"""Synthetic inputs in the REAL file formats/CRSs the pipeline reads (NetCDF, GeoTIFF in EPSG:3995/3031 and a lunar
polar-stereographic CRS with +R=1737400). They exercise the real code paths; the numbers themselves are fake."""
from __future__ import annotations
import json, os
import numpy as np, pandas as pd, rasterio, xarray as xr
from pyproj import Transformer
from rasterio.crs import CRS
from rasterio.transform import from_origin
from scipy.ndimage import gaussian_filter

MOON_CRS = CRS.from_proj4("+proj=stere +lat_0=-90 +lat_ts=-90 +lon_0=0 +k=1 +x_0=0 +y_0=0 +R=1737400 +units=m +no_defs")


def _write(path, arr, transform, crs, nodata=-9999.0):
    a = np.where(np.isfinite(arr), arr, nodata).astype("float32")
    with rasterio.open(path, "w", driver="GTiff", height=a.shape[0], width=a.shape[1], count=1, dtype="float32",
                       crs=crs, transform=transform, nodata=nodata) as dst:
        dst.write(a, 1)


def _field(shape, rng, sigma, amp):
    f = gaussian_filter(rng.normal(size=shape), sigma)
    return amp * (f - f.min()) / (np.ptp(f) + 1e-9)


def _geo_dem(path, bbox, rng, res=0.02, amp=2500):
    w, h = int(round((bbox[2] - bbox[0]) / res)), int(round((bbox[3] - bbox[1]) / res))
    z = _field((h, w), rng, 8, amp) + rng.normal(0, 8, (h, w))
    _write(path, z, from_origin(bbox[0], bbox[3], res, res), CRS.from_epsg(4326))


def _sar(path, bbox, epsg, rng, res_m=1000):
    tf = Transformer.from_crs(4326, epsg, always_xy=True)
    xs, ys = zip(*[tf.transform(lo, la) for lo in np.linspace(bbox[0], bbox[2], 12) for la in np.linspace(bbox[1], bbox[3], 12)])
    x0, x1, y0, y1 = min(xs), max(xs), min(ys), max(ys)
    w, h = int((x1 - x0) / res_m), int((y1 - y0) / res_m)
    sigma0 = np.exp(rng.normal(-3, 0.5, (h, w)) + 0.8 * _field((h, w), rng, 15, 1))   # linear backscatter
    _write(path, sigma0, from_origin(x0, y1, res_m, res_m), CRS.from_epsg(epsg))


def _nldas(d, bbox, rng, days=5, res=0.5):
    lat = np.arange(bbox[1] + res / 2, bbox[3], res); lon = np.arange(bbox[0] + res / 2, bbox[2], res)
    t = pd.date_range("2025-07-01", periods=days * 24, freq="h")
    LAT, LON = np.meshgrid(lat, lon, indexing="ij")
    elev = _field(LAT.shape, rng, 3, 3000)
    hr = t.hour.values[:, None, None]
    T = 303 - 0.5 * (LAT - 35) - 6.5 * elev / 1000 + (6 + 8 * elev / 3000) * np.sin(2 * np.pi * (hr - 9) / 24) + rng.normal(0, 1, (len(t),) + LAT.shape)
    T[:, 2:5, 8:14] = np.nan; T[30:70, 10:13, 15:25] = np.nan                       # voids
    sh = (len(t),) + LAT.shape
    mk = lambda a, u, ln="": (("time", "lat", "lon"), a.astype("float32"), {"units": u, "long_name": ln})
    noah = xr.Dataset({"AvgSurfT": mk(T, "K", "Average surface skin temperature"), "SoilM_0_10cm": mk(20 + 5 * rng.random(sh), "kg m-2"),
                       "SWnet": mk(300 * np.clip(np.sin(2 * np.pi * (hr - 6) / 24), 0, None) + 0 * T, "W m-2", "Net shortwave radiation flux"),
                       "LWnet": mk(-80 + 10 * rng.random(sh), "W m-2", "Net longwave radiation flux"), "Albedo": mk(np.full(sh, 18.0), "%")},
                      coords={"time": t, "lat": lat, "lon": lon})
    fora = xr.Dataset({"PSurf": mk(101325 * np.exp(-elev / 8400) + 0 * T, "Pa"), "Wind_E": mk(rng.normal(2, 1, sh), "m s-1"),
                       "Wind_N": mk(rng.normal(0, 1, sh), "m s-1"), "SWdown": mk(np.full(sh, 400.0), "W m-2")},
                      coords={"time": t, "lat": lat, "lon": lon})
    for name, ds in (("noah", noah), ("fora", fora)):
        for i, (_, g) in enumerate(ds.groupby("time.day")):
            g.to_netcdf(os.path.join(d, f"{name}_{i:02d}.nc"))


def _moon(d, rng, half_km=150, px=200, dpx=400):
    n = int(2 * half_km * 1000 / px)
    xs = (np.arange(n) + 0.5) * px - half_km * 1000
    X, Y = np.meshgrid(xs, -xs)
    z = rng.normal(0, 15, (n, n)) + 300 * gaussian_filter(rng.normal(size=(n, n)), 40) / 0.02 * 0.02
    for _ in range(12):
        cx, cy, r = rng.uniform(-90e3, 90e3, 2).tolist() + [rng.uniform(6e3, 18e3)]
        rr = np.hypot(X - cx, Y - cy)
        z += -2500 * np.exp(-(rr / r) ** 2) + 600 * np.exp(-((rr - r) / (0.25 * r)) ** 2)
    tf = from_origin(-half_km * 1000, half_km * 1000, px, px)
    _write(os.path.join(d, "LDEM_80S_synth.tif"), z, tf, MOON_CRS)
    m = int(2 * half_km * 1000 / dpx)                                                       # Diviner on a different grid
    zs = z[::dpx // px, ::dpx // px][:m, :m]
    tmin = 30 + 0.03 * (zs - zs.min()) + rng.normal(0, 1, zs.shape)
    tmax = tmin + 150 + _field(zs.shape, rng, 10, 100)
    dtf = from_origin(-half_km * 1000 + 100, half_km * 1000 - 100, dpx, dpx)
    _write(os.path.join(d, "diviner_tmin.tif"), tmin, dtf, MOON_CRS)
    _write(os.path.join(d, "diviner_tmax.tif"), tmax, dtf, MOON_CRS)


def make_fixtures(root: str) -> str:
    os.makedirs(root, exist_ok=True)
    rng = np.random.default_rng(7)
    doms = {"NLDAS": (-115, 35, -100, 45), "RCM_Arctic": (-100, 70, -80, 78), "RCM_Antarctic": (-70, -80, -50, -72)}
    cfg_dom = []
    for name, bb in doms.items():
        d = os.path.join(root, name); os.makedirs(d, exist_ok=True)
        st = pd.DataFrame({"lat": rng.uniform(bb[1], bb[3], 25), "lon": rng.uniform(bb[0], bb[2], 25)})
        st.to_csv(os.path.join(d, "stations.csv"), index=False)
        _geo_dem(os.path.join(d, "dem.tif"), bb, rng)
        spec = {"name": name, "bbox": list(bb), "stations_csv": os.path.join(d, "stations.csv"), "dem": os.path.join(d, "dem.tif")}
        if name == "NLDAS":
            _nldas(d, bb, rng)
            spec.update(grid_res_deg=0.5, noah=[os.path.join(d, "noah_*.nc")], fora=[os.path.join(d, "fora_*.nc")])
        else:
            _sar(os.path.join(d, "rcm_sigma0.tif"), bb, 3995 if "Arctic" in name else 3031, rng)
            spec.update(grid_res_deg=0.5, rcm=[os.path.join(d, "rcm_sigma0.tif")])
        cfg_dom.append(spec)
    ld = os.path.join(root, "lro"); os.makedirs(ld, exist_ok=True)
    _moon(ld, rng)
    cfg = {"geometry_baseline_m": 500.0, "robustness_runs": 3, "top_n": 120, "max_critical": 40,
           "hard_limits": {"slope_deg": [0, 60]}, "domains": cfg_dom,
           "lro": {"ldem": os.path.join(ld, "LDEM_80S_synth.tif"), "diviner_tmin": os.path.join(ld, "diviner_tmin.tif"),
                   "diviner_tmax": os.path.join(ld, "diviner_tmax.tif"), "aoi_radius_km": 100.0, "target_lat_max": -88.0}}
    p = os.path.join(root, "config.json")
    json.dump(cfg, open(p, "w"), indent=1)
    return p
