"""Refresher state and freshness file (T52 step 5, ADR-009 section 4)."""
import json

from discovery import refresher as rf
from discovery.watch import Response

T0, T1, T2 = "2026-11-23T10:00:00Z", "2026-11-30T10:00:00Z", "2026-12-07T10:00:00Z"


def result(state, signal=None, **kw):
    return {"state": state, "signal": signal, "checked_at": kw.pop("at", T0), "changed": [], "withdrawn": [],
            "added": [], "reason": None, **kw}


def test_first_check_records_the_baseline_without_claiming_up_to_date():
    e = rf.update_entry(None, result("baseline", {"a": {"etag": "1"}}))
    assert e["state"] == "first_check" and e["release_signal"] == {"a": {"etag": "1"}} and e["last_success"] == T0


def test_unchanged_is_up_to_date():
    e = rf.update_entry(rf.update_entry(None, result("baseline", {"a": 1})), result("unchanged", {"a": 1}, at=T1))
    assert e["state"] == "up_to_date" and e["last_success"] == T1


def test_a_change_stays_detected_until_a_release_uses_it():
    """The signal of the current release stays the comparison base: a later check does not hide the change."""
    e = rf.update_entry(None, result("baseline", {"a": 1}))
    e = rf.update_entry(e, result("changed", {"a": 2}, at=T1, changed=["a"]))
    assert e["state"] == "update_detected" and e["detected_on"] == T1 and e["release_signal"] == {"a": 1}
    e = rf.update_entry(e, result("changed", {"a": 2}, at=T2, changed=["a"]))
    assert e["detected_on"] == T1                                         # the first detection date is kept
    e = rf.consumed(e, {"a": 2})                                         # a published release used the new signal
    assert e["state"] == "up_to_date" and e["release_signal"] == {"a": 2} and e["detected_on"] is None


def test_a_failed_check_keeps_the_last_success_and_the_base():
    e = rf.update_entry(None, result("baseline", {"a": 1}))
    e = rf.update_entry(e, result("check_failed", reason="unreachable", at=T1))
    assert e["state"] == "check_failed" and e["last_success"] == T0 and e["release_signal"] == {"a": 1}
    assert e["reason"] == "unreachable"


def test_a_check_is_due_after_its_interval():
    e = rf.update_entry(None, result("baseline", {"a": 1}))
    assert rf.due(None, "weekly", T0) and not rf.due(e, "weekly", "2026-11-29T09:00:00Z")
    assert rf.due(e, "weekly", T1) and not rf.due(e, "none", T2)


def test_freshness_marks_sources_of_a_running_or_held_update():
    entries = {"a": rf.update_entry(rf.update_entry(None, result("baseline", {"x": 1})),
                                    result("changed", {"x": 2}, at=T1, changed=["x"])),
               "b": rf.update_entry(None, result("not_checkable", reason="no machine signal"))}
    doc = rf.freshness(entries, {"a": "weekly", "b": "none"}, progress={"sources": ["a"], "step": "assess",
                                                                         "done": 0.4}, held=[], now=T1)
    assert doc["refresher"] is True and doc["sources"]["a"]["state"] == "update_in_progress"
    assert doc["sources"]["a"]["interval_hours"] == 168 and doc["sources"]["b"]["interval_hours"] is None
    held = rf.freshness(entries, {"a": "weekly", "b": "none"}, progress=None,
                        held=[{"id": "r-x", "sources": ["a"], "reasons": ["3% of cells change"]}], now=T1)
    assert held["sources"]["a"]["state"] == "update_held" and held["held"][0]["id"] == "r-x"


def test_run_checks_only_due_sources_and_writes_the_file_atomically(tmp_path):
    catalog = [{"id": "a", "refresh": {"family": "api", "interval": "weekly",
                                       "watch": {"endpoint": "https://api.example.org/x", "path": "v"}}},
               {"id": "b", "refresh": {"family": "none", "interval": "none"}},
               {"id": "c"}]
    calls = []

    def fetch(url, method="GET"):
        calls.append(url)
        return Response(200, {}, json.dumps({"v": 1}).encode())

    store = tmp_path / "refresh.json"
    rf.run_checks(catalog, store, fetch, now=T0)
    rf.run_checks(catalog, store, fetch, now="2026-11-24T10:00:00Z")      # not due yet
    doc = json.loads(store.read_text())
    assert calls == ["https://api.example.org/x"]
    assert set(doc["entries"]) == {"a", "b"} and doc["entries"]["a"]["state"] == "first_check"
    assert doc["entries"]["b"]["state"] == "not_checkable"
    assert not list(tmp_path.glob("*.tmp"))


def test_the_refresher_refuses_a_folder_without_releases(tmp_path, capsys):
    """Started without EARTHMOON_DATA, the container mounts an empty folder: it says so and checks nothing."""
    assert rf.main(["check", "--state", str(tmp_path / "s.json"), "--releases", str(tmp_path / "releases")]) == 2
    assert "no releases" in capsys.readouterr().err and not (tmp_path / "s.json").exists()
