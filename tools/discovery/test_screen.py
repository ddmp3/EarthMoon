"""Stage 1 screening (T43): which tiles are refined. Synthetic data only."""
import numpy as np

from discovery.screen import target_intervals, tile_passes


def test_target_intervals_are_the_lunar_iqr_widened_by_two_degrees_and_never_negative():
    profiles = {"a": {"metrics": {"slope_mean": {"p25": 1.88, "p75": 2.97}}},
                "b": {"metrics": {"slope_mean": {"p25": 5.2, "p75": 12.9}}}}
    out = target_intervals(profiles, ["a", "b"], widen=2.0)
    assert out == {"a": (0.0, 4.97), "b": (3.2, 14.9)}


def test_a_tile_passes_when_one_unmasked_window_falls_in_one_interval():
    iv = {"a": (3.0, 5.0)}
    slope = np.array([1.0, 4.0, 20.0])
    assert tile_passes(slope, np.array([False, False, False]), iv)
    assert not tile_passes(slope, np.array([False, True, False]), iv)      # the only match is masked
    assert not tile_passes(np.array([np.nan, 1.0]), np.zeros(2, bool), iv)  # missing never passes
