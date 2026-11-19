"""Antarctic rock outcrop mask (T43, catalogue entry add-rock-outcrop-v7-3). Synthetic raster only."""
import numpy as np
from rasterio.transform import from_origin

from discovery.antarctic import outcrop_share, tiles_with_outcrops


def _raster():
    """A 3031 grid of 10 km pixels, 200 x 200, with one rock block around (lat -77.85, lon 166.67): McMurdo area."""
    from rasterio.warp import transform
    tf = from_origin(-1_000_000, 0, 10_000, 10_000)               # x -1000..1000 km, y 0..-2000 km
    r = np.zeros((200, 200), "uint8")
    x, y = transform("EPSG:4326", "EPSG:3031", [166.67], [-77.85])
    col, row = int((x[0] + 1_000_000) // 10_000), int(-y[0] // 10_000)
    r[row - 1:row + 2, col - 1:col + 2] = 1
    return r, tf


def test_outcrop_share_is_one_on_rock_zero_on_ice_and_nan_north_of_60():
    r, tf = _raster()
    s = outcrop_share(np.array([-77.85, -80.0, -50.0]), np.array([166.67, 0.0, 10.0]), r, tf, radius_m=0.0)
    assert s[0] == 1.0 and s[1] == 0.0 and np.isnan(s[2])


def test_tiles_with_outcrops_lists_the_one_degree_tiles_holding_rock():
    r, tf = _raster()
    tiles = tiles_with_outcrops(r, tf)
    assert "-78,166" in tiles and all(int(t.split(",")[0]) < -60 for t in tiles)
