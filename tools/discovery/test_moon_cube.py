"""Lunar window cube helpers (T41): iron split, map lookups, unit shares. Synthetic data only."""
import numpy as np
import pytest

from discovery.moon_cube import grid_lookup, otsu_split, unit_share


def test_otsu_split_separates_two_populations_and_respects_weights():
    rng = np.random.default_rng(0)
    v = np.concatenate([rng.normal(5, 0.5, 1000), rng.normal(17, 1.0, 400)])
    t = otsu_split(v, np.ones_like(v))
    assert 9 < t < 13                                             # middle of the empty gap between the classes
    u = np.concatenate([rng.normal(5, 2.0, 1000), rng.normal(12, 2.0, 1000)])   # overlapping classes
    even = otsu_split(u, np.ones_like(u))
    heavy_low = otsu_split(u, np.concatenate([np.full(1000, 5.0), np.ones(1000)]))
    assert 7 < even < 10 and abs(heavy_low - even) > 0.3          # area weights change the split


def test_grid_lookup_reads_the_cell_containing_each_point_with_east_or_signed_longitudes():
    grid = np.arange(4 * 8, dtype=float).reshape(4, 8)          # 45° cells, rows from 90°N, columns from 180°W
    v = grid_lookup(grid, lat=np.array([80.0, -80.0]), lon=np.array([-170.0, 350.0]), lat_top=90, lon_left=-180)
    assert v.tolist() == [0.0, grid[3, 3]]                         # 350°E is 10°W: column [-45°, 0°)


def test_unit_share_gives_the_majority_unit_and_its_share_and_zero_means_no_unit():
    samples = np.array([[3, 3, 3, 7], [0, 0, 0, 5], [2, 2, 4, 4]])
    unit, share = unit_share(samples)
    assert unit.tolist() == [3, 0, 2] and share.tolist() == [0.75, 0.75, 0.5]
