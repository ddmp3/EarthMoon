"""Incremental recompute planner (T52 step 3, ADR-009 section 2). Synthetic world of 4 x 4 tiles, two targets."""
import pytest

from discovery.refresh_plan import World, code_version, describe, plan, tiles_of_item

TILES = [f"{la},{lo}" for la in range(10, 14) for lo in range(20, 24)]
WORLD = World(tiles=TILES, targets={"moon-a": ["lola"], "moon-b": ["sldem"]},
              tile_sources=["copernicus-dem-glo90", "esa-worldcover"], global_sources=["add-rock-outcrop-v7-3"],
              context_sources=["obu-permafrost-2018"])
CODE = {s: f"code-{s}" for s in ("features", "profiles", "assess", "zones", "context", "validate", "export")}
PARAMS = {"tau": 0.5}


def dem(la, lo):
    ns, ew = ("N" if la >= 0 else "S"), ("E" if lo >= 0 else "W")
    return f"Copernicus_DSM_COG_30_{ns}{abs(la):02d}_00_{ew}{abs(lo):03d}_00_DEM/x_DEM.tif"


def signals(**changes):
    s = {"copernicus-dem-glo90": {dem(int(t.split(",")[0]), int(t.split(",")[1])): {"etag": "e"} for t in TILES},
         "esa-worldcover": {"v200/2021/map/ESA_WorldCover_10m_2021_v200_N09E018_Map.tif": {"etag": "w"}},
         "lola": {"ldem.img": {"size": 1}}, "sldem": {"t.img": {"size": 2}},
         "add-rock-outcrop-v7-3": {"doi": {"version": "7.3"}}, "obu-permafrost-2018": {"doi": {"updated": "2019"}}}
    for src, items in changes.items():
        s[src.replace("_", "-")] = {**s[src.replace("_", "-")], **items}
    return s


def baseline():
    return plan(WORLD, signals(), CODE, PARAMS, previous=None)["keys"]


def test_no_change_reruns_nothing():
    p = plan(WORLD, signals(), CODE, PARAMS, previous=baseline())
    assert p["rerun"] == {} and p["withdrawn_tiles"] == []


def test_one_tile_change_reruns_that_tile_its_neighbour_cells_and_the_global_steps():
    p = plan(WORLD, signals(copernicus_dem_glo90={dem(11, 21): {"etag": "new"}}), CODE, PARAMS, previous=baseline())
    r = p["rerun"]
    assert r["features"] == ["11,21"]
    assert sorted(r["assess"]) == sorted(f"{la},{lo}" for la in (10, 11, 12) for lo in (20, 21, 22))  # one cell margin
    assert r["zones"] == ["moon-a", "moon-b"] and r["validate"] == ["global"] and r["export"] == ["moon-a", "moon-b"]
    assert "profiles" not in r and "context" not in r


def test_a_planetary_change_reruns_compare_but_no_earth_feature():
    p = plan(WORLD, signals(lola={"ldem.img": {"size": 9}}), CODE, PARAMS, previous=baseline())
    r = p["rerun"]
    assert r["profiles"] == ["moon-a"] and "features" not in r
    assert sorted(r["assess"]) == sorted(TILES)


def test_a_worldcover_tile_covers_three_by_three_degrees():
    assert tiles_of_item("esa-worldcover", "v200/2021/map/ESA_WorldCover_10m_2021_v200_N09E018_Map.tif") == \
        {f"{la},{lo}" for la in (9, 10, 11) for lo in (18, 19, 20)}
    assert tiles_of_item("copernicus-dem-glo90", dem(-1, -2)) == {"-1,-2"}


def test_a_changed_parameter_or_step_code_reruns_everything_downstream():
    p = plan(WORLD, signals(), {**CODE, "assess": "code-new"}, PARAMS, previous=baseline())
    assert "features" not in p["rerun"] and sorted(p["rerun"]["assess"]) == sorted(TILES)
    q = plan(WORLD, signals(), CODE, {"tau": 0.7}, previous=baseline())
    assert set(q["rerun"]) == {"features", "profiles", "assess", "zones", "context", "validate", "export"}


def test_a_context_source_reruns_the_context_layer_only():
    p = plan(WORLD, signals(obu_permafrost_2018={"doi": {"updated": "2026"}}), CODE, PARAMS, previous=baseline())
    assert set(p["rerun"]) == {"context", "export"}


def test_a_withdrawn_tile_is_reported_so_its_cells_become_not_evaluated():
    s = signals()
    del s["copernicus-dem-glo90"][dem(12, 22)]
    p = plan(WORLD, s, CODE, PARAMS, previous=baseline())
    assert p["withdrawn_tiles"] == ["12,22"] and "12,22" in p["rerun"]["assess"]


def test_the_dry_run_estimates_time_from_measured_step_times():
    p = plan(WORLD, signals(copernicus_dem_glo90={dem(11, 21): {"etag": "new"}}), CODE, PARAMS, previous=baseline())
    text = describe(p, seconds_per_unit={"features": 60, "assess": 10, "zones": 100, "validate": 600, "export": 50})
    assert "features: 1 unit" in text and "assess: 9 units" in text
    assert "about 0.3 h" in text                                   # 60 + 90 + 200 + 600 + 100 s = 1050 s


def test_code_version_ignores_tests_and_docs(tmp_path):
    (tmp_path / "a.py").write_text("x = 1\n")
    v1 = code_version([tmp_path / "a.py"])
    (tmp_path / "test_a.py").write_text("assert True\n")
    assert code_version([tmp_path / "a.py"]) == v1
    (tmp_path / "a.py").write_text("x = 2\n")
    assert code_version([tmp_path / "a.py"]) != v1


@pytest.mark.parametrize("bad", ["foo.tif", "Copernicus_DSM_COG_30_X10_00_E020_00_DEM/x.tif"])
def test_an_item_that_names_no_tile_maps_to_no_tile(bad):
    assert tiles_of_item("copernicus-dem-glo90", bad) == set()
