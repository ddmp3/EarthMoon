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
