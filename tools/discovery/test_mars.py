"""Mars terrain windows (T48, decision E19): MOLA grids read from their PDS4 labels, square metric windows of 25
pixels, observed share from the shot counts. Synthetic grids only."""
import math

import numpy as np
import pytest

from discovery.mars import MARS_R_M, band_windows, observed_fraction, polar_latlon, read_pds4


def _write(tmp_path, arr: np.ndarray, name="megt00n000hb"):
    (tmp_path / f"{name}.img").write_bytes(arr.astype(">i2").tobytes())
    (tmp_path / f"{name}.xml").write_text(f"""<Product_Observational><File_Area_Observational>
<Array_2D_Image><offset unit="byte">0</offset><Element_Array><data_type>SignedMSB2</data_type><unit>meter</unit></Element_Array>
<Axis_Array><axis_name>Line</axis_name><elements>{arr.shape[0]}</elements></Axis_Array>
<Axis_Array><axis_name>Sample</axis_name><elements>{arr.shape[1]}</elements></Axis_Array></Array_2D_Image>
</File_Area_Observational></Product_Observational>""")
    return tmp_path / f"{name}.img"


def test_a_grid_is_read_with_the_shape_and_type_of_its_label(tmp_path):
    a = np.arange(12, dtype=np.int16).reshape(3, 4) - 5
    z = read_pds4(_write(tmp_path, a))
    assert z.shape == (3, 4) and z.dtype == np.int16 and (z == a).all()


def test_band_windows_are_square_in_metres_at_any_latitude():
    ppd = 128
    py = 2 * math.pi * MARS_R_M / 360 / ppd                            # about 463 m north-south
    lat0 = 60.0
    rows = 25
    lats = lat0 - (np.arange(rows) + 0.5) / ppd
    cols = 400
    x = np.arange(cols) * py * math.cos(math.radians(lat0))             # metres east, shrunk by cos(lat)
    z = np.tile(x * math.tan(math.radians(10.0)), (rows, 1))             # a plane rising 10° to the east
    w = band_windows(z, lats, ppd, window_px=25)
    assert w["slope_mean"].size >= 7                                     # 400 columns at cos 60° hold 8 square windows
    assert np.nanmedian(w["slope_mean"]) == pytest.approx(10.0, abs=0.3)
    assert w["width_m"] == pytest.approx(25 * py, rel=0.02)


def test_observed_fraction_counts_pixels_with_at_least_one_shot():
    counts = np.array([[0, 1], [2, 0]])
    assert observed_fraction(counts) == 0.5


def test_polar_grid_centre_is_the_pole_and_latitude_falls_outwards():
    lat, lon = polar_latlon(np.array([500.0, 500.0, 0.0]), np.array([500.0, 1000.0, 500.0]), size=1001, pixel_m=115.8, north=True)
    assert lat[0] == pytest.approx(90.0, abs=0.01)
    assert lat[1] < lat[0] and lat[2] < lat[0]
    assert lat[1] == pytest.approx(lat[2], abs=1e-6)                    # same distance from the pole


def test_swim_coordinates_follow_its_grid_centred_on_180():
    from discovery.mars import swim_xy
    x, y = swim_xy(np.array([0.0, 30.0]), np.array([180.0, 0.0]))
    assert x[0] == pytest.approx(0.0) and y[0] == pytest.approx(0.0)
    assert x[1] == pytest.approx(-MARS_R_M * math.pi) and y[1] == pytest.approx(MARS_R_M * math.pi / 6)


def test_a_grid_with_scaling_in_its_label_is_converted_to_metres(tmp_path):
    raw = np.array([[32000, 32004]], dtype=np.uint16)
    (tmp_path / "megt_n_512_1.img").write_bytes(raw.astype(">u2").tobytes())
    (tmp_path / "megt_n_512_1.xml").write_text("""<Array_2D_Image><offset unit="byte">0</offset><Element_Array>
<data_type>UnsignedMSB2</data_type><unit>meter</unit><scaling_factor>0.25</scaling_factor><value_offset>-8000</value_offset>
</Element_Array><Axis_Array><elements>1</elements></Axis_Array><Axis_Array><elements>2</elements></Axis_Array></Array_2D_Image>""")
    z = read_pds4(tmp_path / "megt_n_512_1.img")
    assert z.tolist() == [[0.0, 1.0]]


def test_volcanic_plains_keep_observed_windows_inside_volcanic_units_and_report_edifices_apart():
    from discovery.mars import volcanic_selection
    units = np.array(["AHv", "Ave", "mNh", "AHv", ""], dtype=object)
    observed = np.array([0.9, 0.8, 0.9, 0.2, 0.9])
    sel, sens = volcanic_selection(units, observed, volcanic={"AHv", "Ave"}, edifices={"Ave"})
    assert sel.tolist() == [True, True, False, False, False]          # the last AHv window is mostly interpolated
    assert sens == {"all_volcanic_units": 2, "without_edifices": 1, "any_observed_share": 3}
