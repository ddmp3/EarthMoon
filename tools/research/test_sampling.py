"""Tests of the sampling experiments (task T22). Synthetic data only."""
import numpy as np
import pytest

from sampling import (block_mean, contrast_rows, pick_land_tiles, radial_spectrum, screening_misses,
                      spectral_ratio, window_slope_means)


def test_pick_land_tiles_is_seeded_area_weighted_and_skips_ocean():
    exists = lambda lat, lon: lon % 2 == 0          # every other tile is "ocean"
    a = pick_land_tiles(20261117, 50, exists)
    assert a == pick_land_tiles(20261117, 50, exists)
    assert len(a) == 50 and len(set(a)) == 50 and all(lon % 2 == 0 for _, lon in a)
    lats = np.array([lat for lat, _ in pick_land_tiles(1, 2000, lambda la, lo: True)])
    assert 0.47 < np.mean(np.abs(lats + 0.5) < 30) < 0.53   # equal-area: half the area within 30° of the equator


def test_contrast_rows_take_the_rows_nearest_the_quantiles_and_skip_flat():
    rows = [{"lat": i, "lon": i, "slope_mean": float(i), "flat": i == 0} for i in range(101)]
    picked = contrast_rows(rows, (0.1, 0.5, 0.95))
    assert [r["slope_mean"] for r in picked] == [11.0, 50.0, 95.0]   # median 50.5 is a tie: the lower row wins


def test_block_mean_degrades_and_ignores_partial_blocks():
    z = np.arange(36, dtype=float).reshape(6, 6)
    out = block_mean(z, 3)
    assert out.shape == (2, 2) and out[0, 0] == pytest.approx(z[:3, :3].mean())
    z[0, 0] = np.nan
    assert np.isnan(block_mean(z, 3)[0, 0])


def test_window_slope_means_of_a_tilted_plane():
    x = np.arange(100) * 40.0
    z = np.tile(x * np.tan(np.radians(10)), (100, 1))
    out = window_slope_means(z, 40.0, 1000.0)
    assert out.shape == (4, 4) and np.allclose(out, 10, atol=0.01)


def test_window_with_too_many_missing_pixels_is_nan():
    z = np.zeros((50, 50))
    z[:, :20] = np.nan
    assert np.isnan(window_slope_means(z, 40.0, 2000.0)).all()


def test_screening_counts_matches_lost_in_rejected_cells():
    fine = {"a": [5.0, 30.0], "b": [6.0], "c": [40.0]}
    passed = {"a": True, "b": False, "c": False}
    out = screening_misses(fine, passed, lo=4.0, hi=10.0)
    assert out == {"fine_matches": 2, "missed": 1, "cells": 3, "cells_passed": 1}


def test_windows_are_grouped_into_cells_by_their_centre_coordinates():
    from sampling import cells_by_coordinate
    vals = np.arange(36, dtype=float).reshape(6, 6)       # 6 x 6 windows of 990 m
    cells = cells_by_coordinate(vals, 990.0, 5000.0)
    # centres at 495, 1485, ..., 5445 m: the sixth window (5445 m) falls in the second cell
    assert sorted(len(v) for v in cells.values()) == [1, 5, 5, 25]
    assert cells[(0, 0)] == [vals[r, c] for r in range(5) for c in range(5)]


def test_spectrum_of_a_smoothed_surface_loses_high_frequencies():
    rng = np.random.default_rng(0)
    z = rng.normal(size=(128, 128))
    smooth = block_mean(np.kron(block_mean(z, 4), np.ones((4, 4))), 1)
    k1, p1 = radial_spectrum(z, 40.0)
    k2, p2 = radial_spectrum(smooth, 40.0)
    assert spectral_ratio(k2, p2, 40.0, 160.0, 2000.0) < spectral_ratio(k1, p1, 40.0, 160.0, 2000.0)
