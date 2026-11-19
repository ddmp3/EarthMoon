"""Comparison engine (T42): typicality, cell summaries, requirements, suitability, Monte Carlo. Synthetic data."""
import numpy as np
import pytest

from discovery.compare import (cell_requirement, cell_similarity, interval_score, linear_suitability, monte_carlo,
                               percentile_typicality, window_requirement)

rng = np.random.default_rng(0)
REF = rng.normal(10, 3, 20000)


# --- moved from tools/research/test_compare_methods.py (T23) with their functions ---

def test_interval_score_matches_v2_shape():
    q = {"p5": 0, "p25": 2, "p75": 4, "p95": 6}
    assert list(interval_score(np.array([-1, 0, 1, 2, 3, 4, 5, 6, 7.0]), q)) == [0, 0, 0.5, 1, 1, 1, 0.5, 0, 0]


def test_percentile_typicality_is_one_at_the_median_and_uniform_on_the_reference():
    t = percentile_typicality(np.array([10.0]), REF)
    assert t[0] == pytest.approx(1, abs=0.01)
    held = percentile_typicality(rng.normal(10, 3, 5000), REF)
    counts, _ = np.histogram(held, bins=10, range=(0, 1))
    assert held.mean() == pytest.approx(0.5, abs=0.02) and counts.min() > 400       # flat: about 500 per bin


# --- engine ---

def test_missing_value_has_no_typicality_and_counts_neither_for_nor_against():
    t = percentile_typicality(np.array([10.0, np.nan]), REF)
    assert np.isfinite(t[0]) and np.isnan(t[1])


def test_cell_similarity_reports_the_distribution_of_its_valid_windows_only():
    typ = np.array([0.9, 0.7, 0.2, np.nan, np.nan, np.nan])
    cell = np.array([1, 1, 1, 2, 2, 3])
    typ[5] = 0.6
    out = cell_similarity(typ, cell)
    assert out[1] == {"windows": 3, "valid": 3, "median": 0.7, "share_above_half": pytest.approx(2 / 3), "p25": 0.45, "p75": 0.8}
    assert out[2]["valid"] == 0 and out[2]["median"] is None                         # missing, not zero
    assert out[3]["median"] == 0.6


def test_window_requirement_is_met_failed_or_unknown():
    s = window_requirement(np.array([0.9, 0.5, 0.2, np.nan]), at_least=0.5)
    assert s.tolist() == ["met", "met", "failed", "unknown"]
    assert window_requirement(np.array([4.0, 12.0]), at_most=10.0).tolist() == ["met", "failed"]


def test_cell_requirement_fails_when_fewer_than_half_its_valid_windows_meet_it():
    status = np.array(["met", "failed", "failed", "unknown", "met", "met", "unknown", "unknown"])
    cell = np.array([1, 1, 1, 1, 2, 2, 3, 3])
    out = cell_requirement(status, cell)
    assert out[1] == {"status": "failed", "met": 1, "failed": 2, "unknown": 1}
    assert out[2]["status"] == "met" and out[3]["status"] == "unknown"


def test_a_failed_requirement_never_offsets_and_is_never_offset_by_similarity():
    from discovery.compare import assess_cells
    windows = {"cell": np.array([1, 1, 2, 2]), "slope_mean": np.array([10.0, 10.0, 30.0, 30.0]),
               "traversable_20": np.array([0.1, 0.2, 0.9, 1.0])}
    refs = {"t": np.sort(REF)}
    out = assess_cells(windows, refs, requirements=[{"id": "r", "param": "traversable_20", "at_least": 0.5}],
                       suitability=None)
    c1, c2 = out[1], out[2]
    assert c1["similarity"]["t"]["median"] > 0.9 and c1["requirements"]["r"]["status"] == "failed"
    assert c2["similarity"]["t"]["median"] < 0.01 and c2["requirements"]["r"]["status"] == "met"
    assert "score" not in c1 and "overall" not in c1                                  # nothing mixes the outputs


def test_linear_suitability_is_one_below_good_zero_above_bad_and_unknown_when_missing():
    s = linear_suitability(np.array([3.0, 5.0, 7.5, 10.0, 12.0, np.nan]), good=5.0, bad=10.0)
    assert s[:5].tolist() == [1.0, 1.0, 0.5, 0.0, 0.0] and np.isnan(s[5])


def test_monte_carlo_is_reproducible_and_reports_rank_intervals():
    cells = np.repeat(np.arange(20), 25)
    slope = np.concatenate([rng.normal(8 + i * 0.3, 2, 25) for i in range(20)])
    windows = {"cell": cells, "slope_mean": slope}
    refs = {"t": np.sort(REF)}
    a = monte_carlo(windows, refs, "t", runs=30, seed=20261119, slope_sigma=0.5)
    b = monte_carlo(windows, refs, "t", runs=30, seed=20261119, slope_sigma=0.5)
    c = monte_carlo(windows, refs, "t", runs=30, seed=1, slope_sigma=0.5)
    assert a == b and a != c
    row = a[0]
    assert row["rank_p5"] <= row["rank_median"] <= row["rank_p95"] and 0 <= row["share_top_decile"] <= 1


def test_vectorised_cell_medians_equal_the_cell_summary_medians():
    from discovery.compare import cell_medians
    cell = rng.integers(0, 50, 2000)
    v = rng.normal(0, 1, 2000)
    v[rng.random(2000) < 0.2] = np.nan
    cell[:5] = 99                                                    # one cell with only NaN
    v[:5] = np.nan
    ids, med = cell_medians(v, cell)
    ref = cell_similarity(v, cell)
    for c, m in zip(ids, med):
        expect = ref[int(c)]["median"]
        assert (np.isnan(m) and expect is None) or m == pytest.approx(expect, abs=1e-6)


def test_window_masking_hides_covered_ground_and_keeps_unknown_masks_unknown():
    from discovery.compare import masked_windows
    w = {"wc_tree": np.array([0.6, 0.1, np.nan, 0.0]), "wc_built": np.array([0.0, 0.2, np.nan, 0.0]),
         "wc_water": np.array([0.0, 0.25, np.nan, 0.0]), "wc_snow_ice": np.array([0.0, 0.0, np.nan, 0.0]),
         "wc_covered": np.array([1.0, 1.0, 0.0, 1.0])}
    masked, unknown = masked_windows(w)
    assert masked.tolist() == [True, True, False, False] and unknown.tolist() == [False, False, True, False]


def test_confidence_needs_enough_valid_windows_and_little_hidden_or_unknown_ground():
    from discovery.compare_run import confidence
    assert confidence(valid=25, windows=25, masked=0, unknown_mask=0) == "high"
    assert confidence(valid=22, windows=25, masked=3, unknown_mask=0) == "medium"      # 12% masked
    assert confidence(valid=25, windows=25, masked=0, unknown_mask=25) == "medium"     # cover unknown
    assert confidence(valid=5, windows=25, masked=20, unknown_mask=0) == "low"


def test_b_suitability_rule_is_the_traversable_share_itself():
    from discovery.compare_run import SUITABILITY
    r = SUITABILITY["B"]
    assert linear_suitability(np.array([0.0, 0.3, 1.0]), r["good"], r["bad"]).tolist() == [0.0, 0.3, 1.0]


def test_cell_ids_may_be_text_as_in_the_cube():
    typ = np.array([0.9, 0.1, 0.5])
    cell = np.array(["tileA:1:2", "tileA:1:3", "tileA:1:2"])
    out = cell_similarity(typ, cell)
    assert out["tileA:1:2"]["median"] == 0.7 and out["tileA:1:3"]["valid"] == 1


def test_requirements_and_suitability_can_be_assessed_without_any_similarity_target():
    from discovery.compare import assess_cells
    w = {"cell": np.array(["a", "a", "b"]), "slope_mean": np.array([3.0, 4.0, 12.0])}
    out = assess_cells(w, {}, [{"id": "base", "param": "slope_mean", "at_most": 10.0}],
                       {"id": "s", "param": "slope_mean", "good": 5.0, "bad": 10.0})
    assert out["a"]["requirements"]["base"]["status"] == "met" and out["b"]["requirements"]["base"]["status"] == "failed"
    assert out["a"]["suitability"]["median"] == 1.0 and out["b"]["suitability"]["median"] == 0.0


CAP = __import__("pathlib").Path(__import__("os").environ.get("EARTHMOON_DATA", "/data")) / "profiles/moon/moon-south-polar-cap-v2.windows.parquet"


@pytest.mark.skipif(not CAP.exists(), reason="lunar windows not present (data folder)")
def test_planetary_self_consistency_on_held_out_lunar_blocks():
    """Lunar windows split by 5 km blocks (checkerboard): held-out windows scored against the other half."""
    import pyarrow.parquet as pq
    t = pq.read_table(CAP, columns=["x_m", "y_m", "slope_mean"])
    x, y, v = (t.column(k).to_numpy() for k in ("x_m", "y_m", "slope_mean"))
    held = ((np.floor(x / 5000) + np.floor(y / 5000)) % 2).astype(bool)
    typ = percentile_typicality(v[held], v[~held])
    counts, _ = np.histogram(typ, bins=10, range=(0, 1))
    assert typ.mean() == pytest.approx(0.5, abs=0.02)
    assert counts.min() / counts.max() > 0.8                   # close to uniform across the held-out blocks


def test_summary_ranks_high_confidence_cells_separately():
    from discovery.compare_run import summary
    cell = lambda m, conf: {"similarity": {"t": {"median": m}}, "requirements": {}, "confidence": conf}
    res = {"scenario": "B", "tiles": 1, "targets": {"t": {"comparable": True}}, "monte_carlo": {},
           "cells": {"a": cell(0.99, "low"), "b": cell(0.8, "high"), "c": cell(0.9, "medium"), "d": cell(0.7, "high")}}
    s = summary(res, top=2)
    assert [r["cell"] for r in s["top"]["t"]] == ["a", "c"]
    assert [r["cell"] for r in s["top_high_confidence"]["t"]] == ["b", "d"]
