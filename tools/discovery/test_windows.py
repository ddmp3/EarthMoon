"""Window metrics of the discovery pipeline (T40). Synthetic surfaces only."""
import sys
from pathlib import Path

import numpy as np
import pytest

from discovery.windows import (ALL_METRICS, block_mean, cells_by_coordinate, screening_misses, window_metrics_grid,
                               window_px_m, window_slope_means)

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "precompute"))
from terrain_metrics import slope_deg, window_metrics  # noqa: E402  (v2 reference implementation)


def plane(n, deg, px=40.0):
    x = np.arange(n) * px
    return np.tile(x * np.tan(np.radians(deg)), (n, 1))


def test_plane_gives_its_slope_zero_detrended_roughness_and_full_traversability():
    out = window_metrics_grid(plane(77, 10.0), 40.0, 25, margin=1)
    assert out["slope_mean"].shape == (3, 3)
    assert np.allclose(out["slope_mean"], 10.0, atol=1e-9)
    assert np.allclose(out["roughness_detrended"], 0.0, atol=1e-6)
    assert np.allclose(out["traversable_15"], 1.0) and np.allclose(out["traversable_20"], 1.0)
    assert np.all(out["valid_frac"] == 1.0)


def test_steep_plane_is_not_traversable_below_its_slope():
    out = window_metrics_grid(plane(52, 30.0), 40.0, 25, margin=1)
    assert np.allclose(out["traversable_20"], 0.0) and np.allclose(out["slope_mean"], 30.0)


def test_bowl_has_slope_rising_from_the_centre():
    n, px = 151, 40.0
    yy, xx = np.mgrid[0:n, 0:n] * px
    r2 = (xx - xx.mean()) ** 2 + (yy - yy.mean()) ** 2
    z = 1e-4 * r2                                   # paraboloid: slope grows with distance
    out = window_metrics_grid(z, px, 25, margin=13)
    s = out["slope_mean"]
    assert s[2, 2] < s[2, 0] and s[2, 2] < s[0, 2] and s[2, 2] < s[4, 4]
    assert np.isclose(s[0, 0], s[4, 4], rtol=1e-6)  # symmetric


@pytest.mark.parametrize("seed", [0, 1, 2])
def test_vectorised_metrics_equal_the_v2_window_metrics(seed):
    rng = np.random.default_rng(seed)
    z = np.cumsum(np.cumsum(rng.normal(0, 2, (77, 77)), 0), 1)  # rough random surface
    z[3, 40] = np.nan                                           # one hole: still valid (>= 90%)
    z[50:60, 1:26] = np.nan                                     # a window below 90%: invalid
    out = window_metrics_grid(z, 40.0, 25, margin=1, metrics=ALL_METRICS)
    slope = slope_deg(z, 40.0)
    for r in range(3):
        for c in range(3):
            sl = (slice(1 + r * 25, 1 + (r + 1) * 25), slice(1 + c * 25, 1 + (c + 1) * 25))
            ref = window_metrics(z[sl], slope[sl])
            assert out["valid_frac"][r, c] == ref["valid_frac"]
            for k in ALL_METRICS:
                if ref[k] is None:
                    assert np.isnan(out[k][r, c])
                else:
                    assert out[k][r, c] == pytest.approx(ref[k], rel=1e-9, abs=1e-9), (k, r, c)


def test_flat_window_is_flagged_as_editing_artefact():
    out = window_metrics_grid(np.zeros((27, 27)), 40.0, 25, margin=1)
    assert out["flat"][0, 0]


# --- moved from tools/research/sampling.py (T22) with their tests ---

def test_block_mean_degrades_and_ignores_partial_blocks():
    z = np.arange(36, dtype=float).reshape(6, 6)
    out = block_mean(z, 3)
    assert out.shape == (2, 2) and out[0, 0] == pytest.approx(z[:3, :3].mean())
    z[0, 0] = np.nan
    assert np.isnan(block_mean(z, 3)[0, 0])


def test_window_slope_means_of_a_tilted_plane():
    out = window_slope_means(plane(100, 10.0), 40.0, 1000.0)
    assert out.shape == (4, 4) and np.allclose(out, 10, atol=0.01)


def test_window_with_too_many_missing_pixels_is_nan():
    z = np.zeros((50, 50))
    z[:, :20] = np.nan
    assert np.isnan(window_slope_means(z, 40.0, 2000.0)).all()


def test_window_length_is_a_whole_number_of_pixels():
    assert window_px_m(1000.0, 40.0) == 1000.0 and window_px_m(1000.0, 90.0) == 990.0


def test_screening_counts_matches_lost_in_rejected_cells():
    fine = {"a": [5.0, 30.0], "b": [6.0], "c": [40.0]}
    passed = {"a": True, "b": False, "c": False}
    out = screening_misses(fine, passed, lo=4.0, hi=10.0)
    assert out == {"fine_matches": 2, "missed": 1, "cells": 3, "cells_passed": 1}


def test_windows_are_grouped_into_cells_by_their_centre_coordinates():
    vals = np.arange(36, dtype=float).reshape(6, 6)       # 6 x 6 windows of 990 m
    cells = cells_by_coordinate(vals, 990.0, 5000.0)
    assert sorted(len(v) for v in cells.values()) == [1, 5, 5, 25]
    assert cells[(0, 0)] == [vals[r, c] for r in range(5) for c in range(5)]
