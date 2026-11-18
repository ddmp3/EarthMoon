"""Terrain power spectra (moved from tools/research/sampling.py in T41; used by the effective resolution test)."""
from __future__ import annotations

import numpy as np


def radial_spectrum(z: np.ndarray, pixel_m: float) -> tuple[np.ndarray, np.ndarray]:
    """Radially averaged power spectrum of a square block after removing a plane, with a Hann taper."""
    n = z.shape[0]
    yy, xx = np.mgrid[0:n, 0:n]
    a = np.column_stack([np.ones(z.size), xx.ravel(), yy.ravel()])
    coef, *_ = np.linalg.lstsq(a, z.ravel(), rcond=None)
    r = (z.ravel() - a @ coef).reshape(n, n) * np.outer(np.hanning(n), np.hanning(n))
    p = np.abs(np.fft.fftshift(np.fft.fft2(r))) ** 2
    f = np.fft.fftshift(np.fft.fftfreq(n, d=pixel_m))
    k = np.hypot(*np.meshgrid(f, f))
    bins = np.linspace(0, k.max(), n // 2)
    idx = np.digitize(k.ravel(), bins)
    kk = np.array([k.ravel()[idx == i].mean() for i in range(1, len(bins)) if np.any(idx == i)])
    pp = np.array([p.ravel()[idx == i].mean() for i in range(1, len(bins)) if np.any(idx == i)])
    return kk, pp


def spectral_ratio(k: np.ndarray, p: np.ndarray, pixel_m: float, short_m: float, long_m: float) -> float:
    """Power near wavelength short_m relative to power near long_m (both bands +-25%)."""
    lam = 1 / np.where(k > 0, k, np.nan)
    near = lambda w: np.nanmean(np.where((lam >= w / 1.25) & (lam <= w * 1.25), p, np.nan))
    return float(near(short_m) / near(long_m))
