"""T54: multi-criteria selection (required gates, preferred criteria, equations) and its check on known sites."""
import math

import numpy as np
import pytest

from discovery import criteria as cr

NAN = float("nan")


def cols(**kw):
    """Release-like columns for 4 cells."""
    base = {"masked_share": [0.1, 0.9, 0.2, 0.0], "confidence": np.array(["high", "high", "low", "medium"]),
            "geo:mars-volcanic:match": [0.5, 0.0, 0.0, 0.0], "geo:mars-volcanic:partial": [0.2, 0.0, 0.0, 0.0],
            "geo:mars-volcanic:no_match": [0.3, 1.0, 0.0, 0.5], "geo:mars-volcanic:unresolved": [0.0, 0.0, 0.0, 0.5],
            "geo:mars-volcanic:no_map": [0.0, 0.0, 1.0, 0.0],
            "ctx:permafrost_prob": [0.8, NAN, 0.1, 0.6], "ctx:aridity_index": [0.1, 0.5, NAN, 0.02],
            "mars-volcanic-plains:median": [0.7, 0.2, NAN, 0.55],
            "req:climbing_limit_lrv": np.array(["met", "failed", "unknown", "met"])}
    base.update(kw)
    return {k: (v if isinstance(v, np.ndarray) else np.array(v, float)) for k, v in base.items()}


def get(c):
    return lambda name: c.get(name)


def test_variables_are_named_described_and_sourced():
    vs = {v["id"]: v for v in cr.variables("mars", ["mars-volcanic-plains"])}
    v = vs["volcanic_rock"]
    assert v["unit"] == "share" and "Macrostrat" in v["source"]["en"] and "Macrostrat" in v["source"]["fr"] and v["label"]["fr"] and v["label"]["en"]
    assert "relief_volcanic_plains" in vs and vs["relief_volcanic_plains"]["unit"] == "typicality"
    assert {"hidden_ground", "permafrost", "aridity", "confidence", "climb_lrv_ok"} <= set(vs)
    assert all(set(x) >= {"id", "label", "unit", "source", "scale", "help"} and x["help"]["fr"] for x in vs.values())


def test_rock_shares_count_only_mapped_and_resolved_samples_and_are_unknown_without_them():
    a = cr.values("volcanic_rock", get(cols()), "mars")
    assert a[0] == pytest.approx(0.7)                       # 0.5 + 0.2 of fully resolved samples
    assert a[1] == 0.0
    assert math.isnan(a[2])                                 # no map at all: unknown, never zero
    assert a[3] == 0.0                                      # half resolved, none volcanic


def test_flags_and_confidence_are_numbers_with_unknown_as_nan():
    c = get(cols())
    assert list(cr.values("climb_lrv_ok", c, "mars")[:2]) == [1.0, 0.0] and math.isnan(cr.values("climb_lrv_ok", c, "mars")[2])
    assert list(cr.values("confidence", c, "mars")) == [2.0, 2.0, 0.0, 1.0]


@pytest.mark.parametrize("text", [
    "volcanic_rock > 0", "permafrost >= 0.5 and hidden_ground <= 0.5", "not (aridity < 0.2)",
    "0.6 * relief_volcanic_plains + 0.4 * volcanic_rock >= 0.5", "max(permafrost, 1 - aridity) >= 0.5",
    "abs(relief_volcanic_plains - 0.5) < 0.2 or volcanic_rock == 0"])
def test_equations_parse(text):
    cr.parse(text, {"volcanic_rock", "permafrost", "hidden_ground", "aridity", "relief_volcanic_plains"})


@pytest.mark.parametrize("text, message", [
    ("volcanic_rock", "must be a condition"),
    ("foo > 1", "unknown variable 'foo'"),
    ("__import__('os') > 1", "unknown|unexpected"),
    ("volcanic_rock > ", "incomplete"),
    ("volcanic_rock >> 1", "unexpected"),
    ("1 ; 2", "unexpected"),
    ("x" * 600, "too long"),
])
def test_bad_equations_are_refused_with_a_readable_reason(text, message):
    with pytest.raises(cr.CriteriaError, match=message):
        cr.parse(text, {"volcanic_rock"})


def test_equations_use_three_valued_logic_missing_stays_unknown():
    c = get(cols())
    s = cr.condition("permafrost >= 0.5 and hidden_ground <= 0.5", c, "mars", ["mars-volcanic-plains"])
    assert s[0] == 1 and s[1] == 0 and s[2] == 0 and s[3] == 1      # cell 1: hidden 0.9 fails, so unknown ice is moot
    s = cr.condition("permafrost >= 0.5 or aridity < 0.2", c, "mars", ["mars-volcanic-plains"])
    assert s[0] == 1 and math.isnan(s[1]) and math.isnan(s[2])      # unknown or false stays unknown
    s = cr.condition("not (permafrost >= 0.5)", c, "mars", ["mars-volcanic-plains"])
    assert math.isnan(s[1])


def test_a_simple_criterion_is_a_readable_condition():
    crit = {"variable": "permafrost", "op": ">=", "value": 0.5, "role": "required"}
    assert cr.as_text(crit) == "permafrost >= 0.5"
    with pytest.raises(cr.CriteriaError, match="op"):
        cr.check_criterion({"variable": "permafrost", "op": "=>", "value": 0.5, "role": "required"}, {"permafrost"})
    with pytest.raises(cr.CriteriaError, match="role"):
        cr.check_criterion({"variable": "permafrost", "op": ">=", "value": 0.5, "role": "maybe"}, {"permafrost"})


def test_selection_keeps_cells_meeting_every_required_criterion_and_orders_by_preferred_met():
    rule = {"criteria": [
        {"variable": "volcanic_rock", "op": ">", "value": 0, "role": "required"},
        {"variable": "hidden_ground", "op": "<=", "value": 0.5, "role": "required"},
        {"variable": "aridity", "op": "<", "value": 0.2, "role": "preferred"},
        {"expression": "relief_volcanic_plains >= 0.5", "role": "preferred"}]}
    out = cr.select(get(cols(**{"geo:mars-volcanic:match": [0.5, 0.0, 0.0, 0.3]})), "mars", ["mars-volcanic-plains"], rule)
    assert out["state"].tolist() == ["candidate", "excluded", "to check", "candidate"]
    assert out["preferred_met"].tolist() == [2, 0, 0, 2]
    assert out["order"].tolist()[:2] == [0, 3]                     # both meet 2 preferred: higher confidence first
    assert out["counts"] == {"candidate": 2, "to check": 1, "excluded": 1}


def test_a_rule_needs_one_required_criterion_and_at_most_twelve():
    with pytest.raises(cr.CriteriaError, match="required"):
        cr.check_rule({"criteria": [{"variable": "aridity", "op": "<", "value": 0.2, "role": "preferred"}]}, {"aridity"})
    many = [{"variable": "aridity", "op": "<", "value": 0.2, "role": "required"}] * 13
    with pytest.raises(cr.CriteriaError, match="12"):
        cr.check_rule({"criteria": many}, {"aridity"})


def test_known_sites_are_recovered_per_chapter_and_negatives_counted():
    point_state = {("a", 1): "candidate", ("b", 1): "excluded", ("c", 2): "excluded", ("d", 3): "to check"}
    v = cr.site_check([{"name": n, "chapter": ch, "state": s} for (n, ch), s in point_state.items()],
                      negatives=["excluded", "candidate", "to check"], chapters=[1, 2, 3])
    assert v["recovered"] == 1 and v["with_data"] == 2 and v["unknown"] == 1 and v["false_alarms"] == 1
    assert v["chapters"][1]["state"] == "candidate" and v["chapters"][3]["state"] == "to check"


def test_presets_are_valid_and_every_criterion_says_why():
    ps = cr.presets()
    assert {"mars-volcanic-geology", "mars-ground-ice", "moon-rover-mobility", "moon-polar-ice"} <= {p["id"] for p in ps}
    for p in ps:
        names = {v["id"] for v in cr.variables(p["body"], p["targets"])}
        cr.check_rule(p, names)
        assert p["title"]["fr"] and p["title"]["en"] and p["use"]["fr"] and p["use"]["en"]
        for c in p["criteria"]:
            assert c["why"]["fr"] and c["why"]["en"] and c["source_text"]["fr"] and c["source_text"]["en"]
        assert p["known_sites"]["features"], p["id"]
