"""Terrain metrics shared by Earth and Moon (methodology v2, docs/METHOD.md).

One function, `window_metrics`, is applied to a square elevation window sampled on a metric grid with the
SAME pixel size and the SAME window size on both bodies (40 m pixels, 25 x 25 pixels = 1 km). This removes
the baseline mismatch of v1 (Earth ~30 m geographic pixels vs Moon 40 m) since slope depends on baseline.

Metrics (all on a 1 km window):
    slope_mean            mean of the 40 m-baseline slope (degrees)
    slope_p95             95th percentile of slope (degrees); replaces slope_max, an extreme-value statistic
                          dominated by DEM noise and artefacts
    slope_max             kept for continuity with v1
    roughness             standard deviation of elevation (m): v1 definition, kept for continuity. It is
                          dominated by the regional tilt (see docs/wiki/v2/SCIENTIFIC_AUDIT.md, finding T2)
    roughness_detrended   standard deviation of the residuals after removing the least-squares plane (m):
                          relief that is NOT explained by the mean tilt
    traversable_15/20/25  fraction of the window area with slope <= 15, 20, 25 degrees (0 to 1)

What these metrics do NOT measure: anything below the DEM baseline (rocks, small craters, wheel-scale
slopes). A 40 m baseline systematically underestimates the slopes a rover meets at 1 to 5 m scale.
"""
from __future__ import annotations

import numpy as np

PIXEL_M = 40.0
WINDOW_PX = 25
SLOPE_LIMITS_DEG = (15, 20, 25)
METRIC_KEYS = ("slope_mean", "slope_p95", "slope_max", "roughness", "roughness_detrended",
               "traversable_15", "traversable_20", "traversable_25")


def slope_deg(z: np.ndarray, pixel_m: float) -> np.ndarray:
    """Slope in degrees by central differences (one-sided on the edges). NaN propagates."""
    gy, gx = np.gradient(z, pixel_m)
    return np.degrees(np.arctan(np.hypot(gx, gy)))


def detrended_std(z: np.ndarray) -> float:
    """Standard deviation of the residuals of z after removing the least-squares plane a + b*x + c*y."""
    rows, cols = np.indices(z.shape)
    ok = np.isfinite(z)
    if ok.sum() < 4:
        return float("nan")
    a = np.column_stack([np.ones(ok.sum()), cols[ok], rows[ok]])
    coef, *_ = np.linalg.lstsq(a, z[ok], rcond=None)
    return float(np.std(z[ok] - a @ coef))


def window_metrics(z: np.ndarray, slope: np.ndarray) -> dict:
    """Metrics of one window. `z` and `slope` have the same shape; slope is computed by the caller on a larger
    array so that window edges use central differences."""
    ok = np.isfinite(z) & np.isfinite(slope)
    valid = float(ok.mean()) if z.size else 0.0
    if valid < 0.9:
        return {**{k: None for k in METRIC_KEYS}, "valid_frac": round(valid, 3)}
    s = slope[ok]
    out = {
        "slope_mean": float(s.mean()),
        "slope_p95": float(np.percentile(s, 95)),
        "slope_max": float(s.max()),
        "roughness": float(np.std(z[ok])),
        "roughness_detrended": detrended_std(z),
        "valid_frac": round(valid, 3),
    }
    for limit in SLOPE_LIMITS_DEG:
        out[f"traversable_{limit}"] = float((s <= limit).mean())
    return out


def grid_metrics(z: np.ndarray, pixel_m: float = PIXEL_M, window_px: int = WINDOW_PX,
                 mask: np.ndarray | None = None) -> list[dict]:
    """Metrics of every non-overlapping window of `window_px` pixels in `z` (row-major order).
    A window is kept only if all its pixels are inside `mask` (when given)."""
    slope = slope_deg(z.astype("float64"), pixel_m)
    out = []
    for r in range(0, z.shape[0] - window_px + 1, window_px):
        for c in range(0, z.shape[1] - window_px + 1, window_px):
            sl = (slice(r, r + window_px), slice(c, c + window_px))
            if mask is not None and not mask[sl].all():
                continue
            out.append(window_metrics(z[sl].astype("float64"), slope[sl]))
    return out


def robust_sigma(values: list[float]) -> float | None:
    """Robust spread (1.4826 x median absolute deviation) of the finite values; None if fewer than 3."""
    v = np.array([x for x in values if x is not None and np.isfinite(x)], dtype="float64")
    if v.size < 3:
        return None
    return float(1.4826 * np.median(np.abs(v - np.median(v))))
