"""Counted indicators of the v3 grid (T49): read from the run summaries and catalogues in the repository, never typed."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from science_grid import v3_indicators, v3_markdown  # noqa: E402


def test_v3_indicators_come_from_the_run_summaries():
    v = v3_indicators()
    assert v["runs"] == ["run-002", "run-mars-002"]
    assert v["masks"] == {"run-002": "17/18", "run-mars-002": "17/18"}
    assert v["negatives_top10"] == {"run-002": "7/7 targets", "run-mars-002": "4/4 targets"}
    assert v["self_consistency"]["run-002"] == "4/5 targets (fails: moon-pits 0.056)"
    assert v["positive_validation"] == "0 of 4 scenarios"
    assert v["dossiers"]["run-002"] == {"plausible": 4, "unknown": 36}
    assert v["cells"]["run-mars-002"] == 7400488
    assert v["dossiers"]["run-mars-002"] == {"unknown": 20}


def test_robustness_and_monte_carlo_are_reported_per_target():
    v = v3_indicators()
    assert v["monte_carlo"]["run-mars-002"]["D:mars-north-polar"] == "0/11847"
    assert v["monte_carlo"]["run-mars-002"]["D:mars-volcanic-plains"] == "1028/11235"
    assert v["nasadem"]["A"]["top_overlap"] == 0.35


def test_positive_controls_are_counted_with_their_result():
    """A target with positive controls counts for its scenario only when they pass; a failure is reported, never hidden."""
    v = v3_indicators()
    assert v["positive_controls"]["run-mars-002"] == {"D:mars-volcanic-plains": "median percentile 27.9 of 4 controls (fail)"}
    assert v["positive_validation"] == "0 of 4 scenarios"


def test_the_sources_of_the_releases_are_counted_from_the_catalogue():
    v = v3_indicators()
    s = v["sources"]
    assert s["used"] == 16 and s["with_refresh"] == 16 and s["watched"] == 11


def test_the_markdown_table_lists_every_counted_indicator():
    md = v3_markdown()
    assert md.startswith("| Indicator |") and "Masks check" in md and "17/18" in md
