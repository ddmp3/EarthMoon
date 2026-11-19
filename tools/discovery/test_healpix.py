"""HEALPix RING grid of protocol v3 (T43b): checked against its own definition, no external library."""
import numpy as np
import pytest

from discovery.healpix import NSIDE, ang2pix, cell_area_km2, neighbours, pix2ang

rng = np.random.default_rng(3)


@pytest.mark.parametrize("n", [1, 2, 4, 5, 7])
def test_every_pixel_centre_falls_in_its_own_pixel(n):
    p = np.arange(12 * n * n)
    assert (ang2pix(n, *pix2ang(n, p)) == p).all()


def test_pixels_have_equal_area():
    n = 4
    z = rng.uniform(-1, 1, 2_000_000)
    c = np.bincount(ang2pix(n, np.degrees(np.arcsin(z)), rng.uniform(-180, 180, z.size)), minlength=12 * n * n)
    e = z.size / (12 * n * n)                                              # about 10 400 points per pixel
    assert c.min() / e > 0.95 and c.max() / e < 1.05


def test_the_run_grid_has_cells_of_about_25_km2():
    assert cell_area_km2(NSIDE) == pytest.approx(25.04, abs=0.01)


@pytest.mark.parametrize("n", [5, 6])
def test_neighbours_are_symmetric_and_eight_except_at_the_24_corner_pixels(n):
    p = np.arange(12 * n * n)
    nb = neighbours(n, p)
    assert nb.shape == (p.size, 8)
    missing = (nb < 0).sum(1)
    assert set(missing.tolist()) <= {0, 1} and int(missing.sum()) == 24
    pairs = {(int(a), int(b)) for a, row in zip(p, nb) for b in row if b >= 0}
    assert all((b, a) in pairs for a, b in pairs)
    assert all(len(set(r[r >= 0].tolist())) == (r >= 0).sum() and a not in r for a, r in zip(p, nb))


@pytest.mark.parametrize("n", [5, 6])
def test_every_pixel_touching_another_on_a_fine_sample_is_its_neighbour(n):
    """Two adjacent points of a fine grid that fall in two pixels: those pixels touch, so they are neighbours."""
    lat = np.linspace(-89.95, 89.95, 1200)
    lon = np.linspace(-180, 179.9, 2400)
    la, lo = np.meshgrid(lat, lon, indexing="ij")
    pix = ang2pix(n, la.ravel(), lo.ravel()).reshape(la.shape)
    nb = neighbours(n, np.arange(12 * n * n))
    known = {(int(a), int(b)) for a in range(12 * n * n) for b in nb[a] if b >= 0}
    for a, b in ((pix[:, :-1], pix[:, 1:]), (pix[:-1, :], pix[1:, :]), (pix[:, -1], pix[:, 0])):
        d = a != b
        for x, y in set(zip(a[d].tolist(), b[d].tolist())):
            assert (x, y) in known, (x, y)


def test_run_grid_neighbours_are_close_on_the_ground():
    n = NSIDE
    p = rng.integers(0, 12 * n * n, 5000)
    nb = neighbours(n, p)
    la, lo = pix2ang(n, p)

    def xyz(a, b):
        a, b = np.radians(a), np.radians(b)
        return np.stack([np.cos(a) * np.cos(b), np.cos(a) * np.sin(b), np.sin(a)], -1) * 6371.0088
    ok = nb >= 0
    nla, nlo = pix2ang(n, np.where(ok, nb, 0).ravel())
    d = np.linalg.norm(xyz(nla, nlo).reshape(nb.shape + (3,)) - xyz(la, lo)[:, None, :], axis=-1)[ok]
    # 5 km cells: edges about 5 km, corners about 7 km; the stretched diamonds of the polar caps reach 10.4 km
    assert d.min() > 3.0 and d.max() < 11.0
