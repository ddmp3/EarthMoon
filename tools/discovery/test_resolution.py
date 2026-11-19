"""Effective resolution experiment (T41, finding L3). Synthetic surfaces only."""
import numpy as np
import pytest

from discovery.resolution import compare_pairs, gaussian_smooth, match_sigma
from discovery.spectrum import radial_spectrum, spectral_ratio


def test_gaussian_smoothing_keeps_the_mean_and_removes_short_waves():
    rng = np.random.default_rng(1)
    z = rng.normal(size=(64, 64)) + 100.0
    s = gaussian_smooth(z, 2.0)
    assert s.mean() == pytest.approx(z.mean(), abs=0.01) and s.std() < z.std() / 2   # reflected edges: not exact
    assert np.array_equal(gaussian_smooth(z, 0.0), z)


def test_compare_pairs_reports_ratio_rank_correlation_and_differences():
    a = np.array([1.0, 2.0, 3.0, 4.0, np.nan])
    out = compare_pairs(a, 2 * a)
    assert out["n"] == 4 and out["median_ratio"] == 2.0 and out["spearman"] == pytest.approx(1.0)
    assert out["abs_diff"]["median"] == 2.5


def test_match_sigma_finds_the_smoothing_that_brings_a_spectral_ratio_down_to_a_target():
    rng = np.random.default_rng(2)
    blocks = [np.cumsum(np.cumsum(rng.normal(size=(64, 64)), 0), 1) + rng.normal(0, 5, (64, 64)) for _ in range(4)]
    ratio = lambda b: spectral_ratio(*radial_spectrum(b, 40.0), 40.0, 160.0, 2000.0)
    target = float(np.median([ratio(gaussian_smooth(b, 1.5)) for b in blocks]))
    got = match_sigma(blocks, target, sigmas=(0.0, 0.5, 1.0, 1.5, 2.0, 3.0), pixel_m=40.0)
    assert got["sigma_px"] == 1.5


def test_nan_aware_smoothing_keeps_missing_pixels_missing_and_does_not_pull_values_to_zero():
    from discovery.resolution import gaussian_smooth_nan
    z = np.full((40, 40), 100.0)
    z[:, :10] = np.nan                                            # sea on the west side
    s = gaussian_smooth_nan(z, 1.5)
    assert np.isnan(s[:, :10]).all() and np.allclose(s[:, 10:], 100.0)
    assert np.array_equal(gaussian_smooth_nan(z, 0.0), z, equal_nan=True)
