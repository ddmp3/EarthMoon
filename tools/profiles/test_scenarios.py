"""Tests of the v3 scenarios (data/scenarios/*.yaml, task T24)."""
from pathlib import Path

import pytest
import yaml

from profiles import load_specs, validate_scenario

ROOT = Path(__file__).resolve().parents[2]
CTX = {
    "profiles": {"moon-psr", "mars-north-polar"},
    "parameters": {"slope_mean": ("keep", "topography"), "traversable_20": ("context", "topography"),
                   "latitude_abs": ("context", "operational")},
    "references": "| R43 | x |\nNTRS 20250011301",
    "experts": {"E1", "E2"},
}


def scenario(**over):
    s = {
        "id": "B", "name": "Robotics", "objective": "test rovers", "targets": ["moon-psr"],
        "similarity": [{"parameter": "slope_mean", "status": "available"}],
        "context": ["traversable_20"],
        "requirements": [
            {"id": "slope_limit", "what": "climbing limit", "value": "20 to 23°, max 25°", "source": "NTRS 20250011301"},
            {"id": "share", "what": "traversable share", "value": "half", "expert_decision": "E1"},
        ],
        "eliminating": ["slope_limit"],
        "cannot_assess": ["traction in 1/6 g"],
        "proxies": [],
    }
    s.update(over)
    return s


def test_a_complete_scenario_is_valid():
    assert validate_scenario(scenario(), CTX) == []


def test_unknown_target_profile():
    assert any("nowhere" in e for e in validate_scenario(scenario(targets=["nowhere"]), CTX))


def test_similarity_uses_only_kept_parameters_and_never_operational_ones():
    errs = validate_scenario(scenario(similarity=[{"parameter": "traversable_20", "status": "available"}]), CTX)
    assert any("kept" in e for e in errs)


def test_a_requirement_needs_a_checked_source_or_an_expert_label():
    bad = scenario()
    bad["requirements"][0]["source"] = "R99"
    assert any("R99" in e for e in validate_scenario(bad, CTX))
    bad = scenario()
    del bad["requirements"][1]["expert_decision"]
    assert any("source or expert_decision" in e for e in validate_scenario(bad, CTX))
    bad = scenario()
    bad["requirements"][1]["expert_decision"] = "E77"
    assert any("E77" in e for e in validate_scenario(bad, CTX))


def test_eliminating_constraints_point_to_requirements():
    assert any("ghost" in e for e in validate_scenario(scenario(eliminating=["ghost"]), CTX))


def test_proxy_must_say_what_it_stands_for():
    errs = validate_scenario(scenario(proxies=[{"name": "permafrost"}]), CTX)
    assert any("stands_for" in e for e in errs)


def test_instruments_are_checked_like_scenarios():
    s = scenario(instruments=[{"id": "radar", "name": "GPR", "objective": "o", "targets": ["moon-psr"],
                               "similarity": [], "requirements": [], "eliminating": [], "cannot_assess": ["x"],
                               "proxies": [], "context": []}])
    assert validate_scenario(s, CTX) == []
    s["instruments"][0]["targets"] = ["bad"]
    assert any("bad" in e for e in validate_scenario(s, CTX))


# Repository -------------------------------------------------------------------------------------------------

def repo_ctx():
    params = yaml.safe_load((ROOT / "data" / "parameters.yaml").read_text(encoding="utf-8"))["parameters"]
    limits = (ROOT / "docs" / "LIMITS.md").read_text(encoding="utf-8")
    import re
    return {"profiles": {s["id"] for s in load_specs(ROOT / "data" / "profiles" / "spec")},
            "parameters": {p["id"]: (p["decision"], p["dimension"]) for p in params},
            "references": (ROOT / "docs" / "REFERENCES.md").read_text(encoding="utf-8"),
            "experts": set(re.findall(r"^\| (E\d+) \|", limits, re.M))}


SCEN = sorted((ROOT / "data" / "scenarios").glob("*.yaml"))


@pytest.mark.parametrize("path", SCEN, ids=lambda p: p.stem)
def test_repository_scenarios_are_valid(path):
    assert validate_scenario(yaml.safe_load(path.read_text(encoding="utf-8")), repo_ctx()) == []


def test_four_scenarios_and_mars_on_its_own_terms():
    ids = {yaml.safe_load(p.read_text(encoding="utf-8"))["id"] for p in SCEN}
    assert ids == {"A", "B", "C", "D"}
    d = yaml.safe_load((ROOT / "data" / "scenarios" / "D-mars.yaml").read_text(encoding="utf-8"))
    assert all(t.startswith("mars-") for t in d["targets"])
