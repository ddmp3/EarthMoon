"""Terrain power spectra (moved with its test from tools/research in T41)."""
import numpy as np

from discovery.spectrum import radial_spectrum, spectral_ratio
from discovery.windows import block_mean


def test_spectrum_of_a_smoothed_surface_loses_high_frequencies():
    rng = np.random.default_rng(0)
    z = rng.normal(size=(128, 128))
    smooth = block_mean(np.kron(block_mean(z, 4), np.ones((4, 4))), 1)
    k1, p1 = radial_spectrum(z, 40.0)
    k2, p2 = radial_spectrum(smooth, 40.0)
    assert spectral_ratio(k2, p2, 40.0, 160.0, 2000.0) < spectral_ratio(k1, p1, 40.0, 160.0, 2000.0)
