import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
import rankings as rk  # noqa: E402


def site(i, role, total, excluded=None, missing=0):
    criteria = [{"verdict": "missing" if k < missing else "match"} for k in range(4)]
    s = {"id": i, "name": i.title(), "role": role, "total": total, "criteria": criteria}
    if excluded:
        s["excluded"] = excluded
    return s


def test_expected_by_mode():
    exp = rk.expected_by_mode([{"id": "a", "known_for": ["robotics", "colony"]}, {"id": "b", "known_for": []}, {"id": "c"}])
    assert exp["robotics"] == {"a"} and exp["colony"] == {"a"} and exp["calibration"] == set()


def test_check_mode_counts_only_expected_analogs():
    sites = [site("a", "validation", 90), site("c", "validation", 88), site("b", "candidate", 85),
             site("hot", "validation", 40, missing=2), site("neg", "negative", 0, excluded="vegetation")]
    s = rk.check_mode(sites, expected={"a", "c"})      # "hot" is not expected in this mode: no failure
    assert s["ranked"] == 4 and s["excluded"] == ["neg"] and s["negative_ok"]
    assert s["expected_met"] == ["a", "c"] and s["expected_missed"] == []
    assert s["top_candidates"][0] == ("b", "B", 85)
    assert s["top"][0] == (1, "a", "validation", 90, "-", "-") and s["penalized"] == []
    assert s["mean_coverage"] == 0.875


def test_check_mode_missed_and_negative_not_last():
    sites = [site("x", "candidate", 99), site("neg", "negative", 50), site("y", "candidate", 40), site("a", "validation", 10)]
    s = rk.check_mode(sites, expected={"a"})
    assert s["expected_missed"] == [("a", 4)] and not s["negative_ok"]


def test_overall_threshold():
    good = {"expected_met": ["a", "b", "c"], "expected_missed": [("d", 9)], "negative_ok": True}
    assert rk.overall({"m": good})["passes"]                          # 3/4 = 75 %
    bad = {"expected_met": ["a"], "expected_missed": [("d", 9)], "negative_ok": True}
    assert not rk.overall({"m": bad})["passes"]
    assert not rk.overall({"m": {**good, "negative_ok": False}})["passes"]


def test_chance_probability_exact():
    # one mode, 4 sites, top half = 2, one expected analog: P(met) = 2/4
    assert abs(rk.chance_probability([(4, 2, 1)], 1) - 0.5) < 1e-12
    # two expected analogs both in the top half of 4 sites: C(2,2)/C(4,2) = 1/6
    assert abs(rk.chance_probability([(4, 2, 2)], 2) - 1 / 6) < 1e-12
    # two independent modes, each 50%, both met: 25%
    assert abs(rk.chance_probability([(4, 2, 1), (4, 2, 1)], 2) - 0.25) < 1e-12
    assert rk.chance_probability([(4, 2, 1)], 0) == 1.0


def test_robustness_reports_fragile_expectations():
    r = {"m": {"ranked": 10, "half": 5, "negative_ok": True, "expected_met": ["a"], "expected_missed": [("b", 9)],
               "expected_shares": [("a", 0.9), ("b", 0.2)]}}
    rb = rk.robustness(r)
    assert abs(rb["mean_share"] - 0.55) < 1e-9 and rb["fragile"] == [("b", "m")]


def test_check_mode_reads_stability_and_vegetation():
    a = site("a", "validation", 90)
    a["stability"] = {"rankP10": 1, "rankP90": 3, "topHalfShare": 1.0}
    b = site("b", "candidate", 50)
    b["vegetationFactor"] = 0.69
    s = rk.check_mode([a, b], expected={"a"})
    assert s["top"][0][4] == "1-3" and s["expected_shares"] == [("a", 1.0)] and s["penalized"] == [("b", 0.69)]
