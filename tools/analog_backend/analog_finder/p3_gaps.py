"""Phase 3 - Data-gap / uncertainty detection and extreme-microclimate identification."""
from __future__ import annotations
import numpy as np
import pandas as pd
import xarray as xr
from scipy.spatial import cKDTree
from sklearn.covariance import MinCovDet
from sklearn.preprocessing import RobustScaler

TFREEZE = 273.15


def _rank01(a: np.ndarray) -> np.ndarray:
    out = np.full(a.shape, np.nan)
    m = np.isfinite(a)
    out[m] = pd.Series(a[m]).rank(pct=True).values
    return out


# ---------- (a) Temporal gaps ----------
def temporal_gap_stats(da: xr.DataArray, dim="time", block: int = 48) -> xr.Dataset:
    """Missing fraction + longest consecutive NaN run per cell. Streams through time in blocks (dask-friendly)."""
    da = da.transpose(dim, "lat", "lon")
    miss = da.isnull()
    frac = miss.mean(dim).compute()
    run = np.zeros(frac.shape, int); longest = np.zeros(frac.shape, int)
    for t0 in range(0, miss.sizes[dim], block):
        blk = miss.isel({dim: slice(t0, t0 + block)}).values
        for t in range(blk.shape[0]):
            run = np.where(blk[t], run + 1, 0)
            longest = np.maximum(longest, run)
    return xr.Dataset({"missing_frac": frac,
                       "longest_gap": xr.DataArray(longest, coords=frac.coords, dims=frac.dims)})


def residual_uncertainty(da: xr.DataArray) -> xr.DataArray:
    """Temporal unpredictability: std of residual after removing the mean diurnal cycle (hour-of-day climatology)."""
    clim = da.groupby("time.hour").mean("time")
    return (da.groupby("time.hour") - clim).std("time")


# ---------- (b) Spatial gaps ----------
def _xyz(lat, lon):
    la, lo = np.deg2rad(lat), np.deg2rad(lon)
    return np.c_[np.cos(la) * np.cos(lo), np.cos(la) * np.sin(lo), np.sin(la)]


def station_distance_gap(f: xr.Dataset, stations: pd.DataFrame) -> xr.DataArray:
    """Geographic gap: great-circle distance (km) from each cell to the nearest in-situ station.
    `stations` needs columns lat, lon (SNOTEL, USCRN, ISD, Environment Canada, ...)."""
    LAT, LON = np.meshgrid(f["lat"].values, f["lon"].values, indexing="ij")
    tree = cKDTree(_xyz(stations["lat"].values, stations["lon"].values))
    d, _ = tree.query(_xyz(LAT.ravel(), LON.ravel()))
    km = 2 * 6371 * np.arcsin(np.clip(d / 2, 0, 1))
    return xr.DataArray(km.reshape(LAT.shape), coords={"lat": f["lat"], "lon": f["lon"]}, dims=("lat", "lon"))


def feature_space_gap(f: xr.Dataset, stations: pd.DataFrame, feats: list[str], k: int = 3) -> xr.DataArray:
    """Representativeness gap: how far (in standardized feature space) is each cell from the *nearest station's* feature vector?
    High value = this environment is not sampled by any station even if a station is geographically close."""
    df = f[feats].to_dataframe().reset_index()
    X = RobustScaler().fit_transform(df[feats].values)
    ok = np.isfinite(X).all(1)
    # station cells = nearest grid cell to each station
    gi = lambda arr, v: int(np.abs(arr - v).argmin())
    idx = [gi(f["lat"].values, r.lat) * f.sizes["lon"] + gi(f["lon"].values, r.lon) for r in stations.itertuples()]
    idx = [i for i in idx if ok[i]]
    tree = cKDTree(X[idx])
    kk = min(k, len(idx))
    dist = tree.query(X[ok], k=kk)[0]
    d = np.full(len(df), np.nan)
    d[ok] = dist.mean(1) if kk > 1 else dist
    return xr.DataArray(d.reshape(f.sizes["lat"], f.sizes["lon"]), coords={"lat": f["lat"], "lon": f["lon"]}, dims=("lat", "lon"))


def ensemble_spread(models: list[xr.DataArray]) -> xr.DataArray:
    """Structural uncertainty: inter-model std (e.g., NLDAS Noah vs Mosaic vs VIC vs SAC) of the same variable."""
    return xr.concat(models, "model").std("model")


def composite_gap_index(parts: dict[str, xr.DataArray], weights: dict[str, float] | None = None) -> xr.DataArray:
    """Rank-normalize each gap layer to [0,1] and combine. Higher = bigger observational/model blind spot."""
    weights = weights or {k: 1.0 for k in parts}
    tot = sum(weights.values())
    ref = next(iter(parts.values()))
    acc = np.zeros(ref.shape)
    for k, da in parts.items():
        acc += weights[k] * np.nan_to_num(_rank01(da.values), nan=0.5)
    return xr.DataArray(acc / tot, coords=ref.coords, dims=ref.dims, name="gap_index")


# ---------- (c) Extreme microclimates / analog regimes ----------
def robust_z(da: xr.DataArray) -> xr.DataArray:
    med = da.median(skipna=True)
    mad = np.abs(da - med).median(skipna=True) * 1.4826
    return (da - med) / mad


def mahalanobis_outlier(f: xr.Dataset, feats: list[str], support_fraction: float = 0.75) -> xr.DataArray:
    """Multivariate extremeness via Minimum Covariance Determinant (robust Mahalanobis). Large = extreme joint regime."""
    df = f[feats].to_dataframe().reset_index()
    X = df[feats].values
    ok = np.isfinite(X).all(1)
    mcd = MinCovDet(support_fraction=support_fraction, random_state=0).fit(X[ok])
    d = np.full(len(df), np.nan)
    d[ok] = np.sqrt(mcd.mahalanobis(X[ok]))
    return xr.DataArray(d.reshape(f.sizes["lat"], f.sizes["lon"]), coords={"lat": f["lat"], "lon": f["lon"]}, dims=("lat", "lon"), name="mahal")


def regime_masks(f: xr.Dataset, q: float = 0.95) -> xr.Dataset:
    """Boolean masks for the analog regimes the challenge cares about. Thresholds are quantiles -> self-calibrating.
    - low_pressure : lowest-q surface pressure (high elevation; Earth never reaches Mars' ~600 Pa, so use rank)
    - radiation    : high net shortwave AND large diurnal amplitude (thin/dry-atmosphere-like forcing)
    - permafrost   : sub-freezing mean + frequent freeze-thaw crossings (active-layer dynamics)
    - cold_extreme : coldest p05 skin temperature (PSR-like cold-trap proxy)"""
    m = xr.Dataset()
    if "pressure_pa" in f: m["low_pressure"] = f["pressure_pa"] <= f["pressure_pa"].quantile(1 - q)
    if "sw_net_mean" in f: m["radiation"] = (f["sw_net_mean"] >= f["sw_net_mean"].quantile(q)) & (f["t_amp"] >= f["t_amp"].quantile(q - 0.1))
    m["permafrost"] = (f["t_mean"] < TFREEZE) & (f["freeze_thaw_days"] >= f["freeze_thaw_days"].quantile(0.75))
    m["cold_extreme"] = f["t_p05"] <= f["t_p05"].quantile(1 - q)
    return m


def gap_x_extreme(gap: xr.DataArray, mahal: xr.DataArray, q: float = 0.8) -> xr.DataArray:
    """Critical zones = extreme microclimate AND poorly observed (the project's core thesis)."""
    return (gap >= gap.quantile(q)) & (mahal >= mahal.quantile(q))
