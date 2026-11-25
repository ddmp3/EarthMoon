"""Mars geologic map (T48c, R5): the volcanic units of Tanaka et al. 2014 chosen from the map's own unit descriptions,
and the unit under a point. Synthetic shapefiles only."""
import numpy as np
import pytest

from discovery.mars_geology import UnitMap, edifice_units, lon180, volcanic_units

UNITS = {"AHv": "Amazonian and Hesperian volcanic", "lAvf": "Late Amazonian volcanic field unit",
         "Ave": "Amazonian volcanic edifice", "mNh": "Middle Noachian highland unit",
         "lHl": "Late Hesperian lowland unit", "Hpe": "Hesperian polar edifice unit"}


def test_volcanic_units_are_the_units_the_map_describes_as_volcanic():
    assert volcanic_units(UNITS) == {"AHv", "lAvf", "Ave"}


def test_edifices_are_the_volcanic_units_described_as_edifices():
    # the polar edifice unit is not volcanic: only volcanic edifices are taken out for the sensitivity test
    assert edifice_units(UNITS) == {"Ave"}


def test_longitudes_east_from_0_to_360_become_minus_180_to_180():
    assert lon180(np.array([0.0, 90.0, 180.0, 270.0, 359.5])).tolist() == [0.0, 90.0, -180.0, -90.0, -0.5]


def _shp(tmp_path):
    import shapefile
    w = shapefile.Writer(str(tmp_path / "geo"), shapeType=shapefile.POLYGON)
    w.field("Unit", "C", 10)
    w.field("UnitDesc", "C", 80)
    w.poly([[[-140, 10], [-140, 30], [-100, 30], [-100, 10], [-140, 10]]])     # a volcanic plain west of 0°
    w.record("AHv", UNITS["AHv"])
    w.poly([[[10, -20], [10, 0], [40, 0], [40, -20], [10, -20]]])
    w.record("mNh", UNITS["mNh"])
    w.close()
    return tmp_path / "geo"


def test_the_unit_under_each_point_is_read_from_the_polygons(tmp_path):
    m = UnitMap.read(_shp(tmp_path))
    lat = np.array([20.0, -10.0, 50.0])
    lon = np.array([240.0, 25.0, 0.0])                    # MOLA longitudes, 0 to 360° east
    assert m.unit_at(lat, lon).tolist() == ["AHv", "mNh", ""]
    assert m.descriptions == {"AHv": UNITS["AHv"], "mNh": UNITS["mNh"]}


def test_a_window_is_in_the_target_when_its_centre_is_in_a_selected_unit(tmp_path):
    m = UnitMap.read(_shp(tmp_path))
    sel = m.inside(np.array([20.0, -10.0]), np.array([240.0, 25.0]), volcanic_units(m.descriptions))
    assert sel.tolist() == [True, False]


@pytest.mark.parametrize("bad", [{"AHv": ""}, {}])
def test_no_unit_is_volcanic_without_a_description(bad):
    assert volcanic_units(bad) == set()
