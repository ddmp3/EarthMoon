"""Tests of the v3 parameter catalogue (data/parameters.yaml, task T21)."""
import json
from pathlib import Path

import yaml

from profiles import DIMENSIONS, catalogue_ids, validate_parameters

ROOT = Path(__file__).resolve().parents[2]
IDS = {"earth": {"dem": "verified"}, "moon": {"lola": "verified"}, "mars": {"mola": "verified"}}


def param(**over):
    p = {"id": "slope_mean", "dimension": "topography", "definition": "mean pixel slope in a window", "unit": "°",
         "scale": "1 km window of 40 m pixels", "sources": {"earth": ["dem"], "moon": ["lola"], "mars": ["mola"]},
         "comparability": "direct", "decision": "keep", "reason": "primary slope statistic",
         "does_not_measure": "slopes below the pixel scale"}
    p.update(over)
    return p


def test_a_complete_parameter_is_valid():
    assert validate_parameters([param()], [], IDS, {}) == []


def test_comparability_and_decision_are_closed_lists():
    errs = validate_parameters([param(comparability="similar", decision="maybe")], [], IDS, {})
    assert any("comparability" in e for e in errs) and any("decision" in e for e in errs)


def test_unknown_source_is_reported():
    errs = validate_parameters([param(sources={"earth": ["nowhere"]})], [], IDS, {})
    assert any("nowhere" in e for e in errs)


def test_a_kept_redundant_pair_needs_a_justification():
    corr = {"Moon": {"keys": ["slope_mean", "slope_p95"], "spearman": [[1, 0.95], [0.95, 1]]}}
    params = [param(), param(id="slope_p95")]
    assert any("justification" in e for e in validate_parameters(params, [], IDS, corr))
    pairs = [{"pair": ["slope_mean", "slope_p95"], "justification": "different tails"}]
    assert validate_parameters(params, pairs, IDS, corr) == []


def test_a_dropped_parameter_does_not_need_a_pair_justification():
    corr = {"Moon": {"keys": ["slope_mean", "slope_p95"], "spearman": [[1, 0.95], [0.95, 1]]}}
    params = [param(), param(id="slope_p95", decision="drop")]
    assert validate_parameters(params, [], IDS, corr) == []


def test_repository_parameter_catalogue():
    data = yaml.safe_load((ROOT / "data" / "parameters.yaml").read_text(encoding="utf-8"))
    corr = json.loads((ROOT / "data" / "research" / "redundancy-t21.json").read_text(encoding="utf-8"))["matrices"]
    ids = catalogue_ids(ROOT / "data" / "catalog", bodies=("earth", "moon", "mars"))
    assert validate_parameters(data["parameters"], data.get("pairs", []), ids, corr) == []
    covered = {p["dimension"] for p in data["parameters"]}
    assert set(DIMENSIONS) <= covered
    assert data.get("not_comparable"), "list the properties that cannot be compared"
