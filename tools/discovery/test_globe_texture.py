"""Mars globe texture (T45c part 2): shading of a synthetic elevation grid."""
import numpy as np

from discovery.globe_texture import shade


def test_shade_gives_rgb_bytes_and_lighter_colours_higher_up():
    z = np.tile(np.linspace(-5000, 5000, 64), (32, 1))
    rgb = shade(z, 360 / 2048)
    assert rgb.shape == (32, 64, 3) and rgb.dtype == np.uint8
    assert rgb[:, -5].mean() > rgb[:, 5].mean()


def test_missing_elevation_does_not_break_the_texture():
    z = np.zeros((8, 8))
    z[2, 2] = np.nan
    assert np.isfinite(shade(z, 1.0).astype(float)).all()
