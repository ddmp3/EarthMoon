"""Lunar tile grid and SLDEM2015 reader (T41). Synthetic tiles only."""
import numpy as np
import pytest

from discovery.moon_grid import MOON_R, SldemIndex, moon_tile_grid, tile_file


def _write_tiles(folder, ppd):
    """Fake SLDEM tiles (float32 km) whose value encodes the pixel centre: lat * 1000 + lon (in metres after x1000)."""
    for lat0 in (-60, -30, 0, 30):
        for lon0 in range(0, 360, 45):
            rows, cols = 30 * ppd, 45 * ppd
            lat = lat0 + 30 - (np.arange(rows) + 0.5) / ppd
            lon = lon0 + (np.arange(cols) + 0.5) / ppd
            v = (lat[:, None] * 1000 + lon[None, :]) / 1000.0
            v.astype("<f4").tofile(folder / tile_file(lat0, lon0, ppd))


def test_tile_file_names_follow_the_archive():
    assert tile_file(0, 0, 512) == "SLDEM2015_512_00N_30N_000_045_FLOAT.IMG"
    assert tile_file(-60, 315, 512) == "SLDEM2015_512_60S_30S_315_360_FLOAT.IMG"
    assert tile_file(-30, 90, 512) == "SLDEM2015_512_30S_00S_090_135_FLOAT.IMG"   # as named in the archive


def test_reader_assembles_tiles_across_boundaries_and_the_360_meridian(tmp_path):
    _write_tiles(tmp_path, ppd=2)
    idx = SldemIndex(tmp_path, ppd=2)
    z, west, north = idx.read(lat_lo=-31.0, lat_hi=-29.0, lon_lo=-1.0, lon_hi=1.0)   # crosses 30°S and 0°/360°
    assert z.shape == (4, 4) and (west, north) == (-1.0, -29.0)
    assert z[0, 0] == pytest.approx(-29.25 * 1000 + 359.25, abs=1e-3)               # wrapped east longitude
    assert z[-1, -1] == pytest.approx(-30.75 * 1000 + 0.75, abs=1e-3)


def test_reader_refuses_latitudes_outside_the_product(tmp_path):
    _write_tiles(tmp_path, ppd=2)
    with pytest.raises(ValueError):
        SldemIndex(tmp_path, ppd=2).read(-61.0, -59.0, 10.0, 11.0)


def test_moon_tile_grid_uses_the_lunar_sphere_and_owns_each_window_once():
    g = moon_tile_grid(10, 20, 59.225, 1000.0)
    assert "+R=1737400" in g.crs and g.window_px == 17
    lat, lon = g.window_centres_latlon()
    own = g.owned()
    assert own.any() and np.all((lat[own] >= 10) & (lat[own] < 11) & (lon[own] >= 20) & (lon[own] < 21))
    area = own.sum() * (g.window_m / 1000) ** 2
    expected = (np.radians(1) * MOON_R / 1000) ** 2 * np.cos(np.radians(10.5))
    assert area == pytest.approx(expected, rel=0.05)
