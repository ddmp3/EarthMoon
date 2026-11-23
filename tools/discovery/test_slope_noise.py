"""Slope noise of a window from the stated DEM error (protocol mars-v2). Synthetic grids only."""
import numpy as np
import pytest

from discovery.slope_noise import sigma_from_le90, window_slope_noise


def test_le90_is_converted_to_a_gaussian_sigma():
    assert sigma_from_le90(2.0) == pytest.approx(2.0 / 1.6449, rel=1e-3)


def test_no_elevation_error_gives_no_slope_noise():
    z = np.add.outer(np.arange(52.0), np.arange(52.0)) * 3.0
    d = window_slope_noise(z, pixel_m=100.0, window_px=25, sigma_z=0.0, rng=np.random.default_rng(1), draws=2)
    assert d.size == 8 and np.allclose(d, 0.0)


def test_the_noise_falls_as_the_pixel_grows():
    rng = np.random.default_rng(3)
    z = rng.normal(0, 5, (77, 77)).cumsum(axis=0).cumsum(axis=1) * 0.01
    small = window_slope_noise(z, 115.0, 25, 1.2, np.random.default_rng(4), draws=3)
    large = window_slope_noise(z, 463.0, 25, 1.2, np.random.default_rng(4), draws=3)
    rms = lambda d: float(np.sqrt(np.mean(d ** 2)))  # noqa: E731
    assert rms(small) > 3 * rms(large) > 0


def test_on_flat_ground_noise_only_raises_the_slope():
    z = np.zeros((52, 52))
    d = window_slope_noise(z, 115.0, 25, 1.2, np.random.default_rng(5), draws=2)
    assert (d > 0).all()                                     # the bias is kept: rms, not std, is the noise
