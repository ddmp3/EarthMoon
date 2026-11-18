"""Tests of the planetary environment specs (data/profiles/spec/*.yaml, task T20)."""
import json
from pathlib import Path

import pytest

from profiles import catalogue_ids, load_specs, validate_rejected, validate_spec

ROOT = Path(__file__).resolve().parents[2]
SPEC_DIR = ROOT / "data" / "profiles" / "spec"
IDS = {"moon": {"lola-a": "verified", "illum": "verified", "crater-db": "not verified"}}


def spec(**over):
    s = {
        "id": "moon-test", "body": "moon", "name": "Test environment", "kind": "distribution",
        "status": "ready", "catalogue_environments": ["psr"],
        "selection": {
            "rule": "1 km windows south of 85S whose shadow fraction is at least f",
            "steps": [{"product": "lola-a", "condition": "window inside the grid"},
                      {"product": "illum", "condition": "shadow fraction >= f"}],
            "parameters": [{"name": "f", "value": "to fix in T22", "sensitivity": [0.25, 0.5, 0.75]}],
        },
        "parameters": [{"dimension": "topography", "names": ["slope_mean"], "product": "lola-a",
                        "scale": "1 km windows of 40 m pixels", "effective_resolution": "not quantified (L3)"}],
        "statistics": {"percentiles": [5, 10, 25, 50, 75, 90, 95], "joint": "all window vectors kept"},
        "biases": ["interpolated between tracks"],
        "cannot_characterize": ["gravity"],
    }
    s.update(over)
    return s


def test_a_complete_spec_is_valid():
    assert validate_spec(spec(), IDS) == []


def test_missing_field_is_reported():
    s = spec()
    del s["biases"]
    assert any("biases" in e for e in validate_spec(s, IDS))


def test_unknown_product_is_reported():
    s = spec()
    s["selection"]["steps"][0]["product"] = "nowhere"
    assert any("nowhere" in e for e in validate_spec(s, IDS))


def test_ready_spec_cannot_select_with_an_unverified_product():
    s = spec()
    s["selection"]["steps"].append({"product": "crater-db", "condition": "age class"})
    assert any("not verified" in e for e in validate_spec(s, IDS))


def test_conditional_spec_names_what_blocks_it():
    s = spec(status="conditional")
    s["selection"]["steps"].append({"product": "crater-db", "condition": "age class"})
    assert any("blocked_by" in e for e in validate_spec(s, IDS))
    s["blocked_by"] = ["crater-db"]
    assert validate_spec(s, IDS) == []


def test_a_distribution_needs_more_than_a_median():
    s = spec(statistics={"percentiles": [50], "joint": "none"})
    assert any("percentiles" in e for e in validate_spec(s, IDS))


def test_selection_threshold_without_value_needs_a_sensitivity_grid():
    s = spec()
    s["selection"]["parameters"] = [{"name": "f", "value": "to fix in T22"}]
    assert any("sensitivity" in e for e in validate_spec(s, IDS))


def test_selection_must_not_use_a_compared_parameter():
    s = spec()
    s["selection"]["steps"][1]["uses"] = ["slope_mean"]
    assert any("circular" in e for e in validate_spec(s, IDS))


def test_rejected_entries_need_a_reason():
    assert validate_rejected([{"id": "moon-x", "body": "moon"}]) != []
    assert validate_rejected([{"id": "moon-x", "body": "moon", "reason": "no data"}]) == []


# Repository content ------------------------------------------------------------------------------------------

def repo():
    return load_specs(SPEC_DIR), catalogue_ids(ROOT / "data" / "catalog")


def test_repository_specs_are_valid():
    specs, ids = repo()
    errors = [e for s in specs for e in validate_spec(s, ids)]
    assert errors == []


def test_repository_rejected_list_is_valid():
    import yaml
    rejected = yaml.safe_load((SPEC_DIR / "rejected.yaml").read_text(encoding="utf-8"))["rejected"]
    assert validate_rejected(rejected) == []


def test_enough_environments_per_body():
    specs, _ = repo()
    ready = lambda body: [s for s in specs if s["body"] == body and s["status"] == "ready"]
    assert len(ready("moon")) >= 5 and len(ready("mars")) >= 4


def test_every_catalogue_environment_is_specified_or_rejected():
    import yaml
    specs, _ = repo()
    rejected = yaml.safe_load((SPEC_DIR / "rejected.yaml").read_text(encoding="utf-8"))["rejected"]
    covered = {(s["body"], env) for s in specs for env in s["catalogue_environments"]}
    covered |= {(r["body"], env) for r in rejected for env in r.get("catalogue_environments", [])}
    for body, envs in (("moon", ["polar-highlands", "psr", "persistently-lit", "mare-plains", "pits-tubes",
                                  "fresh-craters", "degraded-highlands"]),
                       ("mars", ["volcanic-plains", "ancient-aqueous", "ice-rich-midlatitudes", "polar-deposits",
                                  "dune-fields", "sedimentary-basins", "caves"])):
        for env in envs:
            assert (body, env) in covered, f"{body}/{env} neither specified nor rejected"


def test_v2_south_polar_reference_is_the_regression_anchor():
    specs, _ = repo()
    anchor = next(s for s in specs if s["id"] == "moon-south-polar-cap-v2")
    v2 = json.loads((ROOT / "data" / "reference" / "moon-south-pole.json").read_text(encoding="utf-8"))["terrain_v2"]
    assert anchor["regression"]["file_sha256"] == v2["file_sha256"]
    assert anchor["regression"]["windows"] == v2["windows"]
    assert set(anchor["parameters"][0]["names"]) == set(v2["params"])


@pytest.mark.parametrize("path", sorted(SPEC_DIR.glob("*.yaml")))
def test_spec_file_name_matches_id(path):
    if path.name == "rejected.yaml":
        return
    import yaml
    assert yaml.safe_load(path.read_text(encoding="utf-8"))["id"] == path.stem
