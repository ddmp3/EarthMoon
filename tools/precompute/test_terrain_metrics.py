"""Tests of the shared Earth/Moon terrain metrics (analytic surfaces with known answers)."""
import math

import numpy as np
import pytest

from terrain_metrics import PIXEL_M, WINDOW_PX, detrended_std, grid_metrics, robust_sigma, slope_deg, window_metrics


def plane(shape, slope_deg_x, pixel_m=PIXEL_M):
    cols = np.indices(shape)[1]
    return cols * pixel_m * math.tan(math.radians(slope_deg_x))


def metrics(z):
    return window_metrics(z, slope_deg(z, PIXEL_M))


def test_tilted_plane_has_its_slope_and_no_detrended_roughness():
    m = metrics(plane((25, 25), 10.0))
    assert m["slope_mean"] == pytest.approx(10.0, abs=1e-6)
    assert m["slope_p95"] == pytest.approx(10.0, abs=1e-6)
    assert m["roughness_detrended"] == pytest.approx(0.0, abs=1e-6)


def test_v1_roughness_of_a_plane_is_pure_tilt():
    """The v1 metric is non-zero on a perfectly smooth tilted plane: it measures tilt, not roughness."""
    m = metrics(plane((25, 25), 10.0))
    expected = np.std(np.arange(25) * PIXEL_M * math.tan(math.radians(10.0)))
    assert m["roughness"] == pytest.approx(expected, rel=1e-9)
    assert m["roughness"] > 40


def test_detrended_roughness_recovers_added_relief():
    rng = np.random.default_rng(1)
    noise = rng.normal(0, 5.0, (25, 25))
    m = metrics(plane((25, 25), 8.0) + noise)
    assert m["roughness_detrended"] == pytest.approx(5.0, rel=0.1)


def test_traversable_fractions():
    z = np.hstack([plane((25, 13), 5.0), plane((25, 12), 30.0) + 13 * PIXEL_M * math.tan(math.radians(5.0))])
    m = metrics(z)
    assert 0.4 < m["traversable_15"] < 0.6
    # The single transition column has an intermediate central-difference slope.
    assert m["traversable_15"] <= m["traversable_20"] <= m["traversable_25"] < 0.6
    assert metrics(plane((25, 25), 3.0))["traversable_15"] == 1.0


def test_flat_window():
    m = metrics(np.zeros((25, 25)))
    assert m["slope_mean"] == 0 and m["roughness"] == 0 and m["roughness_detrended"] == 0
    assert m["traversable_15"] == 1.0


def test_window_with_too_many_gaps_is_missing_not_zero():
    z = np.zeros((25, 25))
    z[:5, :] = np.nan
    m = metrics(z)
    assert m["slope_mean"] is None and m["roughness_detrended"] is None
    assert m["valid_frac"] < 0.9


def test_grid_metrics_splits_into_windows_and_applies_mask():
    z = plane((75, 75), 6.0)
    assert len(grid_metrics(z)) == 9
    mask = np.ones((75, 75), dtype=bool)
    mask[0, 0] = False
    assert len(grid_metrics(z, mask=mask)) == 8
    assert all(m["slope_mean"] == pytest.approx(6.0, abs=1e-6) for m in grid_metrics(z))
    assert WINDOW_PX * PIXEL_M == 1000


def test_detrended_std_needs_points():
    assert math.isnan(detrended_std(np.full((2, 2), np.nan)))


def test_robust_sigma():
    assert robust_sigma([1, 2]) is None
    assert robust_sigma([1, 2, 3, 4, 100]) == pytest.approx(1.4826, rel=1e-6)
    assert robust_sigma([5, 5, 5, None]) == 0
