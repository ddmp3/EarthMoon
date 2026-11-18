import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
import score_sites as ss  # noqa: E402


def test_vegetation_factor_matches_the_api_rule():
    assert ss.vegetation_factor(None) == 1.0 and ss.vegetation_factor(0.2) == 1.0
    assert abs(ss.vegetation_factor(0.4) - 0.5) < 1e-12
    assert ss.vegetation_factor(0.6) == 0.0 and ss.vegetation_factor(0.85) == 0.0
    assert round(ss.vegetation_factor(0.325), 2) == 0.69


def test_analyze_degrades_moderate_vegetation_and_excludes_dense():
    crit = [{"param": "wind", "max": 3, "tolerance": 3, "weight": 1}]
    sites = [{"id": "bare", "values": {"wind": 1, "ndvi": 0.05}}, {"id": "sparse", "values": {"wind": 1, "ndvi": 0.4}},
             {"id": "dense", "values": {"wind": 1, "ndvi": 0.8}}]
    res = ss.analyze(sites, criteria=crit)
    by = {s["id"]: s for s in res["sites"]}
    assert by["bare"]["total"] == 100 and "vegetation_factor" not in by["bare"]
    assert by["sparse"]["total"] == 50 and by["sparse"]["vegetation_factor"] == 0.5
    assert [e["id"] for e in res["excluded"]] == ["dense"]
    off = ss.analyze(sites, criteria=crit, ndvi_filter=False)
    assert all(s["total"] == 100 for s in off["sites"])


SLOPE = {"param": "slope_mean", "min": 5, "max": 13, "tolerance": 8, "toleranceBelow": 2, "toleranceAbove": 8, "weight": 1}
DRY = {"param": "precipitation", "max": 1, "tolerance": 1, "weight": 1}
GATE = {"param": "traversable_15", "min": 0.5, "tolerance": 0.25, "weight": 1, "required": True}


def test_asymmetric_tolerance():
    assert abs(ss.criterion_score(4, SLOPE) - 0.5) < 1e-12
    assert ss.criterion_score(3, SLOPE) == 0
    assert abs(ss.criterion_score(17, SLOPE) - 0.5) < 1e-12


def test_missing_value_is_reported_not_scored():
    a = ss.assess({"slope_mean": 8}, [SLOPE, DRY])
    assert a["total"] == 100 and a["coverage"] == 0.5
    assert a["total_min"] == 50 and a["total_max"] == 100
    assert a["missing"] == ["precipitation"]


def test_measured_zero_is_not_missing():
    quakes = {"param": "quake_m45_count", "max": 5, "tolerance": 45, "weight": 1}
    assert ss.assess({"quake_m45_count": 0}, [quakes])["coverage"] == 1
    assert ss.assess({"quake_m45_count": None}, [quakes])["coverage"] == 0


def test_failed_requirement_ranks_after_passing_sites():
    sites = [{"id": "steep", "values": {"slope_mean": 8, "precipitation": 0, "traversable_15": 0.05}},
             {"id": "poor", "values": {"slope_mean": 30, "precipitation": 3, "traversable_15": 0.6}}]
    res = ss.analyze(sites, criteria=[SLOPE, DRY, GATE], ndvi_filter=False)
    assert [s["id"] for s in res["sites"]] == ["poor", "steep"]
    assert res["sites"][1]["requirements"] == "failed" and res["sites"][1]["total"] > res["sites"][0]["total"]
    assert ss.assess({"slope_mean": 8}, [SLOPE, GATE])["requirements"] == "unknown"


def test_rounding_matches_javascript():
    assert ss.js_round(0.5) == 1 and ss.js_round(1.5) == 2 and ss.js_round(2.5) == 3


def test_v2_scenarios_load_and_v1_is_kept_for_the_baseline():
    modes = ss.load_modes()
    assert set(modes) == {"robotics", "calibration", "colony"}
    used = {c["param"] for criteria in modes.values() for c in criteria}
    assert not used & {"volcano_distance", "quake_count", "humidity", "roughness", "slope_max", "solar"}
    assert any(c["param"] == "volcano_distance" for c in ss.MODES_V1["robotics"])


def test_expected_rankings_file_is_up_to_date():
    import json
    with open(ss.EXPECTED_FILE, encoding="utf-8") as fh:
        stored = json.load(fh)["modes"]
    assert stored == ss.expected_rankings(ss.dataset_sites(), ss.load_modes())
