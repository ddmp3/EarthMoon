"""LRO ingestion: LOLA (elevation / slope / roughness / illumination) + Diviner (surface temperature) -> lunar cell table.

All rasters are read with rasterio, co-registered onto the LOLA grid (polar-stereographic GeoTIFF expected for the
south pole) and resampled to the SAME geometry baseline used for Earth DEMs. Output columns match p5_similarity.FEATURES.

Expected inputs (you supply the files; names depend on the PDS product you download):
  ldem           LOLA digital elevation model GeoTIFF (metres; GDAL scale/offset is honoured)
  slope/roughness  optional LOLA-derived GeoTIFFs (slope in degrees, RMS height deviation in metres). If omitted they are
                   derived from `ldem` at `baseline_m` with the same code used for Earth.
  illumination   optional fraction-of-time-in-sunlight raster (0-1 or 0-100). If omitted, shadow_frac is computed from the DEM.
  diviner_tmin / diviner_tmax / (diviner_tmean)  bolometric temperature rasters (K) giving the minimum and maximum (and mean)
                   of the diurnal/seasonal cycle. t_p05 <- tmin ; amp_ratio = (tmax-tmin)/tmean.
  thermal_inertia  optional Diviner-derived thermal inertia raster; otherwise ati = (1-albedo)/(tmax-tmin), the SAME proxy as Earth.
"""
from __future__ import annotations
import logging
from dataclasses import dataclass, fields
import numpy as np
import pandas as pd
from .p1_audit import audit_raster
from .p2_ingest import (R_MOON, read_at_baseline, shadow_fraction_array, slope_roughness_arrays, warp_array, warp_file)
from .p5_similarity import FEATURES

log = logging.getLogger(__name__)


@dataclass
class LROConfig:
    ldem: str
    diviner_tmin: str
    diviner_tmax: str
    diviner_tmean: str | None = None
    thermal_inertia: str | None = None
    slope: str | None = None
    roughness: str | None = None
    illumination: str | None = None
    baseline_m: float = 120.0
    aoi_radius_km: float = 150.0
    target_lat_max: float = -85.0       # target profile = cells poleward of this latitude
    albedo: float = 0.12
    sun_elevation_deg: float = 1.5
    n_az: int = 8
    max_steps: int = 40
    max_cells: int = 6_000_000

    @classmethod
    def from_dict(cls, d: dict, **defaults):
        known = {f.name for f in fields(cls)}
        return cls(**{**defaults, **{k: v for k, v in d.items() if k in known}})

    def raster_paths(self) -> list[str]:
        names = ("ldem", "diviner_tmin", "diviner_tmax", "diviner_tmean", "thermal_inertia", "slope", "roughness", "illumination")
        return [getattr(self, n) for n in names if getattr(self, n)]


def audit_lro(cfg: LROConfig) -> list[dict]:
    """Phase 1 for the lunar side: header-only audit of every raster."""
    return [audit_raster(p) for p in cfg.raster_paths()]


def load_lunar_table(cfg: LROConfig) -> tuple[pd.DataFrame, np.ndarray]:
    """Return (table with lat, lon, FEATURES..., aoi_mask array aligned with table rows)."""
    import rasterio
    from pyproj import CRS, Transformer
    with rasterio.open(cfg.ldem) as src:
        rcrs = src.crs
    if rcrs is None:
        raise ValueError(f"{cfg.ldem} has no CRS; LOLA GeoTIFFs must be georeferenced")
    pcrs = CRS.from_wkt(rcrs.to_wkt())
    geo = pcrs.geodetic_crs
    r_m = cfg.aoi_radius_km * 1000.0
    if rcrs.is_geographic:                                   # cylindrical product
        bounds = (-180.0, -90.0, 180.0, -90.0 + np.degrees(r_m / R_MOON))
        x0 = y0 = None
    else:                                                    # polar stereographic product
        x0, y0 = Transformer.from_crs(geo, pcrs, always_xy=True).transform(0.0, -90.0)
        bounds = (x0 - r_m, y0 - r_m, x0 + r_m, y0 + r_m)
        n_est = (2 * r_m / cfg.baseline_m) ** 2
        if n_est > cfg.max_cells:
            raise ValueError(f"AOI would produce ~{n_est:.0f} cells (> {cfg.max_cells}); raise baseline_m or lower aoi_radius_km")

    z, tr, crs, (dx, dy) = read_at_baseline(cfg.ldem, cfg.baseline_m, bounds, radius_m=R_MOON)
    shape = z.shape
    log.info("LOLA window: %s px @ ~%.0f m", shape, cfg.baseline_m)

    sd, rd = slope_roughness_arrays(z, dx, dy) if not (cfg.slope and cfg.roughness) else (None, None)
    slope = warp_file(cfg.slope, shape, tr, crs) if cfg.slope else sd
    rough = warp_file(cfg.roughness, shape, tr, crs) if cfg.roughness else rd
    if cfg.illumination:
        lit = warp_file(cfg.illumination, shape, tr, crs)
        lit = lit / 100.0 if np.nanmax(lit) > 1.5 else lit
        shadow = (1.0 - lit).clip(0, 1)
    else:
        shadow = shadow_fraction_array(z, dx, dy, cfg.sun_elevation_deg, cfg.n_az, cfg.max_steps)

    tmin = warp_file(cfg.diviner_tmin, shape, tr, crs)
    tmax = warp_file(cfg.diviner_tmax, shape, tr, crs)
    tmean = warp_file(cfg.diviner_tmean, shape, tr, crs) if cfg.diviner_tmean else (tmin + tmax) / 2
    swing = tmax - tmin
    with np.errstate(all="ignore"):
        amp_ratio = swing / tmean
        ati = warp_file(cfg.thermal_inertia, shape, tr, crs) if cfg.thermal_inertia else \
            np.where(swing > 0.5, (1 - cfg.albedo) / swing, np.nan)

    rows, cols = np.indices(shape)
    xs, ys = tr.c + tr.a * (cols + 0.5), tr.f + tr.e * (rows + 0.5)
    if rcrs.is_geographic:
        lon, lat = xs, ys
        inside = np.ones(shape, bool)
    else:
        lon, lat = Transformer.from_crs(pcrs, geo, always_xy=True).transform(xs, ys)
        inside = np.hypot(xs - x0, ys - y0) <= r_m
    tab = pd.DataFrame({"lat": np.ravel(lat), "lon": np.ravel(lon), "elev_m": z.ravel(),
                        "slope_deg": slope.ravel(), "roughness_m": rough.ravel(), "shadow_frac": shadow.ravel(),
                        "t_p05": tmin.ravel(), "amp_ratio": amp_ratio.ravel(), "ati": np.ravel(ati)})
    tab = tab[inside.ravel()].replace([np.inf, -np.inf], np.nan).dropna(subset=FEATURES).reset_index(drop=True)
    if tab.empty:
        raise ValueError("No valid lunar cells after co-registration; check CRS/bounds overlap between LOLA and Diviner rasters")
    return tab, (tab["lat"] <= cfg.target_lat_max).values
