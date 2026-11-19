"""Raster map tiles of a release (T44, ADR-002). Synthetic cells only."""
import numpy as np
import pytest

from discovery.healpix import NSIDE, ang2pix, pix2ang
from discovery.tiles import (CLASS_CODE, PASTEL, cell_codes, pixel_cells, pixel_latlon, render_coverage, render_value,
                             tiles_with_cells)


def test_pixel_centres_follow_web_mercator():
    lat, lon = pixel_latlon(0, 0, 0)
    assert lat.shape == (256, 256)
    assert lon[0, 0] == pytest.approx(-180 + 360 / 512) and lon[0, -1] == pytest.approx(180 - 360 / 512)
    assert lat[0, 0] == pytest.approx(85.0, abs=0.2) and lat[127, 0] > 0 > lat[128, 0]
    lat1, lon1 = pixel_latlon(1, 1, 0)                                  # north-east quarter
    assert lon1.min() > 0 and lat1.min() > 0


def test_each_pixel_gets_the_cell_holding_its_centre():
    lat, lon = pixel_latlon(7, 75, 60)
    cells = pixel_cells(7, 75, 60)
    assert (cells == ang2pix(NSIDE, lat.ravel(), lon.ravel()).reshape(256, 256)).all()


def _one_tile_cells():
    """Every cell of tile 7/75/60 with one value and one class, in stripes."""
    ids = np.unique(pixel_cells(7, 75, 60))
    lat, _ = pix2ang(NSIDE, ids)
    order = np.argsort(lat)
    value = np.linspace(0, 1, ids.size)[np.argsort(order)]
    cls = np.array(list(CLASS_CODE))[np.arange(ids.size) % len(CLASS_CODE)]
    return ids, value, cls


def test_value_tiles_colour_evaluated_cells_and_never_colour_missing_or_hidden_ground():
    ids, value, cls = _one_tile_cells()
    cells = pixel_cells(7, 75, 60)
    img = render_value(cells, ids, value, cell_codes(cls), 7, 75, 60)
    assert img.shape == (256, 256, 4)
    k = np.searchsorted(ids, cells)
    c = cls[k]
    assert (img[c == "evaluated"][:, 3] == 255).all()                    # value colour, opaque
    hidden = img[c == "ground_hidden"]
    assert (hidden[:, 3] < 255).all()                                    # masked: outline only, never a value colour
    missing = img[(c == "screened_out") | (c == "no_data")]
    assert set(map(tuple, missing[:, :3][missing[:, 3] > 0].tolist())) <= {(128, 128, 128)}   # grey dots only


def test_pixels_outside_every_cell_of_the_run_are_transparent():
    ids, value, cls = _one_tile_cells()
    keep = ids[: ids.size // 2]
    img = render_value(pixel_cells(7, 75, 60), keep, value[: keep.size], cell_codes(cls[: keep.size]), 7, 75, 60)
    out = ~np.isin(pixel_cells(7, 75, 60), keep)
    assert (img[out][:, 3] == 0).all()


def test_coverage_overlay_is_transparent_on_evaluated_cells_and_patterned_elsewhere():
    ids, _, cls = _one_tile_cells()
    cells = pixel_cells(7, 75, 60)
    img = render_coverage(cells, ids, cell_codes(cls), 7, 75, 60)
    c = cls[np.searchsorted(ids, cells)]
    assert (img[c == "evaluated"][:, 3] == 0).all()
    for name in ("no_data", "ground_hidden", "partial"):
        part = img[c == name]
        drawn = part[part[:, 3] > 0]
        assert 0 < len(drawn) < len(part), name                              # hatching: some pixels, not a fill
        assert set(map(tuple, drawn[:, :3].tolist())) == {PASTEL}, name


def test_patterns_continue_across_tile_edges():
    """Hatching uses global pixel coordinates, so two neighbouring tiles join without a seam."""
    ids = np.unique(np.concatenate([pixel_cells(7, 75, 60), pixel_cells(7, 76, 60)]))
    codes = cell_codes(np.array(["no_data"] * ids.size))
    a = render_coverage(pixel_cells(7, 75, 60), ids, codes, 7, 75, 60)
    b = render_coverage(pixel_cells(7, 76, 60), ids, codes, 7, 76, 60)
    # the 45° hatching of a at its last column continues at the first column of b, one row higher
    assert (a[1:, 255, 3] > 0).tolist() == (b[:-1, 0, 3] > 0).tolist()


def test_only_tiles_holding_cells_are_rendered():
    lat, lon = np.array([10.0, -45.0]), np.array([20.0, 170.0])
    t = tiles_with_cells(ang2pix(NSIDE, lat, lon), zoom=3)
    assert t == {(3, 4, 3), (3, 7, 5)}
