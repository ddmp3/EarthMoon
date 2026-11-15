"""Per-domain Earth feature builders. Each domain is processed independently (own grid, own inputs) and later concatenated.

  NLDAS        CONUS, 0.125 deg hourly: Noah (surface/soil/radiation) + FORA (wind/pressure) [+ optional DEM]
  RCM_Arctic   Canadian Arctic  SAR (RCM sigma0 GeoTIFFs) + optional DEM + optional thermal NetCDF (e.g. a reanalysis)
  RCM_Antarctic Antarctica      same as above
RCM is a SAR mission: it has NO temperature/wind/pressure. RCM cells therefore carry geometry + SAR texture only (thermal
features NaN) unless you supply `thermal` NetCDF files; scoring is then partial and flagged via `coverage`.
"""
from __future__ import annotations
import glob
import logging
from dataclasses import dataclass, field
import numpy as np
import pandas as pd
import xarray as xr

from . import p2_ingest as p2, p3_gaps as p3
from .p1_audit import audit_dataset, audit_raster, value_score

log = logging.getLogger(__name__)
SOURCES = ("NLDAS", "RCM_Arctic", "RCM_Antarctic")
CLUSTER_OFFSET = {"NLDAS": 0, "RCM_Arctic": 100, "RCM_Antarctic": 200}
EXTREME_CANDIDATES = ["t_mean", "t_amp", "pressure_pa", "sw_net_mean", "freeze_thaw_days",
                      "slope_deg", "roughness_m", "sar_texture_db"]
CLUSTER_CANDIDATES = ["t_mean", "t_amp", "t_p05", "pressure_pa", "slope_deg", "roughness_m", "shadow_frac", "sar_texture_db"]


def _expand(patterns) -> list[str]:
    out: list[str] = []
    for p in patterns or []:
        out += sorted(glob.glob(p)) or ([p] if "*" not in p else [])
    return out


@dataclass
class DomainSpec:
    name: str
    bbox: tuple[float, float, float, float]            # lon0, lat0, lon1, lat1
    grid_res_deg: float = 0.125
    noah: list[str] = field(default_factory=list)
    fora: list[str] = field(default_factory=list)
    thermal: list[str] = field(default_factory=list)   # optional extra NetCDF thermal source for RCM domains
    dem: str | None = None
    rcm: list[str] = field(default_factory=list)
    rcm_is_db: bool = False
    stations_csv: str | None = None                    # columns lat,lon

    def __post_init__(self):
        if self.name not in SOURCES:
            raise ValueError(f"domain name must be one of {SOURCES}")
        self.bbox = tuple(self.bbox)
        for a in ("noah", "fora", "thermal", "rcm"):
            setattr(self, a, _expand(getattr(self, a)))

    @classmethod
    def from_dict(cls, d: dict):
        return cls(**d)


def audit_domain(spec: DomainSpec) -> dict:
    """Phase 1 per domain: audit ONE file of each input group; never touches the bulk data."""
    rep: dict = {"domain": spec.name}
    groups = {"noah": ("skin_temp", "sw_net", "lw_net", "soil_moist"), "fora": ("wind_u", "wind_v", "pressure"),
              "thermal": ("skin_temp",)}
    for g, need in groups.items():
        paths = getattr(spec, g)
        if paths:
            s, d = audit_dataset(paths[0])
            rep[g] = {"summary": s, "value": value_score(s, d, need=need, nice=()), "n_files": len(paths)}
    if spec.dem:
        rep["dem"] = audit_raster(spec.dem)
    if spec.rcm:
        rep["rcm"] = {"n_files": len(spec.rcm), "first": audit_raster(spec.rcm[0])}
    return rep


def _usable(f: xr.Dataset, cands: list[str], min_finite=0.9) -> list[str]:
    ok = []
    for c in cands:
        if c in f:
            v = f[c].values
            if np.isfinite(v).mean() >= min_finite and np.nanstd(v) > 0:
                ok.append(c)
    return ok


def build_domain(spec: DomainSpec, baseline_m: float, sun_elev_deg: float) -> tuple[pd.DataFrame, dict]:
    """Return (cell table incl. gap/extreme layers, info dict)."""
    ds = None
    if spec.name == "NLDAS":
        if not spec.noah:
            raise ValueError("NLDAS domain needs `noah` files")
        ds = p2.open_nldas(spec.noah, spec.fora, spec.bbox)
        template = ds["skin_temp"].isel(time=0, drop=True).reset_coords(drop=True)
    else:
        template = p2.make_template(spec.bbox, spec.grid_res_deg)
        if spec.thermal:
            ds = p2.regrid(p2.open_stack(spec.thermal, spec.bbox), template)
    geometry = p2.geometry_layers_on_grid(spec.dem, template, baseline_m, sun_elev_deg=sun_elev_deg) if spec.dem else None
    tex = None
    if spec.rcm:
        layers = [p2.sar_texture_on_grid(p, template, is_db=spec.rcm_is_db) for p in spec.rcm]
        tex = xr.concat(layers, "scene").mean("scene", skipna=True)
    f = p2.build_features(ds, geometry, tex).compute()

    # ---- Phase 3: gaps + extremes ----
    parts, miss = {}, None
    if ds is not None:
        T = ds["skin_temp"]
        tg = p3.temporal_gap_stats(T)
        miss = tg["missing_frac"]
        parts["missing"] = miss
        parts["resid_unc"] = p3.residual_uncertainty(T).compute()
    ext = _usable(f, EXTREME_CANDIDATES)
    if spec.stations_csv:
        st = pd.read_csv(spec.stations_csv)
        parts["station_km"] = p3.station_distance_gap(f, st)
        if len(ext) >= 2:
            parts["feature_gap"] = p3.feature_space_gap(f, st, ext)
    gap = p3.composite_gap_index(parts) if parts else xr.full_like(f[list(f.data_vars)[0]], np.nan, dtype=float)
    try:
        mahal = p3.mahalanobis_outlier(f, ext) if len(ext) >= 2 else xr.full_like(gap, np.nan)
    except Exception as e:                                  # singular covariance etc.
        log.warning("%s: Mahalanobis skipped (%s)", spec.name, e)
        mahal = xr.full_like(gap, np.nan)
    crit = p3.gap_x_extreme(gap, mahal) if np.isfinite(gap.values).any() and np.isfinite(mahal.values).any() \
        else xr.zeros_like(gap, dtype=bool)

    extra = {"gap_index": gap, "mahal": mahal, "critical": crit}
    if miss is not None:
        extra["missing_frac"] = miss
    g = f.copy()
    for k, v in extra.items():
        g[k] = v
    df = g.to_dataframe().reset_index()
    df.insert(0, "source", spec.name)
    info = {"n_cells": len(df), "extreme_features": ext, "cluster_features": _usable(f, CLUSTER_CANDIDATES),
            "has_thermal": "t_p05" in f, "has_geometry": geometry is not None}
    return df, info
