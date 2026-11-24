"""Analog links and place names (T45c part 2): synthetic data only, no network."""
import numpy as np
import pytest

from discovery import analogs as an


FEATURES = [  # name, centre lat, centre lon (east, 0-360), diameter km, bbox (min_lat, max_lat, min_lon, max_lon)
    {"name": "Shackleton", "lat": -89.6, "lon": 129.8, "diameter": 21.0, "bbox": (-89.9, -89.3, 0.0, 360.0)},
    {"name": "Big Basin", "lat": -60.0, "lon": 20.0, "diameter": 900.0, "bbox": (-75.0, -45.0, 0.0, 40.0)},
    {"name": "Small Crater", "lat": -60.2, "lon": 20.1, "diameter": 10.0, "bbox": (-60.4, -60.0, 19.9, 20.3)},
]


def test_a_point_takes_the_smallest_named_feature_that_holds_it():
    names = an.PlanetNames(FEATURES, radius_km=1737.4)
    assert names.name(-60.2, 20.1) == "Small Crater"
    assert names.name(-55.0, 10.0) == "Big Basin"


def test_a_point_in_no_feature_says_how_far_the_nearest_one_is():
    names = an.PlanetNames(FEATURES, radius_km=1737.4)
    assert names.name(-89.0, 10.0).startswith("near Shackleton (")


def test_longitudes_west_are_read_as_east():
    names = an.PlanetNames(FEATURES, radius_km=1737.4)
    assert names.name(-60.2, 20.1 - 360) == "Small Crater"


def test_polar_stereographic_windows_are_placed_on_the_sphere():
    lat, lon = an.polar_latlon(np.array([0.0, 0.0]), np.array([0.0, 30000.0]), radius_m=1737400.0, south=True)
    assert lat[0] == pytest.approx(-90.0) and -90 < lat[1] < -88.9


def test_same_slope_windows_share_the_zone_percentile():
    ref = np.sort(np.linspace(0, 20, 2001))
    win = {"lat": np.arange(5.0), "lon": np.arange(5.0), "slope": np.array([1.0, 9.9, 10.0, 10.1, 19.0]),
           "name": ["a", "b", "c", "d", "e"]}
    out = an.same_slope(10.0, ref, win, band=0.025)
    assert out["percentile"] == pytest.approx(0.5, abs=0.001)
    assert [w["name"] for w in out["windows"]] == ["b", "c", "d"]
    assert out["rule"].startswith("windows whose slope percentile is within 2.5 points")


def test_a_planet_point_finds_the_earth_zones_of_the_same_percentile():
    ref = np.sort(np.linspace(0, 20, 2001))
    zones = [{"id": "z1", "slope_median": 10.05, "typicality": 0.9}, {"id": "z2", "slope_median": 2.0, "typicality": 0.95},
             {"id": "z3", "slope_median": 9.8, "typicality": 0.97}, {"id": "z4", "slope_median": None, "typicality": 0.99}]
    out = an.zones_like(10.0, ref, zones, band=0.025)
    assert [z["id"] for z in out] == ["z3", "z1"]                       # ranked by typicality, no slope means no match


def test_earth_place_label_is_short_and_in_the_order_locality_region_country():
    addr = {"village": "Itabirito", "state": "Minas Gerais", "country": "Brazil", "postcode": "35450"}
    assert an.place_label(addr) == "Itabirito, Minas Gerais, Brazil"
    assert an.place_label({"state": "Northern State", "country": "Sudan"}) == "Northern State, Sudan"
    assert an.place_label({}) is None


def test_geocoding_is_cached_and_never_repeats_a_query(tmp_path):
    calls = []

    def fetch(lat, lon, lang):
        calls.append((lat, lon, lang))
        return {"address": {"state": "S", "country": "C"}}

    cache = an.GeoCache(tmp_path / "geo.json", fetch, sleep=lambda: None)
    a = cache.label(10.004, 20.004, "en")
    b = cache.label(10.001, 20.002, "en")                               # same 0.01° key: no second request
    assert a == b == "S, C" and len(calls) == 1
    cache.save()
    again = an.GeoCache(tmp_path / "geo.json", fetch, sleep=lambda: None)
    assert again.label(10.0, 20.0, "en") == "S, C" and len(calls) == 1


def test_zone_slope_is_the_median_of_its_unmasked_windows():
    from discovery.discover import global_cell
    lat = np.array([10.01, 10.02, 10.03, 10.5])
    lon = np.array([20.01, 20.02, 20.03, 20.5])
    cells = global_cell(lat, lon)
    win = {"lat": lat, "lon": lon, "slope_mean": np.array([1.0, 3.0, 50.0, 9.0]),
           "hidden": np.array([0.0, 0.1, 0.9, 0.0])}                    # the third window is hidden ground
    zones = {"z": {"cells": [int(cells[0]), int(cells[1]), int(cells[2])], "tiles": ["10,20"]}}
    out = an.zone_slopes(zones, lambda tile: win)
    assert out == {"z": 2.0}


def test_a_zone_without_window_has_no_slope():
    out = an.zone_slopes({"z": {"cells": [1], "tiles": ["10,20"]}}, lambda tile: None)
    assert out == {"z": None}


def test_labels_keep_latin_script_parts_for_scientists():
    assert an.latin_label("Halfa - حلفا, Northern State, Sudan") == "Halfa, Northern State, Sudan"
    assert an.latin_label("Артёмовское городское поселение, Irkutsk Oblast, Russia") == "Irkutsk Oblast, Russia"
    assert an.latin_label("Boyacá, Manabí, Ecuador") == "Boyacá, Manabí, Ecuador"
    assert an.latin_label("東京, 日本") == "東京, 日本"                    # nothing Latin at all: kept as it is
    assert an.latin_label(None) is None
