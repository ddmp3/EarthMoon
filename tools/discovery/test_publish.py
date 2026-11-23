"""Automatic publication of a refreshed release (T52 step 4, ADR-009 section 3)."""
import json
import os

import pytest

from discovery import publish as pub

OK = {"state": "validated", "checks": [{"check": "masks", "pass": True}]}
ANCHOR = {"pass": True, "detail": "71,731 windows"}


def change(share=0.0, appeared=0, disappeared=0):
    return {"cells_changed_share": share, "zones_appeared": appeared, "zones_disappeared": disappeared}


def test_a_validated_release_with_its_anchor_and_a_small_change_is_published():
    assert pub.gate(OK, ANCHOR, change(0.004)) == {"publish": True, "reasons": []}


@pytest.mark.parametrize("validity,anchor,ch,why", [
    ({"state": "not_validated", "checks": [{"check": "masks", "pass": False}, {"check": "positives", "pass": None}]},
     ANCHOR, change(), "not validated (failing: masks, positives)"),
    (OK, {"pass": False, "detail": "71,000 windows"}, change(), "regression anchor"),
    (OK, None, change(), "no regression anchor"),
    (OK, ANCHOR, change(0.03), "3.0% of evaluated cells change state"),
    (OK, ANCHOR, change(0.0, appeared=1), "1 zone appears"),
    (OK, ANCHOR, change(0.0, disappeared=2), "2 zones disappear"),
])
def test_each_hold_reason_is_stated(validity, anchor, ch, why):
    g = pub.gate(validity, anchor, ch)
    assert g["publish"] is False and any(why in r for r in g["reasons"])


def test_state_change_counts_cells_evaluated_in_either_release():
    old = {1: "evaluated", 2: "evaluated", 3: "low_confidence", 4: "evaluated"}
    new = {1: "evaluated", 2: "masked", 3: "low_confidence", 5: "evaluated"}
    # evaluated in either: 1, 2, 4, 5; changed: 2 (masked), 4 (gone), 5 (new)
    assert pub.state_change(old, new) == pytest.approx(3 / 4)
    assert pub.state_change({}, {}) == 0.0


def test_zones_are_identified_by_their_cells():
    old = [{"target": "t", "cell_ids": [1, 2, 3]}, {"target": "t", "cell_ids": [7, 8, 9]}]
    new = [{"target": "t", "cell_ids": [3, 2, 1]}, {"target": "t", "cell_ids": [7, 8]}]
    assert pub.zone_change(old, new) == (1, 1)


def test_lunar_anchor_is_the_v2_south_polar_window_count():
    profs = [{"id": "moon-south-polar-cap-v2", "windows": {"valid": 71731}}]
    assert pub.anchor(profs, "moon")["pass"] is True
    assert pub.anchor([{"id": "moon-south-polar-cap-v2", "windows": {"valid": 70000}}], "moon")["pass"] is False
    assert pub.anchor([], "moon")["pass"] is False
    assert pub.anchor([], "mars") is None                      # no anchor on Mars: every Mars release is held


def index(tmp_path, **extra):
    idx = {"current": "r-m1", "current_by_body": {"moon": "r-m1"},
           "releases": [{"id": "r-m1", "body": "moon"}], **extra}
    p = tmp_path / "index.json"
    p.write_text(json.dumps(idx))
    return p


def test_a_published_release_becomes_current_of_its_body(tmp_path):
    p = index(tmp_path)
    pub.register(p, {"id": "r-m2", "body": "moon"}, {"publish": True, "reasons": []})
    idx = json.loads(p.read_text())
    assert idx["current"] == "r-m2" and idx["current_by_body"]["moon"] == "r-m2"
    assert [r["id"] for r in idx["releases"]] == ["r-m2", "r-m1"]       # the previous one stays readable


def test_a_held_release_is_not_served_and_keeps_its_reasons(tmp_path):
    p = index(tmp_path)
    pub.register(p, {"id": "r-m2", "body": "moon"}, {"publish": False, "reasons": ["3.0% of evaluated cells change"]})
    idx = json.loads(p.read_text())
    assert idx["current"] == "r-m1" and [r["id"] for r in idx["releases"]] == ["r-m1"]
    assert idx["held"] == [{"id": "r-m2", "body": "moon", "reasons": ["3.0% of evaluated cells change"]}]


def test_approve_publishes_a_held_release_and_reject_removes_it(tmp_path):
    p = index(tmp_path)
    for rid in ("r-m2", "r-m3"):
        (tmp_path / rid).mkdir()
        pub.register(p, {"id": rid, "body": "moon"}, {"publish": False, "reasons": ["x"]})
    pub.approve(p, "r-m2")
    idx = json.loads(p.read_text())
    assert idx["current"] == "r-m2" and [h["id"] for h in idx["held"]] == ["r-m3"]
    pub.reject(p, "r-m3")
    idx = json.loads(p.read_text())
    assert idx["held"] == [] and not (tmp_path / "r-m3").exists() and (tmp_path / "r-m2").exists()
    with pytest.raises(pub.PublishError, match="not held"):
        pub.reject(p, "r-m1")                                   # never deletes a served release


def test_the_index_is_replaced_atomically(tmp_path, monkeypatch):
    p = index(tmp_path)
    calls = []
    real = os.replace
    monkeypatch.setattr(pub.os, "replace", lambda a, b: (calls.append((a, b)), real(a, b)))
    pub.register(p, {"id": "r-m2", "body": "moon"}, {"publish": True, "reasons": []})
    assert calls and str(calls[0][1]) == str(p) and not list(tmp_path.glob("*.tmp"))


def test_unchanged_files_are_shared_by_hash(tmp_path):
    old, new = tmp_path / "r-old", tmp_path / "r-new"
    for d, body in ((old, b"same"), (new, b"same")):
        (d / "layers").mkdir(parents=True)
        (d / "layers" / "a.png").write_bytes(body)
    (old / "b.json").write_bytes(b"old")
    (new / "b.json").write_bytes(b"new")
    shared = pub.share_unchanged(new, old)
    assert shared == 1 and (new / "b.json").read_bytes() == b"new"
    assert os.path.samefile(new / "layers" / "a.png", old / "layers" / "a.png")
