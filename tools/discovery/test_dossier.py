"""Zone dossiers (T43): hillshade and PNG writer. Synthetic data only."""
import struct
import zlib

import numpy as np

from discovery.dossier import hillshade, write_png


def test_hillshade_is_brighter_on_slopes_facing_the_light():
    x = np.tile(np.arange(50, dtype=float) * 10, (50, 1))         # rises to the east
    east, west = hillshade(x, 40.0, azimuth=90.0), hillshade(-x, 40.0, azimuth=90.0)
    assert east.dtype == np.uint8 and west[25, 25] > east[25, 25]
    flat = hillshade(np.zeros((10, 10)), 40.0)
    assert np.all(flat == flat[0, 0])


def test_png_writer_produces_a_valid_greyscale_png(tmp_path):
    img = (np.arange(12, dtype=np.uint8).reshape(3, 4) * 20)
    p = tmp_path / "a.png"
    write_png(p, img)
    b = p.read_bytes()
    assert b[:8] == b"\x89PNG\r\n\x1a\n"
    w, h = struct.unpack(">II", b[16:24])
    assert (w, h) == (4, 3)
    idat = b[b.index(b"IDAT") + 4: b.index(b"IEND") - 8]
    raw = zlib.decompress(idat)
    assert raw[0] == 0 and raw[1:5] == bytes(img[0])


def test_rgb_png_and_world_map_rasterise_cells_in_their_pixel(tmp_path):
    from discovery.dossier import world_map, write_png_rgb
    img = world_map(lat=np.array([0.05, 45.05]), lon=np.array([0.05, -90.05]), cls=np.array([2, 3]), deg=1.0)
    assert img.shape == (180, 360, 3)
    assert tuple(img[89, 180]) != tuple(img[0, 0])                       # the cell at 0°N 0°E is coloured
    p = tmp_path / "m.png"
    write_png_rgb(p, img)
    b = p.read_bytes()
    assert b[:8] == b"\x89PNG\r\n\x1a\n" and b[25] == 2                   # colour type 2: RGB
