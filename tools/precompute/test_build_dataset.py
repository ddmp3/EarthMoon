"""Tests of the dataset builder (pure functions, no network)."""
import pytest

from build_dataset import build, corrected_temperature, entry, lava_tube_level, site_values

SITE = {
    "id": "x", "lat": -20.0, "lon": 10.0,
    "precomputed": {"elevation": 3000.0, "ndvi": 0.05, "lst_day": 20.0, "lst_night": 1.0, "lst_amplitude": 19.0,
                    "modis_samples": {"lst": 12, "lst_valid_pairs": 12}},
    "terrain_v2": {"value": {"slope_mean": 6.0, "roughness_detrended": 8.0}, "sigma": {"slope_mean": 1.5}, "flags": []},
}
LIVE = {
    "power": {"cell_elevation_m": 1000.0, "values": {"T2M": {"ANN": 15.0}, "T2M_MIN": {"ANN": -2.0}, "T2M_MAX": {"ANN": 30.0},
                                                     "WS2M": {"ANN": 3.0}, "RH2M": {"ANN": 40.0}, "QV2M": {"ANN": 4.0},
                                                     "PRECTOTCORR": {"ANN": 0.2}, "ALLSKY_SFC_SW_DWN": {"ANN": None}}},
    "usgs": {"m2.5": 900, "m4.5": 16},
    "volcano": {"distance_km": 12.0, "major_rock_type": "Basalt / Picro-Basalt"},
}


def test_lapse_rate_correction_cools_a_site_above_its_grid_cell():
    value, sigma = corrected_temperature(15.0, 1000.0, 3000.0)
    assert value == pytest.approx(2.0)
    assert sigma == pytest.approx((1.5 ** 2 + 4.0 ** 2) ** 0.5, abs=0.01)
    assert corrected_temperature(15.0, 1000.0, 1000.0) == (15.0, 1.5)
    assert corrected_temperature(None, 0, 0) == (None, None)


def test_site_values_apply_the_documented_transformations():
    v = site_values(SITE, LIVE, {})
    assert v["t2m_mean"]["value"] == pytest.approx(2.0)
    assert "large_elevation_correction" in v["t2m_mean"]["flags"]
    assert v["specific_humidity"] == {"value": None, "sigma": None, "sigma_basis": None, "flags": ["not_representative_elevation"]}
    assert v["wind"]["value"] is None and v["precipitation"]["value"] is None
    mid = site_values({**SITE, "precomputed": {**SITE["precomputed"], "elevation": 1700.0}}, LIVE, {})
    assert mid["wind"]["value"] == 3.0 and "cell_elevation_mismatch" in mid["wind"]["flags"]
    near = site_values({**SITE, "precomputed": {**SITE["precomputed"], "elevation": 1200.0}}, LIVE, {})
    assert near["specific_humidity"]["value"] == 4.0 and near["specific_humidity"]["flags"] == []
    assert v["quake_m45_count"] == {"value": 16, "sigma": 4.0, "sigma_basis": "Poisson counting error", "flags": []}
    assert "incomplete_catalog" in v["quake_count"]["flags"]
    assert v["slope_mean"]["sigma"] == 1.5
    assert v["latitude_abs"]["value"] == 20.0


def test_missing_measurements_stay_missing():
    v = site_values(SITE, LIVE, {})
    assert v["solar"]["value"] is None and v["solar"]["sigma"] is None
    assert v["slope_p95"]["value"] is None
    nothing = site_values({"id": "y", "lat": 1.0, "lon": 1.0}, None, {})
    assert nothing["t2m_mean"]["value"] is None
    assert nothing["quake_m45_count"]["value"] is None
    assert nothing["lava_tube_evidence"]["value"] is None


def test_zero_earthquakes_is_a_measurement_not_a_gap():
    v = site_values(SITE, {**LIVE, "usgs": {"m2.5": 0, "m4.5": 0}}, {})
    assert v["quake_m45_count"]["value"] == 0
    assert v["quake_m45_count"]["sigma"] == 1.0


def test_lava_tube_levels_separate_presence_from_predisposition():
    basalt_near = {"distance_km": 5.0, "major_rock_type": "Basalt / Picro-Basalt"}
    assert lava_tube_level("a", basalt_near, {}) == (1, ["predisposition_only"])
    andesite = {"distance_km": 5.0, "major_rock_type": "Andesite / Basaltic Andesite"}
    assert lava_tube_level("a", andesite, {}) == (None, ["not_assessed"])
    far = {"distance_km": 80.0, "major_rock_type": "Basalt / Picro-Basalt"}
    assert lava_tube_level("a", far, {}) == (None, ["not_assessed"])
    assert lava_tube_level("a", None, {}) == (None, ["not_assessed"])
    assert lava_tube_level("a", None, {"a": {"level": 3}}) == (3, ["curated_reference"])


def test_no_temperature_correction_without_site_elevation():
    site = {**SITE, "precomputed": {}}
    v = site_values(site, LIVE, {})
    assert v["t2m_mean"]["value"] == 15.0
    assert v["t2m_mean"]["flags"] == ["no_elevation_correction"]


def test_seasonal_gaps_are_flagged():
    site = {**SITE, "precomputed": {**SITE["precomputed"], "modis_samples": {"lst": 12, "lst_valid_pairs": 9}}}
    assert site_values(site, LIVE, {})["lst_amplitude"]["flags"] == ["seasonal_gaps"]


def test_entry_rejects_non_numbers():
    assert entry("n/a", 1.0, "x")["value"] is None
    assert entry(float("nan"))["value"] is None
    assert entry(True)["value"] is None


def test_build_keeps_every_site_and_records_the_version():
    d = build([SITE], {"created_at": "t", "sources": {}, "sites": {"x": LIVE}}, {"sites": {}})
    assert d["version"] == "2.0.0" and list(d["sites"]) == ["x"]
    assert d["constants"]["lapse_rate_K_per_km"] == 6.5
