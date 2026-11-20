"""Geology dimension (T46): Earth map-unit lithology against lunar environments, by the crosswalk E17."""
import pytest

from discovery.geology import GROUPS, lith_names, unit_state


@pytest.mark.parametrize("text, names, major", [
    ("plutonic: anorthosite", ["plutonic", "anorthosite"], None),
    ("basalt, olivine basalt, tholeiite, alkali basalt", ["basalt"], None),
    ("Major:{sandstone}, Minor:{dolostone,shale}", ["sandstone", "dolostone", "shale"], ["sandstone"]),
    ("Major:{gneiss,metaanorthosite}", ["gneiss", "metaanorthosite"], ["gneiss", "metaanorthosite"]),
    ("gneiss, gabbroic, metagabbro, pyroxenite", ["gneiss", "gabbro", "metagabbro", "pyroxenite"], None),
    ("basaltic andesite", ["andesite"], None),
    ("plutonic: undivided granitic rocks", ["plutonic", "granite"], None),
    ("", [], None),
])
def test_lithology_names_are_read_from_the_map_text(text, names, major):
    found, maj = lith_names(text)
    assert found == names and maj == major


def test_a_known_anorthosite_body_is_a_match_for_the_highlands():
    assert unit_state("plutonic: anorthosite", "highland") == ("match", False)        # Lac-Saint-Jean, Marcy (1:5M)


def test_known_basalt_fields_are_a_match_for_the_maria():
    assert unit_state("basalt", "mare") == ("match", False)                           # Holuhraun (1:500k)
    assert unit_state("flood basalt(s); mafic volcanic rocks; basalt", "mare")[0] == "match"   # Deccan (world map)


def test_partial_matches_follow_the_crosswalk():
    assert unit_state("norite", "highland")[0] == "partial"
    assert unit_state("gneiss, gabbroic, metagabbro, pyroxenite", "highland")[0] == "partial"
    assert unit_state("diabase", "mare")[0] == "partial"
    assert unit_state("basalt", "pits")[0] == "partial"                               # no full match for pits
    assert unit_state("plutonic: anorthosite", "pits")[0] == "no match"


def test_an_unknown_or_generic_lithology_stays_unresolved_never_no_match():
    for text in ("", "intrusive igneous rocks", "volcanic: mafic rocks", "plutonic: undivided", "Quaternary"):
        for g in GROUPS:
            assert unit_state(text, g)[0] == "unresolved", (text, g)


def test_a_known_lithology_of_another_family_is_no_match():
    assert unit_state("sandstone, siltstone, shale", "highland")[0] == "no match"
    assert unit_state("plutonic: undivided granitic rocks", "mare")[0] == "no match"


def test_mixed_units_take_the_best_major_lithology_and_are_flagged():
    assert unit_state("sandstone, basalt", "mare") == ("match", True)
    assert unit_state("Major:{sandstone}, Minor:{basalt}", "mare") == ("no match", False)   # basalt only minor


def test_every_lunar_target_of_the_scenarios_has_a_group():
    from discovery.geology import TARGET_GROUP
    for t in ("moon-polar-lit-highlands", "moon-psr", "moon-south-polar-cap-v2", "moon-mare-plains", "moon-pits"):
        assert TARGET_GROUP[t] in GROUPS


def test_nine_sample_points_per_cell_stay_inside_the_5_km_cell():
    import numpy as np
    from discovery.geology import sample_points
    lat, lon = sample_points(np.array([46.0, -80.0]), np.array([10.0, 100.0]))
    assert lat.shape == (2, 9) and lon.shape == (2, 9)
    assert lat[0, 0] == 46.0 and lon[0, 0] == 10.0                                 # the centre first
    assert np.all(np.abs(lat[0] - 46.0) * 111.2 <= 1.7)
    assert np.all(np.abs(lon[0] - 10.0) * 111.2 * np.cos(np.radians(46.0)) <= 1.7)


def test_shares_of_a_cell_count_each_state_and_say_when_no_map_exists():
    from discovery.geology import cell_shares
    s = cell_shares(["match"] * 4 + ["partial"] * 2 + ["no match"] + [None] * 2)
    assert s == {"match": 4 / 9, "partial": 2 / 9, "no match": 1 / 9, "unresolved": 0.0, "no map": 2 / 9}


def test_a_tile_assigns_each_point_the_state_of_the_unit_that_holds_it():
    import math
    import mapbox_vector_tile
    from discovery.geology import classify_points
    z, x, y = 8, 0, 0
    n = 2 ** z
    def lonlat(px, py):                                     # tile pixel (extent 4096, y down) -> lon, lat
        lon = (x + px / 4096) / n * 360 - 180
        lat = math.degrees(math.atan(math.sinh(math.pi * (1 - 2 * (y + py / 4096) / n))))
        return lon, lat
    data = mapbox_vector_tile.encode([{"name": "units", "features": [
        {"geometry": "POLYGON ((0 0, 2048 0, 2048 4096, 0 4096, 0 0))", "properties": {"lith": "plutonic: anorthosite", "source_id": 7}},
        {"geometry": "POLYGON ((2048 0, 4096 0, 4096 4096, 2048 4096, 2048 0))", "properties": {"lith": "basalt", "source_id": 1080}},
    ]}], default_options={"y_coord_down": True})
    pts = [lonlat(1000, 2000), lonlat(3000, 2000)]
    out = classify_points(data, z, x, y, [p[1] for p in pts], [p[0] for p in pts])
    assert out["highland"] == ["match", "no match"] and out["mare"] == ["no match", "match"]
    assert out["source_id"] == [7, 1080]
    empty = classify_points(b"", z, x, y, [pts[0][1]], [pts[0][0]])
    assert empty["highland"] == [None] and empty["source_id"] == [None]
