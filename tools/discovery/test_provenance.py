"""Tile provenance and release changes for researchers (T52, David 23/11/2026)."""
import json

from discovery import provenance as pv

ITEM_A = "Copernicus_DSM_COG_30_N10_00_E020_00_DEM/Copernicus_DSM_COG_30_N10_00_E020_00_DEM.tif"
ITEM_B = "Copernicus_DSM_COG_30_N10_00_E021_00_DEM/Copernicus_DSM_COG_30_N10_00_E021_00_DEM.tif"


def rec(lat, lon, out="sha-w", computed_at=None, etag="e1"):
    r = {"tile": f"t{lat}{lon}", "lat": lat, "lon": lon, "code": "code-1", "commit": "abc",
         "inputs": {ITEM_A: {"etag": etag, "size": 10, "last_modified": "2022-05-09T14:10:02.000Z", "sha256": "s1"},
                    ITEM_B: {"etag": "e2", "size": 11, "last_modified": "2021-01-01T00:00:00.000Z"}},
         "outputs": {"windows": out, "cells": "sha-c"}}
    if computed_at:
        r["computed_at"] = computed_at
    return r


def manifest(tmp_path, scale, records):
    d = tmp_path / scale
    d.mkdir(parents=True, exist_ok=True)
    (d / "manifest.jsonl").write_text("".join(json.dumps(r) + "\n" for r in records))


def test_the_last_record_of_a_tile_wins_and_its_sources_are_kept(tmp_path):
    manifest(tmp_path, "glo90-90m", [rec(10, 20, out="old"), rec(10, 20, out="new", computed_at="2026-11-24T10:00:00Z")])
    p = pv.build(tmp_path, ["glo90-90m"], release="r-2", previous=None)
    t = pv.tile(p, "10,20")
    s = t["scales"]["glo90-90m"]
    assert s["outputs"] == "new" and s["computed_at"] == "2026-11-24T10:00:00Z" and s["code"] == "code-1"
    assert {i["item"] for i in s["inputs"]} == {ITEM_A, ITEM_B}
    assert t["data_date"] == "2022-05-09" and t["last_changed_in"] == "r-2"


def test_a_tile_computed_before_t52_says_its_date_was_not_recorded(tmp_path):
    manifest(tmp_path, "glo90-90m", [rec(10, 20)])
    s = pv.tile(pv.build(tmp_path, ["glo90-90m"], release="r-1", previous=None), "10,20")["scales"]["glo90-90m"]
    assert s["computed_at"] is None and s["computed_at_note"] == "not recorded (computed before T52)"


def test_an_unchanged_tile_keeps_the_release_where_it_last_changed(tmp_path):
    manifest(tmp_path, "glo90-90m", [rec(10, 20), rec(11, 20)])
    first = pv.build(tmp_path, ["glo90-90m"], release="r-1", previous=None)
    manifest(tmp_path, "glo90-90m", [rec(10, 20), rec(11, 20, out="changed", etag="e9", computed_at="2026-12-01T00:00:00Z")])
    second = pv.build(tmp_path, ["glo90-90m"], release="r-2", previous=first)
    assert pv.tile(second, "10,20")["last_changed_in"] == "r-1"
    assert pv.tile(second, "11,20")["last_changed_in"] == "r-2"


def test_release_changes_name_the_tiles_and_the_source_items_that_changed(tmp_path):
    manifest(tmp_path, "glo90-90m", [rec(10, 20), rec(11, 20)])
    first = pv.build(tmp_path, ["glo90-90m"], release="r-1", previous=None)
    manifest(tmp_path, "glo90-90m", [rec(10, 20), rec(11, 20, out="changed", etag="e9")])
    second = pv.build(tmp_path, ["glo90-90m"], release="r-2", previous=first)
    ch = pv.changes(first, second, events=[{"source": "copernicus-dem-glo90", "detected_on": "2026-12-01"}],
                    decision={"publish": True, "reasons": []})
    assert ch["previous"] == "r-1" and ch["release"] == "r-2"
    assert ch["tiles_recomputed"] == ["11,20"] and ch["source_items_changed"] == [ITEM_A]
    assert ch["events"][0]["source"] == "copernicus-dem-glo90" and ch["decision"]["publish"] is True


def test_the_file_is_compact_source_items_are_stored_once(tmp_path):
    manifest(tmp_path, "glo90-90m", [rec(10, 20), rec(11, 20)])
    p = pv.build(tmp_path, ["glo90-90m"], release="r-1", previous=None)
    assert len(p["items"]) == 2                                   # both tiles share the two items


def test_a_release_writes_its_provenance_and_its_changes_against_the_current_release_of_its_body(tmp_path):
    from discovery.release import write_provenance
    cube, out = tmp_path / "cube", tmp_path / "releases"
    manifest(cube, "glo90-90m", [rec(10, 20)])
    (out / "r-1").mkdir(parents=True)
    write_provenance(out / "r-1", cube, ["glo90-90m"], out, "r-1", body="moon")
    (out / "index.json").write_text(json.dumps({"current": "r-1", "current_by_body": {"moon": "r-1"}, "releases": []}))
    manifest(cube, "glo90-90m", [rec(10, 20, out="changed", etag="e9")])
    (out / "r-2").mkdir()
    write_provenance(out / "r-2", cube, ["glo90-90m"], out, "r-2", body="moon")
    ch = json.loads((out / "r-2" / "changes.json").read_text())
    assert ch["previous"] == "r-1" and ch["tiles_recomputed"] == ["10,20"] and ch["decision"] is None
    assert json.loads((out / "r-2" / "provenance.json").read_text())["last_changed_in"]["10,20"] == "r-2"
