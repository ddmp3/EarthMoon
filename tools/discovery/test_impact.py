"""Pre-analysis of a detected update (T52b, David 24/11/2026): what it would recompute and how long, without any
compute."""
import json

from discovery import impact as im

DEM = "Copernicus_DSM_COG_30_N10_00_E020_00_DEM/Copernicus_DSM_COG_30_N10_00_E020_00_DEM.tif"


def release(tmp_path, rid, body, targets, inputs, tiles=1000, cells=250_000):
    d = tmp_path / rid
    d.mkdir(parents=True)
    (d / "release.json").write_text(json.dumps({"release": rid, "processing": [
        {"step": "cells", "assessed_tiles": tiles, "cells": cells}]}))
    (d / "scenarios.json").write_text(json.dumps({"scenarios": [{"id": "S", "assessed_targets": targets}]}))
    (d / "profiles.json").write_text(json.dumps({"profiles": [{"id": t, "inputs": inputs[t]} for t in targets]}))
    srcs = ["copernicus-dem-glo90", "esa-worldcover", "add-rock-outcrop-v7-3", "obu-permafrost-2018"]
    (d / "method.json").write_text(json.dumps({"sources": [{"id": s} for s in srcs]}))
    return {"id": rid, "body": body}


def world(tmp_path):
    rels = [release(tmp_path, "r-m", "moon", ["moon-psr", "moon-mare-plains"],
                    {"moon-psr": {"lro-lola-ldem-85s-40m": {}}, "moon-mare-plains": {"moon-cube/inputs": {"SLDEM2015_x.IMG": {}}}}),
            release(tmp_path, "r-x", "mars", ["mars-north-polar"], {"mars-north-polar": {"mola/n": {}}})]
    return im.releases(tmp_path, rels)


def test_one_earth_tile_reassesses_its_neighbours_in_every_release_that_uses_the_source(tmp_path):
    out = im.impact("copernicus-dem-glo90", {"changed": [DEM], "withdrawn": [], "added": []}, world(tmp_path))
    assert out["kind"] == "earth_tiles" and out["tiles_changed"] == ["10,20"] and out["tiles_reassessed"] == 9
    assert [r["release"] for r in out["releases"]] == ["r-m", "r-x"]
    m = out["releases"][0]
    assert m["targets"] == ["moon-mare-plains", "moon-psr"] and m["cells_estimate"] == 9 * 250
    assert out["cpu_hours_estimate"] > 0 and "calibration" in out["basis"]
    assert out["recompute_started"] is False


def test_a_planetary_change_touches_its_targets_only_on_every_tile_and_no_earth_feature(tmp_path):
    out = im.impact("lro-lola-ldem-85s-40m", {"changed": ["ldem_85s_40m.img"], "withdrawn": [], "added": []}, world(tmp_path))
    assert out["kind"] == "planetary" and [r["release"] for r in out["releases"]] == ["r-m"]
    m = out["releases"][0]
    assert m["targets"] == ["moon-psr"] and m["tiles_reassessed"] == 1000 and m["earth_features"] is False
    assert m["cells_estimate"] == 250_000


def test_a_context_layer_recomputes_the_context_only(tmp_path):
    out = im.impact("obu-permafrost-2018", {"changed": ["doi"], "withdrawn": [], "added": []}, world(tmp_path))
    assert out["kind"] == "earth_context" and all(r["targets"] == [] and r["context"] for r in out["releases"])
    assert out["cpu_hours_estimate"] is None and "not measured" in out["basis"]      # never a made-up 0


def test_the_cube_inputs_of_a_lunar_target_map_to_their_catalogue_source(tmp_path):
    out = im.impact("sldem2015", {"changed": ["SLDEM2015_x.IMG"], "withdrawn": [], "added": []}, world(tmp_path))
    assert out["releases"][0]["targets"] == ["moon-mare-plains"]


def test_a_source_no_release_uses_has_no_impact(tmp_path):
    out = im.impact("emit-l2b-minerals", {"changed": ["x"], "withdrawn": [], "added": []}, world(tmp_path))
    assert out["releases"] == [] and out["cpu_hours_estimate"] == 0


def test_the_mars_geologic_map_input_is_traced_to_its_catalogue_entry():
    """A new version of the Tanaka map must reach the volcanic-plains target in the pre-analysis."""
    from discovery.impact import _sources_of_inputs
    assert _sources_of_inputs({"tanaka2014/SIM3292_Global_Geology.shp": {}}) == {"usgs-mars-geologic-map-2014"}
