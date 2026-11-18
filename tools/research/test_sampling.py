"""Tests of the sampling experiments (task T22). Synthetic data only."""
import numpy as np
import pytest

from sampling import contrast_rows, pick_land_tiles, radial_spectrum, spectral_ratio
# block_mean, window_slope_means, cells_by_coordinate and screening_misses moved to tools/discovery (T40)


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












def test_spectrum_of_a_smoothed_surface_loses_high_frequencies():
    rng = np.random.default_rng(0)
    z = rng.normal(size=(128, 128))
    smooth = block_mean(np.kron(block_mean(z, 4), np.ones((4, 4))), 1)
    k1, p1 = radial_spectrum(z, 40.0)
    k2, p2 = radial_spectrum(smooth, 40.0)
    assert spectral_ratio(k2, p2, 40.0, 160.0, 2000.0) < spectral_ratio(k1, p1, 40.0, 160.0, 2000.0)
