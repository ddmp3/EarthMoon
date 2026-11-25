"""T53: known analog sites of the ESA/Open University catalogue, the literature criteria and our protocol."""
import math

import pytest

from discovery import known_analogs as ka


@pytest.mark.parametrize("text, lat, lon", [
    ("77°30'S 163°00'E", -77.5, 163.0),
    ("77.722053°S, 162.271861°E", -77.722053, 162.271861),
    ("24.062 S, 69.923 W.", -24.062, -69.923),
    ("Alice Springs is located at 23.7°S, 133.87°E", -23.7, 133.87),
    ("Gypsum Hill: 79.409175N, 90.732765W", 79.409175, -90.732765),
    ("25°47′10″S 31°3′11″E", -(25 + 47 / 60 + 10 / 3600), 31 + 3 / 60 + 11 / 3600),
    ("35° 42′ 0.0″ N, 111° 18′ 0.0″ W", 35.7, -111.3),
    ("35.3225°, -111.51806°", 35.3225, -111.51806),
    ("65° 11'58\"N, 124° 38'15\"W", 65 + 11 / 60 + 58 / 3600, -(124 + 38 / 60 + 15 / 3600)),
    ("75.21.5N 89.32.40W.", 75 + 21 / 60 + 5 / 3600, -(89 + 32 / 60 + 40 / 3600)),
    ("75.21.26.8 N 88.40.47.2 W", 75 + 21 / 60 + 26.8 / 3600, -(88 + 40 / 60 + 47.2 / 3600)),
    ("30.5°, -6.75°", 30.5, -6.75),
    ("7°4'21,7\"W; 30°59'37\"N", 30 + 59 / 60 + 37 / 3600, -(7 + 4 / 60 + 21.7 / 3600)),
    ("6°40’19,7”W; 30°47’60”N.", 30 + 48 / 60, -(6 + 40 / 60 + 19.7 / 3600)),
    ("N 55° 53' W 63° 18'", 55 + 53 / 60, -(63 + 18 / 60)),
    ("Huelva is located at 37°15′N 6°57′W", 37.25, -6.95),
    ("78°N 16°E", 78.0, 16.0),
    ("78° 16′ 22.8″ N, 15° 44′ 42″ E and ?", 78 + 16 / 60 + 22.8 / 3600, 15 + 44 / 60 + 42 / 3600),
    ("42.63°N, 89.86°E.", 42.63, 89.86),
])
def test_coordinates_are_read_as_the_catalogue_prints_them(text, lat, lon):
    la, lo = ka.parse_coord(text)
    assert la == pytest.approx(lat, abs=1e-6) and lo == pytest.approx(lon, abs=1e-6)


@pytest.mark.parametrize("text", ["20 °S to 30 °S", "Various", "Extending from lat. 51°N to lat. 61°N", ""])
def test_ranges_and_empty_fields_are_not_points(text):
    with pytest.raises(ka.NotAPoint):
        ka.parse_coord(text)


def test_every_frozen_catalogue_point_parses_and_lies_in_range():
    sites, excluded = ka.load_sites()
    assert len(sites) >= 60 and all(-90 <= s["lat"] <= 90 and -180 <= s["lon"] <= 180 for s in sites)
    names = {e["name"] for e in excluded}
    assert {"The Atacama Desert", "Columbia River Basalt Group", "Kamchatka", "The Namib Desert",
            "Impact Breccia Supersite", "Chocolate Pots"} <= names
    assert {s["chapter"] for s in sites} == set(range(1, 31)) - {8, 13, 19}
    bvc = next(s for s in sites if s["name"] == "Bockfjord Volcanic Complex")
    assert bvc["lat"] == pytest.approx(79 + 29 / 60 + 53 / 3600)              # the `fix` field is used


def test_the_directory_gives_the_chapters_of_a_feature():
    assert ka.chapters_of("moon", "anorthosite") == [17]
    assert ka.chapters_of("mars", "sulphate") == [2, 4, 9, 23, 26, 29]
    assert ka.chapters_of("mars", "present-day-aridity") == [1, 2, 11]          # from the literature, not the directory


def test_rock_rules_use_macrostrat_names_and_types():
    rules = ka.rock_rules()
    assert rules["basalt"] == {"basalt"}
    assert {"basalt", "tuff", "volcanic"} <= rules["volcanic"] and "granite" not in rules["volcanic"]
    assert {"limestone", "dolomite", "travertine"} <= rules["carbonate"]
    assert rules["sulphate"] == {"gypsum", "anhydrite"}


def test_a_rock_is_found_anywhere_in_a_unit_and_strict_when_listed_first():
    r = {"basalt"}
    assert ka.rock_state(["Major:{sandstone}, basalt"], r) == "found"
    assert ka.rock_state(["Major:{basalt}, sandstone", "shale"], r) == "strict"
    assert ka.rock_state(["tholeiitic basalt flows"], r) == "strict"              # alias of geology.py
    assert ka.rock_state(["sandstone", "shale", None], r) == "absent"
    assert ka.rock_state([None, None], r) == "unknown"                           # no map unit
    assert ka.rock_state(["volcanic rocks", "mafic"], r) == "unknown"            # generic classes only
    assert ka.rock_state(["volcanic rocks"], {"volcanic", "basalt"}) == "strict"  # 'volcanic' is a volcanic name


def test_a_feature_is_found_at_a_chapter_when_one_point_has_it():
    assert ka.chapter_state(["absent", "found", "unknown"]) == "found"
    assert ka.chapter_state(["absent", "strict"]) == "strict"
    assert ka.chapter_state(["absent", "unknown"]) == "absent"
    assert ka.chapter_state(["unknown", "unknown"]) == "unknown"


def test_context_rules_leave_missing_values_unknown():
    assert ka.ground_ice(0.7) == "strict" and ka.ground_ice(0.2) == "absent" and ka.ground_ice(None) == "unknown"
    assert ka.ground_ice(float("nan")) == "unknown"
    assert ka.arid(0.03) == "strict" and ka.arid(0.25) == "absent" and ka.arid(None) == "unknown"


def test_recovery_counts_chapters_with_data_and_needs_three():
    v = ka.recovery({1: "found", 2: "strict", 3: "absent", 4: "unknown"})
    assert v == {"with_data": 3, "found": 2, "share": pytest.approx(2 / 3), "verdict": "not recovered"}
    assert ka.recovery({1: "found", 2: "found", 3: "found", 4: "absent"})["verdict"] == "recovered"
    assert ka.recovery({1: "found", 2: "unknown"})["verdict"] == "not testable"


def test_false_alarms_and_base_rate_verdicts():
    assert ka.discrimination(false_alarms=1, base_rate=0.05) == "discriminating"
    assert ka.discrimination(false_alarms=2, base_rate=0.05) == "false alarms"
    assert ka.discrimination(false_alarms=0, base_rate=0.30) == "gate only"
    assert ka.discrimination(false_alarms=0, base_rate=None) == "base rate not computed"


def test_units_at_points_read_the_lithology_of_the_polygon_holding_each_point():
    import mapbox_vector_tile
    from discovery.geology import tile_xy
    lat, lon = 10.0, 20.0
    x, y, px, py = tile_xy([lat], [lon])
    sq = [(0, 0), (4096, 0), (4096, 4096), (0, 4096), (0, 0)]
    tile = mapbox_vector_tile.encode([{"name": "units", "features": [
        {"geometry": {"type": "Polygon", "coordinates": [sq]}, "properties": {"lith": "Major:{basalt}"}}]}],
        default_options={"y_coord_down": True})
    texts = ka.units_from_tile(tile, [lat], [lon])
    assert texts == ["Major:{basalt}"]
    assert ka.units_from_tile(b"", [lat], [lon]) == [None]
    assert int(x[0]) >= 0 and math.isfinite(px[0]) and math.isfinite(py[0])


def test_current_protocol_is_recognised_at_the_zone_threshold():
    assert ka.recognised(0.62) is True and ka.recognised(0.31) is False and ka.recognised(None) is None
