"""Window metrics on a metric grid, vectorised (T40).

Same definitions as the v2 reference `tools/precompute/terrain_metrics.window_metrics` (a test checks equality):
slope by central differences on the whole array, then non-overlapping windows of `window_px` pixels; a window
is valid when at least 90% of its pixels have both an elevation and a slope.

Stored metrics follow `data/parameters.yaml`: `slope_mean` (keep) and `roughness_detrended`, `traversable_15`,
`traversable_20` (context). The dropped metrics can still be computed (`ALL_METRICS`) for the v2 anchor.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "precompute"))
from terrain_metrics import slope_deg  # noqa: E402  (one slope implementation for v2 and v3)

MIN_VALID = 0.9
STORED_METRICS = ("slope_mean", "roughness_detrended", "traversable_15", "traversable_20")
ALL_METRICS = ("slope_mean", "slope_p95", "slope_max", "roughness", "roughness_detrended",
               "traversable_15", "traversable_20", "traversable_25")
FLAT_SLOPE_DEG = 1e-6


def _blocks(a: np.ndarray, n: int, margin: int) -> np.ndarray:
    """(rows, cols, n, n) view of the non-overlapping windows inside the margin."""
    core = a[margin:a.shape[0] - margin, margin:a.shape[1] - margin]
    h, w = (core.shape[0] // n) * n, (core.shape[1] // n) * n
    return core[:h, :w].reshape(h // n, n, w // n, n).transpose(0, 2, 1, 3)


def _detrended_std(zb: np.ndarray) -> np.ndarray:
    """Std of residuals after the least-squares plane a + b*col + c*row, per window, over finite z."""
    n = zb.shape[-1]
    rows, cols = np.indices((n, n), dtype="float64")
    ok = np.isfinite(zb)
    z = np.where(ok, zb, 0.0)
    w = ok.astype("float64")
    x, y = cols, rows
    s = lambda a: (a * w).sum(axis=(-2, -1))
    m = np.stack([np.stack([s(np.ones_like(x)), s(x), s(y)], -1),
                  np.stack([s(x), s(x * x), s(x * y)], -1),
                  np.stack([s(y), s(x * y), s(y * y)], -1)], -2)
    rhs = np.stack([(z * w).sum(axis=(-2, -1)), (z * x * w).sum(axis=(-2, -1)), (z * y * w).sum(axis=(-2, -1))], -1)
    enough = w.sum(axis=(-2, -1)) >= 4
    m = np.where(enough[..., None, None], m, np.eye(3))
    coef = np.linalg.solve(m, rhs[..., None])[..., 0]
    pred = coef[..., 0, None, None] + coef[..., 1, None, None] * x + coef[..., 2, None, None] * y
    res = np.where(ok, zb - pred, np.nan)
    with np.errstate(invalid="ignore"):
        out = np.sqrt(np.nanmean((res - np.nanmean(res, axis=(-2, -1), keepdims=True)) ** 2, axis=(-2, -1)))
    return np.where(enough, out, np.nan)


def window_metrics_grid(z: np.ndarray, pixel_m: float, window_px: int, margin: int = 1,
                        metrics: tuple[str, ...] = STORED_METRICS) -> dict[str, np.ndarray]:
    """Metrics of every window of `window_px` pixels inside `margin`. Invalid windows are NaN.
    Returns arrays of shape (rows, cols) for each metric, plus `valid_frac` and `flat`."""
    z = z.astype("float64")
    slope = slope_deg(z, pixel_m)
    zb, sb = _blocks(z, window_px, margin), _blocks(slope, window_px, margin)
    ok = np.isfinite(zb) & np.isfinite(sb)
    valid = np.round(ok.mean(axis=(-2, -1)), 3)
    good = ok.mean(axis=(-2, -1)) >= MIN_VALID
    s = np.where(ok, sb, np.nan)
    out: dict[str, np.ndarray] = {"valid_frac": valid}
    with np.errstate(invalid="ignore"), _quiet():
        smax = np.nanmax(np.where(good[..., None, None], s, np.nan), axis=(-2, -1))
        for k in metrics:
            if k == "slope_mean":
                v = np.nanmean(s, axis=(-2, -1))
            elif k == "slope_p95":
                v = np.nanpercentile(s, 95, axis=(-2, -1))
            elif k == "slope_max":
                v = smax
            elif k == "roughness":
                v = np.nanstd(np.where(ok, zb, np.nan), axis=(-2, -1))
            elif k == "roughness_detrended":
                v = _detrended_std(zb)
            elif k.startswith("traversable_"):
                limit = float(k.split("_")[1])
                v = np.where(ok, sb <= limit, False).sum(axis=(-2, -1)) / np.maximum(ok.sum(axis=(-2, -1)), 1)
            else:
                raise KeyError(k)
            out[k] = np.where(good, v, np.nan)
    out["flat"] = good & (smax < FLAT_SLOPE_DEG)
    return out


class _quiet:
    """Silence numpy's 'all-NaN slice' warnings for invalid windows (they are NaN by design)."""
    def __enter__(self):
        import warnings
        self._w = warnings.catch_warnings()
        self._w.__enter__()
        warnings.simplefilter("ignore", RuntimeWarning)

    def __exit__(self, *exc):
        return self._w.__exit__(*exc)


# --- moved from tools/research/sampling.py (T22) ---------------------------------------------------------

def block_mean(z: np.ndarray, f: int) -> np.ndarray:
    """Mean of f x f blocks; a block with any missing pixel is missing."""
    h, w = (z.shape[0] // f) * f, (z.shape[1] // f) * f
    return z[:h, :w].reshape(h // f, f, w // f, f).mean(axis=(1, 3))


def window_slope_means(z: np.ndarray, pixel_m: float, window_m: float) -> np.ndarray:
    """Mean slope of each non-overlapping window; NaN when fewer than 90% of its pixels have a slope."""
    s = slope_deg(z.astype("float64"), pixel_m)
    n = max(int(round(window_m / pixel_m)), 1)
    h, w = (s.shape[0] // n) * n, (s.shape[1] // n) * n
    blocks = s[:h, :w].reshape(h // n, n, w // n, n)
    valid = np.isfinite(blocks).mean(axis=(1, 3))
    with np.errstate(invalid="ignore"), _quiet():
        mean = np.nanmean(blocks, axis=(1, 3))
    return np.where(valid >= MIN_VALID, mean, np.nan)


def window_px_m(window_m: float, pixel_m: float) -> float:
    """Actual window length: a whole number of pixels (1 km at 90 m is 11 pixels, 990 m)."""
    return max(int(round(window_m / pixel_m)), 1) * pixel_m


def cells_by_coordinate(values: np.ndarray, window_m: float, cell_m: float) -> dict:
    """Group a grid of window values into square cells of cell_m by the coordinates of the window centres."""
    cells: dict = {}
    for r in range(values.shape[0]):
        for c in range(values.shape[1]):
            key = (int((r + 0.5) * window_m // cell_m), int((c + 0.5) * window_m // cell_m))
            cells.setdefault(key, []).append(values[r, c])
    return cells


def screening_misses(fine: dict, passed: dict, lo: float, hi: float) -> dict:
    """fine: cell -> fine-scale window values; passed: cell -> did the coarse stage keep it.
    A fine match is a window inside [lo, hi]; a miss is a fine match inside a rejected cell."""
    matches = {c: sum(lo <= v <= hi for v in vals) for c, vals in fine.items()}
    return {"fine_matches": sum(matches.values()), "missed": sum(m for c, m in matches.items() if not passed[c]),
            "cells": len(fine), "cells_passed": sum(bool(passed[c]) for c in fine)}
