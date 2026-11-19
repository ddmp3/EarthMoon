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
