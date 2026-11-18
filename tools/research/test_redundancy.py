"""Tests of the redundancy measurement (task T21). No network, no large file."""
import numpy as np
import pytest

from redundancy import (complete_rows, correlations, earth_sample, partial_correlations, random_points,
                        redundant_pairs)

KEYS = ["a", "b", "c"]


def rows(n=400, seed=1):
    rng = np.random.default_rng(seed)
    a = rng.normal(size=n)
    b = a * 2 + rng.normal(scale=0.1, size=n)      # nearly the same property as a
    c = rng.normal(size=n)                          # independent
    return [{"a": float(x), "b": float(y), "c": float(z)} for x, y, z in zip(a, b, c)]


def test_complete_rows_drop_missing_and_count_them():
    data = rows(10) + [{"a": None, "b": 1.0, "c": 2.0}]
    kept, dropped = complete_rows(data, KEYS)
    assert len(kept) == 10 and dropped == 1


def test_correlations_find_the_redundant_pair():
    out = correlations(rows(), KEYS)
    p, s = np.array(out["pearson"]), np.array(out["spearman"])
    assert out["n"] == 400
    assert p[0, 1] > 0.95 and s[0, 1] > 0.95
    assert abs(p[0, 2]) < 0.2 and np.allclose(np.diag(p), 1)


def test_spearman_is_rank_based():
    data = [{"a": float(x), "b": float(np.exp(x)), "c": float(-x)} for x in np.linspace(0, 5, 50)]
    out = correlations(data, KEYS)
    assert out["spearman"][0][1] == pytest.approx(1.0)
    assert out["pearson"][0][1] < 0.95


def test_partial_correlation_removes_a_shared_cause():
    rng = np.random.default_rng(3)
    z = rng.normal(size=2000)
    x = z + rng.normal(scale=0.3, size=2000)
    y = z + rng.normal(scale=0.3, size=2000)
    r = np.corrcoef([x, y, z])
    pc = partial_correlations(r)
    assert r[0, 1] > 0.8 and abs(pc[0][1]) < 0.1


def test_redundant_pairs_use_the_absolute_value():
    m = [[1, -0.9, 0.1], [-0.9, 1, 0.5], [0.1, 0.5, 1]]
    assert redundant_pairs(m, KEYS, 0.8) == [("a", "b", -0.9)]


def test_random_points_are_seeded_and_uniform_on_the_sphere():
    p1, p2 = random_points(7, 5000), random_points(7, 5000)
    assert p1 == p2
    lats = np.array([p[0] for p in p1])
    # uniform on the sphere: about half the area lies within 30 degrees of the equator
    assert 0.47 < np.mean(np.abs(lats) < 30) < 0.53


def test_earth_sample_counts_ocean_and_partial_windows():
    def reader(lat, lon, size):
        if lat < 0:
            raise LookupError("ocean")
        z = np.add.outer(np.arange(size), np.arange(size)) * 1.0
        if lon < 0:
            z[:, : size // 2] = np.nan       # half the window has no data
        return z
    pts = [(10, 10), (10, -10), (-10, 10)]
    out = earth_sample(pts, reader)
    assert out["attempted"] == 3 and out["no_tile"] == 1 and out["incomplete"] == 1
    assert len(out["rows"]) == 1 and out["rows"][0]["slope_mean"] > 0
