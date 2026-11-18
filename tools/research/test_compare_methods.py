"""Analytic tests of the comparison candidates (task T23)."""
import numpy as np
import pytest

from compare_methods import (auc, energy_distance, interval_score, knn_typicality, ks_uniform, mahalanobis_typicality,
                             percentile_typicality, robust_location_scatter, wasserstein_1d)

rng = np.random.default_rng(0)
REF = rng.normal(10, 3, 20000)


def test_interval_score_matches_v2_shape():
    q = {"p5": 0, "p25": 2, "p75": 4, "p95": 6}
    assert list(interval_score(np.array([-1, 0, 1, 2, 3, 4, 5, 6, 7.0]), q)) == [0, 0, 0.5, 1, 1, 1, 0.5, 0, 0]


def test_percentile_typicality_is_one_at_the_median_and_uniform_on_the_reference():
    t = percentile_typicality(np.array([10.0]), REF)
    assert t[0] == pytest.approx(1, abs=0.01)
    held = rng.normal(10, 3, 5000)
    assert ks_uniform(percentile_typicality(held, REF)) < 0.03


def test_mahalanobis_typicality_is_calibrated_on_same_distribution():
    ref = rng.multivariate_normal([0, 0], [[1, 0.6], [0.6, 1]], 20000)
    held = rng.multivariate_normal([0, 0], [[1, 0.6], [0.6, 1]], 5000)
    loc, scat = robust_location_scatter(ref)
    assert np.allclose(loc, 0, atol=0.05)
    assert ks_uniform(mahalanobis_typicality(held, ref, loc, scat)) < 0.03
    far = mahalanobis_typicality(np.array([[6.0, -6.0]]), ref, loc, scat)
    assert far[0] < 0.001


def test_knn_typicality_is_calibrated_and_low_far_away():
    ref = rng.normal(size=(5000, 2))
    held = rng.normal(size=(4000, 2))
    t_held, t_far = knn_typicality(held[:2000], ref, held[2000:], k=10), knn_typicality(np.array([[8.0, 8.0]]), ref, held[2000:], k=10)
    assert ks_uniform(t_held) < 0.05 and t_far[0] < 0.001


def test_wasserstein_of_a_shift_is_the_shift():
    assert wasserstein_1d(REF, REF) == pytest.approx(0, abs=1e-9)
    assert wasserstein_1d(REF + 2.5, REF) == pytest.approx(2.5, abs=0.01)


def test_energy_distance_grows_with_the_shift():
    a = rng.normal(size=(400, 2))
    b = rng.normal(size=(400, 2))
    assert energy_distance(a, b) < energy_distance(a + 1, b) < energy_distance(a + 2, b)


def test_auc():
    assert auc(np.array([3, 4, 5.0]), np.array([0, 1, 2.0])) == 1.0
    assert auc(np.array([1, 2.0]), np.array([1, 2.0])) == pytest.approx(0.5)
