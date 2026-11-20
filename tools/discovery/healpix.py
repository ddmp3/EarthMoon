"""HEALPix grid, RING scheme (Gorski et al. 2005, ApJ 622:759), for the global cells of protocol v3.

Equal-area cells that keep a compact shape at every latitude, so the same 5 km cell exists everywhere, including
near the poles. Written with numpy (no external library); the formulas follow the HEALPix C++ library
(Healpix_Base: ang2pix, pix2ang, ring2xyf, xyf2ring, neighbors). Latitudes are used as they are on a sphere of
radius 6371.0088 km: the cell area on the ellipsoid then varies by less than 1%.
"""
from __future__ import annotations

import numpy as np

EARTH_R_KM = 6371.0088
NSIDE = 1303                                     # 12 * 1303^2 cells of 25.04 km^2: the 5 km cell of the method

_JRLL = np.array([2, 2, 2, 2, 3, 3, 3, 3, 4, 4, 4, 4])
_JPLL = np.array([1, 3, 5, 7, 0, 2, 4, 6, 1, 3, 5, 7])
_XOFF = np.array([-1, -1, 0, 1, 1, 1, 0, -1])
_YOFF = np.array([0, 1, 1, 1, 0, -1, -1, -1])
_FACES = np.array([[8, 9, 10, 11, -1, -1, -1, -1, 10, 11, 8, 9],       # S
                   [5, 6, 7, 4, 8, 9, 10, 11, 9, 10, 11, 8],          # SE
                   [-1, -1, -1, -1, 5, 6, 7, 4, -1, -1, -1, -1],      # E
                   [4, 5, 6, 7, 11, 8, 9, 10, 11, 8, 9, 10],          # SW
                   [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11],            # centre
                   [1, 2, 3, 0, 0, 1, 2, 3, 5, 6, 7, 4],              # NE
                   [-1, -1, -1, -1, 7, 4, 5, 6, -1, -1, -1, -1],      # W
                   [3, 0, 1, 2, 3, 0, 1, 2, 4, 5, 6, 7],              # NW
                   [2, 3, 0, 1, -1, -1, -1, -1, 0, 1, 2, 3]])         # N
_SWAP = np.array([[0, 0, 3], [0, 0, 6], [0, 0, 0], [0, 0, 5], [0, 0, 0], [5, 0, 0], [0, 0, 0], [6, 0, 0], [3, 0, 0]])


def cell_area_km2(n: int = NSIDE) -> float:
    return float(4 * np.pi * EARTH_R_KM ** 2 / (12 * n * n))


def _isqrt(v: np.ndarray) -> np.ndarray:
    r = np.floor(np.sqrt(v.astype(float))).astype(np.int64)
    r = np.where(r * r > v, r - 1, r)
    return np.where((r + 1) * (r + 1) <= v, r + 1, r)


def ang2pix(n: int, lat, lon) -> np.ndarray:
    """Cell of each point (degrees)."""
    lat = np.atleast_1d(np.asarray(lat, float))
    z = np.sin(np.radians(lat))
    za = np.abs(z)
    tt = np.mod(np.radians(np.atleast_1d(np.asarray(lon, float))), 2 * np.pi) / (np.pi / 2)
    tt = np.where(tt >= 4, 0.0, tt)
    pix = np.zeros(z.shape, np.int64)
    eq = za <= 2 / 3
    t1 = n * (0.5 + tt[eq])
    t2 = n * z[eq] * 0.75
    jp = np.floor(t1 - t2).astype(np.int64)
    jm = np.floor(t1 + t2).astype(np.int64)
    ir = n + 1 + jp - jm
    ks = 1 - (ir & 1)
    ip = np.mod((jp + jm - n + ks + 1) // 2, 4 * n)
    pix[eq] = 2 * n * (n - 1) + (ir - 1) * 4 * n + ip
    c = ~eq
    tp = tt[c] - np.floor(tt[c])
    tmp = n * np.sqrt(3 * (1 - za[c]))
    jp = np.floor(tp * tmp).astype(np.int64)
    jm = np.floor((1 - tp) * tmp).astype(np.int64)
    ir = jp + jm + 1
    ip = np.mod(np.floor(tt[c] * ir).astype(np.int64), 4 * ir)
    pix[c] = np.where(z[c] > 0, 2 * ir * (ir - 1) + ip, 12 * n * n - 2 * ir * (ir + 1) + ip)
    return pix


def pix2ang(n: int, pix) -> tuple[np.ndarray, np.ndarray]:
    """Centre (lat, lon in -180..180 degrees) of each cell."""
    pix = np.atleast_1d(np.asarray(pix, np.int64))
    ncap, npix = 2 * n * (n - 1), 12 * n * n
    z, phi = np.zeros(pix.shape), np.zeros(pix.shape)
    a = pix < ncap
    ir = (1 + _isqrt(1 + 2 * pix[a])) >> 1
    iphi = pix[a] + 1 - 2 * ir * (ir - 1)
    z[a] = 1 - ir ** 2 / (3 * n * n)
    phi[a] = (iphi - 0.5) * np.pi / (2 * ir)
    b = (pix >= ncap) & (pix < npix - ncap)
    ip = pix[b] - ncap
    ir = ip // (4 * n) + n
    iphi = ip % (4 * n) + 1
    fodd = np.where((ir + n) & 1, 1.0, 0.5)
    z[b] = (2 * n - ir) * 2 / (3 * n)
    phi[b] = (iphi - fodd) * np.pi / (2 * n)
    s = pix >= npix - ncap
    ip = npix - pix[s]
    ir = (1 + _isqrt(2 * ip - 1)) >> 1
    iphi = 4 * ir + 1 - (ip - 2 * ir * (ir - 1))
    z[s] = -1 + ir ** 2 / (3 * n * n)
    phi[s] = (iphi - 0.5) * np.pi / (2 * ir)
    lon = np.degrees(phi)
    return np.degrees(np.arcsin(np.clip(z, -1, 1))), np.where(lon > 180, lon - 360, lon)


def _ring2xyf(n: int, pix: np.ndarray):
    ncap, npix, nl2 = 2 * n * (n - 1), 12 * n * n, 2 * n
    iring, iphi, kshift, nr, face = (np.zeros(pix.shape, np.int64) for _ in range(5))
    a = pix < ncap
    r = (1 + _isqrt(1 + 2 * pix[a])) >> 1
    iring[a], iphi[a], nr[a] = r, pix[a] + 1 - 2 * r * (r - 1), r
    face[a] = (iphi[a] - 1) // r
    b = (pix >= ncap) & (pix < npix - ncap)
    ip = pix[b] - ncap
    tmp = ip // (4 * n)
    iring[b], iphi[b], nr[b] = tmp + n, ip - tmp * 4 * n + 1, n
    kshift[b] = (tmp + 2 * n) & 1
    ifm = (iphi[b] - ((tmp + 1) >> 1) + n - 1) // n
    ifp = (iphi[b] - ((nl2 + 1 - tmp) >> 1) + n - 1) // n
    face[b] = np.where(ifp == ifm, ifp | 4, np.where(ifp < ifm, ifp, ifm + 8))
    s = pix >= npix - ncap
    ip = npix - pix[s]
    r = (1 + _isqrt(2 * ip - 1)) >> 1
    iphi[s], nr[s], iring[s] = 4 * r + 1 - (ip - 2 * r * (r - 1)), r, 2 * nl2 - r
    face[s] = (iphi[s] - 1) // r + 8
    irt = iring - (2 + (face >> 2)) * n + 1
    ipt = 2 * iphi - _JPLL[face] * nr - kshift - 1
    ipt = np.where(ipt >= nl2, ipt - 8 * n, ipt)
    return (ipt - irt) >> 1, (-ipt - irt) >> 1, face


def _xyf2ring(n: int, ix: np.ndarray, iy: np.ndarray, face: np.ndarray) -> np.ndarray:
    nl4, ncap, npix = 4 * n, 2 * n * (n - 1), 12 * n * n
    jr = _JRLL[face] * n - ix - iy - 1
    north, south = jr < n, jr > 3 * n
    nr = np.where(north, jr, np.where(south, nl4 - jr, n))
    before = np.where(north, 2 * nr * (nr - 1), np.where(south, npix - 2 * (nr + 1) * nr, ncap + (jr - n) * nl4))
    kshift = np.where(north | south, 0, (jr - n) & 1)
    jp = (_JPLL[face] * nr + ix - iy + 1 + kshift) // 2
    jp = np.where(jp > nl4, jp - nl4, np.where(jp < 1, jp + nl4, jp))
    return before + jp - 1


def neighbours(n: int, pix) -> np.ndarray:
    """The 8 neighbours of each cell (SW, W, NW, N, NE, E, SE, S in the HEALPix order); -1 where a cell has 7."""
    pix = np.atleast_1d(np.asarray(pix, np.int64))
    ix, iy, face = _ring2xyf(n, pix)
    out = np.full((pix.size, 8), -1, np.int64)
    for m in range(8):
        x, y = ix + _XOFF[m], iy + _YOFF[m]
        nb = np.full(pix.size, 4)
        nb = np.where(x < 0, nb - 1, np.where(x >= n, nb + 1, nb))
        nb = np.where(y < 0, nb - 3, np.where(y >= n, nb + 3, nb))
        x = np.where(x < 0, x + n, np.where(x >= n, x - n, x))
        y = np.where(y < 0, y + n, np.where(y >= n, y - n, y))
        f = _FACES[nb, face]
        bits = _SWAP[nb, face >> 2]
        x = np.where(bits & 1, n - x - 1, x)
        y = np.where(bits & 2, n - y - 1, y)
        x, y = np.where(bits & 4, y, x), np.where(bits & 4, x, y)
        ok = f >= 0
        out[ok, m] = _xyf2ring(n, x[ok], y[ok], f[ok])
    return out
