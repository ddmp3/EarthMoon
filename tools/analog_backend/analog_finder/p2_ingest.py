"""Phase 2 - Ingestion, alignment, resampling, feature engineering.

Terrain geometry (slope, roughness, shadow) is ALWAYS computed from a raster resampled to one common baseline
(`baseline_m`, metres/pixel) and the same sun elevation, for Earth and Moon alike, and only then aggregated to the
model grid. That keeps geometry comparable in absolute units across planets.
"""
from __future__ import annotations
import logging
import numpy as np
import xarray as xr
from scipy import ndimage as ndi
from .p1_audit import match_alias, LAT_NAMES, LON_NAMES

log = logging.getLogger(__name__)
R_EARTH = 6_371_000.0
R_MOON = 1_737_400.0
TFREEZE = 273.15


# =============================== NetCDF ===============================
def standardize(ds: xr.Dataset, bbox=None) -> xr.Dataset:
    """Rename coords to lat/lon, sort ascending, crop to bbox=(lon0, lat0, lon1, lat1)."""
    ren = {}
    for n in list(ds.coords) + list(ds.dims):
        if n.lower() in LAT_NAMES[:2] and n != "lat": ren[n] = "lat"
        if n.lower() in LON_NAMES[:2] and n != "lon": ren[n] = "lon"
    ds = ds.rename(ren).sortby("lat").sortby("lon")
    if bbox:
        ds = ds.sel(lon=slice(bbox[0], bbox[2]), lat=slice(bbox[1], bbox[3]))
    return ds


def open_stack(paths: list[str], bbox=None, wanted=("skin_temp", "soil_moist", "sw_net", "lw_net", "albedo",
                                                    "wind_u", "wind_v", "pressure")) -> xr.Dataset:
    """Open many granules lazily; keep ONE variable per canonical name (first match wins)."""
    ds = standardize(xr.open_mfdataset(paths, combine="by_coords", chunks={"time": 24}, parallel=False), bbox)
    keep = {}
    for v in ds.data_vars:
        c = match_alias(v, ds[v].attrs)
        if c in wanted and c not in keep:
            keep[c] = ds[v]
    out = xr.Dataset(keep)
    if "wind_u" in out and "wind_v" in out:
        out["wind"] = np.hypot(out["wind_u"], out["wind_v"])
    return out


def open_nldas(noah_paths: list[str], fora_paths: list[str] | None = None, bbox=None) -> xr.Dataset:
    """NLDAS-2 CONUS: surface/soil/radiation from Noah L4 (NLDAS_NOAH0125_H) + wind/pressure from FORCING (NLDAS_FORA0125_H).
    The variable whitelist per product avoids FORA's SWdown/LWdown shadowing Noah's SWnet/LWnet."""
    parts = [open_stack(noah_paths, bbox, wanted=("skin_temp", "soil_moist", "sw_net", "lw_net", "albedo"))]
    if fora_paths:
        parts.append(open_stack(fora_paths, bbox, wanted=("wind_u", "wind_v", "pressure")))
    return xr.merge(parts, join="inner", compat="override")


def resample_time(ds: xr.Dataset, freq="1D", how="mean") -> xr.Dataset:
    return getattr(ds.resample(time=freq), how)()


def regrid(ds, template: xr.DataArray, method="linear"):
    return ds.interp(lat=template["lat"], lon=template["lon"], method=method)


def make_template(bbox, res_deg: float) -> xr.DataArray:
    """Empty lat/lon grid (cell centres) for domains without a gridded NetCDF (e.g. SAR-only RCM)."""
    lon = np.arange(bbox[0] + res_deg / 2, bbox[2], res_deg)
    lat = np.arange(bbox[1] + res_deg / 2, bbox[3], res_deg)
    return xr.DataArray(np.zeros((lat.size, lon.size), "float32"), coords={"lat": lat, "lon": lon}, dims=("lat", "lon"))


# =============================== Raster plumbing ===============================
def pixel_size_m(transform, crs, mid_lat: float = 0.0, radius_m: float = R_EARTH) -> tuple[float, float]:
    """(dx, dy) in metres. Geographic CRS -> degrees converted with the body's radius."""
    if crs is not None and crs.is_geographic:
        dy = np.deg2rad(abs(transform.e)) * radius_m
        dx = np.deg2rad(abs(transform.a)) * radius_m * max(np.cos(np.deg2rad(mid_lat)), 0.05)
        return float(dx), float(dy)
    return float(abs(transform.a)), float(abs(transform.e))


def read_at_baseline(path: str, baseline_m: float, window_bounds=None, band: int = 1, radius_m: float = R_EARTH,
                     resampling: str = "average"):
    """Read a raster (optionally a window given in the raster's CRS units) resampled to ~baseline_m per pixel.
    Never up-samples. Applies GDAL scale/offset. Returns (array float32 with NaN, transform, crs, (dx_m, dy_m))."""
    import rasterio
    from affine import Affine
    from rasterio.enums import Resampling
    from rasterio.windows import Window, from_bounds, intersection
    with rasterio.open(path) as src:
        full = Window(0, 0, src.width, src.height)
        if window_bounds is not None:
            w = from_bounds(*window_bounds, transform=src.transform)
            w = Window(int(np.floor(w.col_off)), int(np.floor(w.row_off)), int(np.ceil(w.width)), int(np.ceil(w.height)))
            win = intersection(w, full)
        else:
            win = full
        mid_lat = 0.0
        if src.crs is not None and src.crs.is_geographic:
            mid_lat = src.xy(win.row_off + win.height // 2, win.col_off + win.width // 2)[1]
        px, py = pixel_size_m(src.transform, src.crs, mid_lat, radius_m)
        if min(px, py) > 1.5 * baseline_m:
            log.warning("%s: native pixel %.0f m is coarser than baseline %.0f m (geometry baselines will differ)", path, px, baseline_m)
        fx, fy = max(baseline_m / px, 1.0), max(baseline_m / py, 1.0)
        out_h, out_w = max(int(win.height / fy), 1), max(int(win.width / fx), 1)
        arr = src.read(band, window=win, out_shape=(out_h, out_w), masked=True,
                       resampling=getattr(Resampling, resampling)).astype("float64")
        sc = src.scales[band - 1] if src.scales else 1.0
        of = src.offsets[band - 1] if src.offsets else 0.0
        arr = (arr * sc + of).astype("float32").filled(np.nan)
        tr = src.window_transform(win) * Affine.scale(win.width / out_w, win.height / out_h)
        crs = src.crs
    dx, dy = pixel_size_m(tr, crs, mid_lat, radius_m)
    return arr, tr, crs, (dx, dy)


def warp_array(arr, src_tr, src_crs, dst_shape, dst_tr, dst_crs, resampling="average") -> np.ndarray:
    from rasterio.warp import reproject, Resampling
    dst = np.full(dst_shape, np.nan, "float32")
    reproject(source=np.ascontiguousarray(arr, dtype="float32"), destination=dst, src_transform=src_tr, src_crs=src_crs,
              src_nodata=np.nan, dst_transform=dst_tr, dst_crs=dst_crs, dst_nodata=np.nan,
              resampling=getattr(Resampling, resampling))
    return dst


def warp_file(path, dst_shape, dst_tr, dst_crs, band=1, resampling="average") -> np.ndarray:
    import rasterio
    from rasterio.warp import reproject, Resampling
    dst = np.full(dst_shape, np.nan, "float32")
    with rasterio.open(path) as src:
        reproject(source=rasterio.band(src, band), destination=dst, src_transform=src.transform, src_crs=src.crs,
                  src_nodata=src.nodata, dst_transform=dst_tr, dst_crs=dst_crs, dst_nodata=np.nan,
                  resampling=getattr(Resampling, resampling))
        sc = src.scales[band - 1] if src.scales else 1.0
        of = src.offsets[band - 1] if src.offsets else 0.0
    return dst * sc + of if (sc != 1.0 or of != 0.0) else dst


def _template_grid(template: xr.DataArray):
    from rasterio.transform import from_origin
    lat, lon = template["lat"].values, template["lon"].values
    dy, dx = abs(np.median(np.diff(lat))), abs(np.median(np.diff(lon)))
    return (lat.size, lon.size), from_origin(lon.min() - dx / 2, lat.max() + dy / 2, dx, dy)


def _to_da(arr_north_up: np.ndarray, template: xr.DataArray) -> xr.DataArray:
    return xr.DataArray(arr_north_up[::-1], coords={"lat": template["lat"], "lon": template["lon"]}, dims=("lat", "lon"))


def reproject_raster(path: str, template: xr.DataArray, band=1, resampling="average") -> xr.DataArray:
    shape, tr = _template_grid(template)
    return _to_da(warp_file(path, shape, tr, "EPSG:4326", band, resampling), template)


# =============================== Terrain (array level, planet-agnostic) ===============================
def slope_roughness_arrays(z: np.ndarray, dx, dy, win: int = 3):
    """Slope (deg) and roughness (RMS height deviation in a win x win window, m)."""
    ok = np.isfinite(z)
    zf = np.where(ok, z, np.nanmedian(z)).astype("float64")
    zf -= zf.mean()
    gy = np.gradient(zf, dy, axis=0)
    gx = np.gradient(zf, axis=1) / dx
    slope = np.degrees(np.arctan(np.hypot(gx, gy)))
    mu = ndi.uniform_filter(zf, win)
    rms = np.sqrt(np.clip(ndi.uniform_filter(zf**2, win) - mu**2, 0, None))
    slope[~ok] = np.nan; rms[~ok] = np.nan
    return slope.astype("float32"), rms.astype("float32")


def shadow_fraction_array(z: np.ndarray, dx, dy, sun_elev_deg: float = 1.5, n_az: int = 8, max_steps: int = 40):
    """Fraction of azimuths in which a cell is horizon-shadowed for a sun at `sun_elev_deg` (horizon-angle ray marching).
    Horizon reach = max_steps * baseline. If you have a LOLA-derived illumination map, prefer it (see lro.py)."""
    ok = np.isfinite(z)
    zf = np.where(ok, z, np.nanmedian(z)).astype("float64")
    H, W = zf.shape
    dxm = float(np.mean(dx))
    zp = np.pad(zf, max_steps, mode="edge")
    shadow = np.zeros_like(zf)
    for az in np.linspace(0, 2 * np.pi, n_az, endpoint=False):
        horizon = np.full_like(zf, -90.0)
        for k in range(1, max_steps + 1):
            sx, sy = int(round(k * np.sin(az))), int(round(k * np.cos(az)))
            if sx == 0 and sy == 0:
                continue
            zz = zp[max_steps + sy:max_steps + sy + H, max_steps + sx:max_steps + sx + W]
            horizon = np.maximum(horizon, np.degrees(np.arctan((zz - zf) / np.hypot(sx * dxm, sy * dy))))
        shadow += horizon > sun_elev_deg
    out = (shadow / n_az).astype("float32")
    out[~ok] = np.nan
    return out


def local_std(a: np.ndarray, win: int = 5) -> np.ndarray:
    ok = np.isfinite(a)
    m = np.where(ok, a, np.nanmean(a)).astype("float64")
    var = ndi.uniform_filter(m**2, win) - ndi.uniform_filter(m, win) ** 2
    out = np.sqrt(np.clip(var, 0, None)).astype("float32")
    out[~ok] = np.nan
    return out


# =============================== Terrain -> model grid ===============================
def geometry_layers_on_grid(dem_path: str, template: xr.DataArray, baseline_m: float = 120.0, radius_m: float = R_EARTH,
                            sun_elev_deg: float = 1.5, n_az: int = 8, max_steps: int = 40) -> xr.Dataset:
    """DEM (any CRS) -> elev_m, slope_deg, roughness_m, shadow_frac on the lat/lon template (block-averaged AFTER derivation)."""
    z, tr, crs, (dx, dy) = read_at_baseline(dem_path, baseline_m, radius_m=radius_m)
    slope, rough = slope_roughness_arrays(z, dx, dy)
    shade = shadow_fraction_array(z, dx, dy, sun_elev_deg, n_az, max_steps)
    shape, dst_tr = _template_grid(template)
    layers = {"elev_m": z, "slope_deg": slope, "roughness_m": rough, "shadow_frac": shade}
    return xr.Dataset({k: _to_da(warp_array(v, tr, crs, shape, dst_tr, "EPSG:4326"), template) for k, v in layers.items()})


def sar_texture_on_grid(path: str, template: xr.DataArray, baseline_m: float = 100.0, win: int = 5,
                        is_db: bool = False, radius_m: float = R_EARTH) -> xr.DataArray:
    """RCM/SAR sigma0 (CALIBRATED, linear unless is_db) -> local std of backscatter in dB, averaged onto the grid.
    Unit is dB, NOT metres: it is a texture covariate for clustering/novelty, not used in the absolute geometry match."""
    arr, tr, crs, _ = read_at_baseline(path, baseline_m, radius_m=radius_m)
    db = arr if is_db else 10 * np.log10(np.where(arr > 0, arr, np.nan))
    shape, dst_tr = _template_grid(template)
    return _to_da(warp_array(local_std(db, win), tr, crs, shape, dst_tr, "EPSG:4326"), template)


# =============================== Feature table ===============================
def build_features(ds: xr.Dataset | None, geometry: xr.Dataset | None = None, sar_texture: xr.DataArray | None = None) -> xr.Dataset:
    """Hourly stack (+ precomputed geometry / SAR texture) -> per-cell feature Dataset. `ds` may be None (SAR/DEM-only domain)."""
    f = xr.Dataset()
    if ds is not None:
        T = ds["skin_temp"].chunk({"time": -1, "lat": 40, "lon": 40})
        daily_max, daily_min = T.resample(time="1D").max(), T.resample(time="1D").min()
        f["t_mean"] = T.mean("time")
        f["t_amp"] = (daily_max - daily_min).mean("time")
        f["t_p05"] = T.quantile(0.05, "time", skipna=True).drop_vars("quantile")
        f["t_p95"] = T.quantile(0.95, "time", skipna=True).drop_vars("quantile")
        f["amp_ratio"] = f["t_amp"] / f["t_mean"]                       # dimensionless
        f["freeze_thaw_days"] = ((daily_min < TFREEZE) & (daily_max > TFREEZE)).sum("time").astype("float32")
        if "sw_net" in ds: f["sw_net_mean"] = ds["sw_net"].mean("time")
        if "lw_net" in ds: f["lw_net_mean"] = ds["lw_net"].mean("time")
        if "soil_moist" in ds: f["soil_moist_mean"] = ds["soil_moist"].mean("time")
        if "wind" in ds: f["wind_mean"] = ds["wind"].mean("time")
        if "pressure" in ds: f["pressure_pa"] = ds["pressure"].mean("time")
        if "albedo" in ds:
            a = ds["albedo"].mean("time")
            alb = a / (100.0 if float(a.max()) > 1.5 else 1.0)
        else:
            alb = 0.25
        f["ati"] = (1 - alb) / f["t_amp"].where(f["t_amp"] > 0.5)       # Price (1977) apparent thermal inertia proxy
        f["obs_frac"] = T.notnull().mean("time")
    if geometry is not None:
        for v in geometry.data_vars:
            f[v] = geometry[v].interp(lat=f["lat"], lon=f["lon"]) if ds is not None else geometry[v]
    if sar_texture is not None:
        f["sar_texture_db"] = sar_texture.interp(lat=f["lat"], lon=f["lon"]) if ds is not None else sar_texture
    return f
