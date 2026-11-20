"""Static release export for API v3 (T44). Synthetic cells only, plus the repository catalogues and profiles."""
import numpy as np
import pytest

from discovery.release import (COVERAGE_CLASSES, coverage_class, coverage_shares, method, release_id, scenarios,
                               zone_id, zone_record)


def _cells():
    t = "moon-psr"
    return {
        "cell": np.array(["1", "2", "3", "4", "5", "6"]),
        "windows": np.array([25, 25, 25, 25, 25, 25], float),
        "valid_unmasked": np.array([25, 0, 5, 15, 22, 25], float),
        "masked_share": np.array([0.0, 0.8, 0.0, 0.0, 0.12, 0.0]),
        "cover_unknown": np.array([0, 0, 0, 0, 0, 25], float),
        "confidence": np.array(["high", "low", "low", "medium", "medium", "medium"], dtype=object),
        f"{t}:windows": np.array([25, 25, 25, 25, 25, 25], float),
        f"{t}:valid": np.array([25, 5, 5, 15, 22, 25], float),
        f"{t}:screened_out": np.array([None, None, None, None, None, None], dtype=object),
    }


def test_each_cell_gets_the_first_overlay_class_that_applies():
    assert coverage_class(_cells(), "moon-psr").tolist() == [
        "evaluated", "ground_hidden", "partial", "low_confidence", "low_confidence", "no_data"]


def test_a_cell_screened_out_for_a_target_is_screened_out_whatever_its_other_values():
    c = _cells()
    c["moon-psr:screened_out"] = np.array([True, None, None, None, None, None], dtype=object)
    c["moon-psr:windows"] = np.array([np.nan, 25, 25, 25, 25, 25])
    assert coverage_class(c, "moon-psr")[0] == "screened_out"


def test_shares_count_land_area_and_put_the_unrefined_land_in_screened_out():
    out = coverage_shares(_cells(), "moon-psr", land_km2=300.0)
    assert set(out["classes"]) == set(COVERAGE_CLASSES)
    assert out["classes"]["evaluated"]["km2"] == 25.0
    assert out["classes"]["screened_out"]["km2"] == 300.0 - 150.0
    assert sum(v["share"] for v in out["classes"].values()) == pytest.approx(1.0, abs=1e-3)   # shares rounded to 4 digits


def test_zone_ids_are_readable_and_parse_back():
    assert zone_id("A", "moon-psr", 0.5, 3, 12) == "A.moon-psr.t0.5.m3.12"


def test_zone_record_carries_spread_coverage_and_the_states_of_its_cells():
    cells = _cells()
    z = {"target": "moon-psr", "scenario": "A", "cells": 2, "area_km2": 50.1, "lat": 1.0, "lon": 2.0, "median": 0.8,
         "cell_median_p25": 0.7, "cell_median_p75": 0.9, "high_confidence_share": 1.0, "tiles": ["1,2"],
         "req:base_slope": {"met": 2, "failed": 0, "unknown": 0}, "suitability_median": 0.4,
         "mc_top_decile_share": 0.95, "cell_ids": ["1", "5"]}
    r = zone_record(z, rank=1, tau=0.5, min_cells=3, cells=cells)
    assert r["id"] == "A.moon-psr.t0.5.m3.1" and "cell_ids" not in r
    assert r["typicality"] == {"median": 0.8, "p25": 0.7, "p75": 0.9}
    assert r["coverage"] == {"windows": 50, "valid_unmasked": 47, "cover_unknown": 0,
                             "cells_by_confidence": {"high": 1, "medium": 1, "low": 0}}
    assert r["monte_carlo"] == {"top_decile_share": 0.95}
    z.pop("mc_top_decile_share")
    assert zone_record(z, 1, 0.5, 3, cells)["monte_carlo"] is None                  # not run: said, not zero


def test_release_id_depends_only_on_the_content():
    a = release_id({"run": "run-002", "x": [1, 2]})
    assert a == release_id({"x": [1, 2], "run": "run-002"}) and a != release_id({"run": "run-003"})
    assert a.startswith("r-") and len(a) == 10


def test_method_lists_catalogue_sources_with_status_and_flags_unknown_ones():
    m = method(["copernicus-dem-glo30", "lro-lola-ldem-85s-40m", "not-a-source"], steps=[{"step": "windows"}])
    by = {s["id"]: s for s in m["sources"]}
    assert by["copernicus-dem-glo30"]["status"] == "verified" and by["copernicus-dem-glo30"]["verified_on"]
    assert by["lro-lola-ldem-85s-40m"]["body"] == "moon"
    assert by["not-a-source"]["status"] == "not in catalogue"
    assert m["processing"] == [{"step": "windows"}]


def test_scenarios_name_their_targets_requirements_and_limits():
    s = {x["id"]: x for x in scenarios()}
    assert s["B"]["targets"] == ["moon-polar-lit-highlands", "moon-psr", "moon-mare-plains", "moon-south-polar-cap-v2"]
    assert any(r["id"] == "climbing_limit_lrv" and r["eliminating"] for r in s["B"]["requirements"])
    assert s["A"]["cannot_assess"] and "moon-persistently-lit" in s["A"]["not_comparable"]


def test_land_cells_are_the_global_cells_holding_a_90m_window(tmp_path):
    import pyarrow as pa
    import pyarrow.parquet as pq
    from discovery.healpix import NSIDE, ang2pix
    from discovery.release import land_cells, land_km2
    d = tmp_path / "glo90-90m"
    d.mkdir()
    a = {"lat": np.array([10.1, 10.11, 10.5]), "lon": np.array([20.1, 20.1, 20.9])}
    b = {"lat": np.array([-80.2]), "lon": np.array([5.0])}
    pq.write_table(pa.table(a), d / "A.windows.parquet")
    pq.write_table(pa.table(b), d / "B.windows.parquet")
    cells = land_cells(tmp_path, workers=1)
    expect = np.unique(ang2pix(NSIDE, np.r_[a["lat"], b["lat"]], np.r_[a["lon"], b["lon"]]))
    assert cells.tolist() == expect.tolist()
    assert land_km2(tmp_path) == 4.0


def test_status_says_not_validated_and_lists_the_checks_that_fail_or_cannot_run():
    from discovery.release import status
    val = {"positives": {"A": "none", "consequence": "no positive validation for scenarios A and B"},
           "negatives": {"top10": {"A:moon-psr": {"in_top10": 0, "pass": True}}, "masks": {"masked_or_flagged": 17, "of": 18, "pass": False}},
           "self_consistency": {"moon-psr": {"ks": 0.02, "pass": True}, "moon-pits": {"ks": 0.056, "pass": False}},
           "reproducibility": {"pass": True}}
    sources = [{"id": "copernicus-dem-glo30", "verified_on": "2026-11-18"}, {"id": "not-a-source", "status": "not in catalogue"}]
    s = status(val, sources, "r-12345678", "2026-11-19")
    assert s["validity"]["state"] == "not_validated" and s["validity"]["protocol"] == "validation-protocol-v3"
    checks = {c["check"]: c for c in s["validity"]["checks"]}
    assert checks["positives"]["pass"] is None and checks["masks"]["pass"] is False
    assert checks["negatives_top10"]["pass"] is True and checks["reproducibility"]["pass"] is True
    assert checks["self_consistency"]["pass"] is False and "moon-pits" in checks["self_consistency"]["detail"]
    fresh = {x["id"]: x for x in s["freshness"]["sources"]}
    assert s["freshness"]["refresher"] is False
    assert fresh["copernicus-dem-glo30"] == {"id": "copernicus-dem-glo30", "state": "not_checkable", "checked_on": "2026-11-18"}
    assert fresh["not-a-source"]["checked_on"] is None


def test_status_is_validated_only_when_every_check_passes():
    from discovery.release import status
    val = {"positives": {"pass": True}, "negatives": {"top10": {"x": {"pass": True}}, "masks": {"pass": True}},
           "self_consistency": {"t": {"pass": True}}, "reproducibility": {"pass": True}}
    assert status(val, [], "r-1", "2026-11-19")["validity"]["state"] == "validated"
    assert status({}, [], "r-1", "2026-11-19")["validity"]["state"] == "not_validated"
