"""Validation helpers of a global run (T43). Synthetic data only."""
import numpy as np
import pytest

from discovery.validate_run import block_split, in_top_decile, ks_uniform


def test_ks_distance_is_small_for_uniform_values_and_large_for_concentrated_ones():
    rng = np.random.default_rng(0)
    assert ks_uniform(rng.random(20000)) < 0.02
    assert ks_uniform(np.full(1000, 0.9)) > 0.8


def test_block_split_is_a_checkerboard_of_blocks():
    a = np.array([0.5, 1.5, 0.5, 1.5])
    b = np.array([0.5, 0.5, 1.5, 1.5])
    assert block_split(a, b, 1.0).tolist() == [False, True, True, False]


def test_a_masked_negative_never_counts_in_the_top_decile():
    vals = np.linspace(0, 1, 101)
    assert in_top_decile(0.95, 0.1, vals) and not in_top_decile(0.95, 0.6, vals)
    assert not in_top_decile(0.5, 0.0, vals) and not in_top_decile(np.nan, 0.0, vals)


def test_a_target_is_done_when_every_zone_file_has_its_monte_carlo_share(tmp_path):
    import json
    from discovery.validate_run import mc_done
    (tmp_path / "zones-A-moon-pits.json").write_text(json.dumps([{"mc_top_decile_share": 0.95}, {"mc_top_decile_share": 0.1}]))
    assert mc_done(tmp_path, "moon-pits") == {"A:moon-pits": {"zones": 2, "stable_zones_90pct": 1, "from_files": True}}
    (tmp_path / "zones-B-moon-psr.json").write_text(json.dumps([{"cells": 3}]))
    (tmp_path / "zones-A-moon-psr.json").write_text(json.dumps([{"mc_top_decile_share": 0.5}]))
    assert mc_done(tmp_path, "moon-psr") is None                         # B not done yet: rerun the target


def test_cell_rows_find_global_cells_and_report_missing_ones():
    from discovery.validate_run import cell_rows
    cells = {"cell": np.array(["30", "10", "20"])}
    assert cell_rows(np.array([10, 20, 25, 30]), cells).tolist() == [1, 2, -1, 0]


def test_monte_carlo_reads_the_window_slopes_written_by_the_assessment(tmp_path, monkeypatch):
    import json
    import discovery.discover as d
    import discovery.validate_run as v
    from discovery.test_discover import _cube
    _cube(tmp_path, ["10,19", "10,20"])
    d._CTX.clear()
    run = tmp_path / "run"
    (run / "cells-parts").mkdir(parents=True)
    refined = {"10,19": ["glo30-40m"], "10,20": ["glo30-40m"]}
    rows = []
    for key in d.assessed_keys(refined):
        d.assess_tile_to_file(key, str(tmp_path), str(tmp_path / "refs.npz"), str(tmp_path / "rock"),
                              str(run / "cells-parts"), {k: s for k, s in refined.items() if k in d.neighbour_keys(key)})
        rows += d.assess_tile(key, str(tmp_path), str(tmp_path / "refs.npz"), str(tmp_path / "rock"),
                              {k: s for k, s in refined.items() if k in d.neighbour_keys(key)})
    ids = [r["cell"] for r in rows]
    for sc in ("A", "B"):
        (run / f"zones-{sc}-moon-psr.json").write_text(json.dumps([{"cell_ids": ids[:3]}, {"cell_ids": ids[3:6]}]))
    monkeypatch.setattr(v, "RUNS", 10)
    out = v._mc_target(("moon-psr", 0, str(run), str(tmp_path / "refs.npz"), ids))
    assert out["A:moon-psr"]["zones"] == 2 and out["A:moon-psr"]["sample_cells"] == len(ids)
    shares = [z["mc_top_decile_share"] for z in json.loads((run / "zones-A-moon-psr.json").read_text())]
    assert all(0 <= s <= 1 for s in shares)


def test_positive_controls_pass_when_their_median_percentile_reaches_75():
    """Protocol section 2: median percentile of the control cells >= 75; the share in the top 10% is reported."""
    from discovery.validate_run import positive_summary
    out = positive_summary([95.0, 80.0, 70.0, 91.0])
    assert out == {"evaluated": 4, "median_percentile": 85.5, "top10_share": 0.5, "pass": True}
    assert positive_summary([95.0, 60.0, 70.0])["pass"] is False


def test_controls_without_a_value_are_not_counted_and_under_three_give_no_positive_validation():
    """Missing data is never a bad value: a control with no Earth value is left out, not ranked last."""
    from discovery.validate_run import positive_summary
    out = positive_summary([95.0, None, 99.0, float("nan")])
    assert out["evaluated"] == 2 and out["pass"] is None
    assert "fewer than 3" in out["note"]
