"""T52 step 7 calibration helpers (pure parts; the run itself needs the Mars cube)."""
import numpy as np

from discovery import refresh_calibrate as cal


def test_the_sample_is_fixed_by_the_seed_and_sorted():
    keys = [f"{la},{lo}" for la in range(-5, 5) for lo in range(0, 10)]
    a, b = cal.sample(keys, 10, 20261119), cal.sample(list(reversed(keys)), 10, 20261119)
    assert a == b and len(a) == 10 and a == sorted(a) and set(a) <= set(keys)


def test_rings_add_existing_neighbours_only():
    have = {(0, 0), (0, 1), (1, 1), (2, 2), (5, 5)}
    assert cal.ring({(0, 0)}, have, 1) == {(0, 0), (0, 1), (1, 1)}
    assert cal.ring({(0, 0)}, have, 2) == {(0, 0), (0, 1), (1, 1), (2, 2)}


def test_change_shares_compare_the_same_cells():
    old = {"cell": np.array([1, 2, 3, 4]), "state": np.array(["evaluated", "evaluated", "hidden", "evaluated"], object),
           "candidate": np.array([True, False, False, True])}
    new = {"cell": np.array([4, 3, 2, 1]), "state": np.array(["evaluated", "hidden", "partial", "evaluated"], object),
           "candidate": np.array([False, False, False, True])}
    out = cal.change_shares(old, new)
    assert out == {"cells": 4, "state_changed": 0.25, "candidate_changed": 0.25}


def test_the_perturbation_stays_within_the_stated_accuracy_and_keeps_voids():
    z = np.full((200, 200), 100.0)
    z[0, 0] = np.nan
    p = cal.perturb(z, np.random.default_rng(1))
    assert np.isnan(p[0, 0]) and abs(np.nanstd(p - z) - cal.SIGMA_Z_M) < 0.05


def test_the_threshold_rule_was_fixed_before_measuring():
    assert cal.threshold({"a": 0.004, "b": 0.009}) == 0.01
    assert cal.threshold({"a": 0.004, "b": 0.023}) == 0.03
