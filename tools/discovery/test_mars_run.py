"""Mars discovery run (T48, protocol mars-v1): its settings of the discovery engine, its confidence rule and the
assignment of windows larger than a 5 km cell. Synthetic cubes only."""
import json
import math

import numpy as np
import pytest

import discovery.discover as d
from discovery import mars_run

SAVED = ("PRODUCT", "SCALES", "COVERAGE_SCALES", "TARGET_SCALE", "SCENARIO_TARGETS", "ELIMINATING", "LOAD_COLUMNS",
         "CELL_SCHEMA", "WINDOW_ASSIGN", "WINDOW_M", "ROCK_RADIUS_M", "CONFIDENCE", "RULES_IN_USE",
         "SUITABILITY_IN_USE")


@pytest.fixture
def mars():
    """The engine configured for Mars during one test, then restored to its lunar settings."""
    import copy
    keep = {k: copy.deepcopy(getattr(d, k)) for k in SAVED}
    d._CTX.clear()
    mars_run.configure(d)
    yield d
    for k, v in keep.items():
        cur = getattr(d, k)
        if isinstance(cur, dict) and isinstance(v, dict):
            cur.clear()
            cur.update(v)
        elif isinstance(cur, list) and isinstance(v, list):
            cur[:] = v
        else:
            setattr(d, k, v)
    d._CTX.clear()


def test_the_mars_run_assesses_only_martian_targets_with_their_own_scales(mars):
    assert set(mars.TARGET_SCALE) == {"mars-north-polar", "mars-south-polar", "mars-ice-rich-midlatitudes"}
    assert mars.TARGET_SCALE["mars-north-polar"] == "glo90-115m-w25"
    assert mars.TARGET_SCALE["mars-ice-rich-midlatitudes"] == "glo90-463m-w25"
    assert mars.SCENARIO_TARGETS == {"D": sorted(mars.TARGET_SCALE)} and mars.ELIMINATING == {"D": []}
    names = mars.CELL_SCHEMA.names
    assert "mars-south-polar:median" in names and not any(n.startswith("moon-") for n in names)
    assert "mars-north-polar:median" in mars.LOAD_COLUMNS and "moon-psr:median" not in mars.LOAD_COLUMNS


def test_no_lunar_requirement_or_suitability_is_applied_on_mars(mars):
    assert mars.RULES_IN_USE == {} and mars.SUITABILITY_IN_USE == {}


def test_the_lunar_settings_are_unchanged_outside_the_mars_run():
    assert "moon-psr" in d.TARGET_SCALE and d.WINDOW_ASSIGN == "centre" and d.CONFIDENCE is None


def test_confidence_is_the_lunar_share_of_valid_and_hidden_windows():
    """Moon: high needs 20 valid windows of about 25 (80%) and under 10% hidden. Mars cells hold 1 to 4 windows."""
    c = mars_run.share_confidence
    assert c(valid=1, windows=1, masked=0, unknown_mask=0) == "high"
    assert c(valid=3, windows=4, masked=0, unknown_mask=0) == "medium"       # 75% valid
    assert c(valid=4, windows=4, masked=0, unknown_mask=0) == "high"
    assert c(valid=1, windows=2, masked=1, unknown_mask=0) == "medium"
    assert c(valid=0, windows=1, masked=1, unknown_mask=0) == "low"
    assert c(valid=0, windows=0, masked=0, unknown_mask=0) == "low"


def test_window_sizes_follow_the_pixel_of_each_scale(mars):
    assert mars.WINDOW_M["glo90-463m-w25"] == pytest.approx(25 * 463.08)
    assert mars.ROCK_RADIUS_M["glo90-115m-w25"] == pytest.approx(0.4 * 25 * 115.77)


def _big_window_cube(tmp_path, window_m):
    """Windows of `window_m` on a square metric grid around 10.5°N 20.5°E, in tile 10,20 only."""
    import pyarrow as pa
    import pyarrow.parquet as pq
    from discovery.compare import MASK_CLASSES
    from discovery.copernicus import tile_name
    km_deg = 6371.0088 * math.pi / 180
    dlat = window_m / 1000 / km_deg
    lats = 10.5 + dlat * np.arange(-4, 5)
    lat, lon = [], []
    for la in lats:
        dlon = dlat / math.cos(math.radians(la))
        lo = 20.5 + dlon * np.arange(-4, 5)
        lat += [la] * lo.size
        lon += lo.tolist()
    lat, lon = np.array(lat), np.array(lon)
    n = lat.size
    slope = np.arange(n, dtype=float)                                    # one distinct value per window
    cols = {"i": np.arange(n), "j": np.zeros(n, int), "lat": lat, "lon": lon, "slope_mean": slope,
            "traversable_15": np.ones(n), "traversable_20": np.ones(n), "wc_covered": np.ones(n)}
    cols.update({c: np.zeros(n) for c in MASK_CLASSES})
    sc = "glo90-463m-w25"
    (tmp_path / sc).mkdir()
    pq.write_table(pa.table(cols), tmp_path / sc / f"{tile_name(10, 20, 'glo90')}.windows.parquet")
    np.savez(tmp_path / "refs.npz", **{t: np.sort(np.arange(n, dtype=float)) for t in d.TARGET_SCALE})
    np.save(tmp_path / "rock.npy", np.zeros((2, 2), "uint8"))
    (tmp_path / "rock.json").write_text(json.dumps({"transform": [1, 0, 0, 0, -1, 0]}))
    return lat, lon, dlat


def test_a_window_larger_than_a_cell_counts_for_every_cell_whose_centre_it_holds(tmp_path, mars):
    lat, lon, dlat = _big_window_cube(tmp_path, mars.WINDOW_M["glo90-463m-w25"])
    rows = mars.assess_tile("10,20", str(tmp_path), str(tmp_path / "refs.npz"), str(tmp_path / "rock"),
                            {"10,20": ["glo90-463m-w25"]})
    inner = [r for r in rows if abs(r["lat"] - 10.5) < 3 * dlat and abs(r["lon"] - 20.5) < 3 * dlat]
    assert len(inner) > 4 * 25                                           # many more cells than the 25 inner windows
    t = "mars-ice-rich-midlatitudes"
    assert all(r.get(f"{t}:windows", 0) >= 1 and r.get(f"{t}:median") is not None for r in inner)
    assert all(r["confidence"] == "high" for r in inner)                 # one valid, unmasked window is the whole cell
    assert all(r.get("mars-north-polar:screened_out") is True for r in inner)     # not refined at 115 m
    ids = [r["cell"] for r in rows]
    assert len(ids) == len(set(ids))


def test_cells_under_one_window_share_its_value(tmp_path, mars):
    lat, lon, dlat = _big_window_cube(tmp_path, mars.WINDOW_M["glo90-463m-w25"])
    rows = mars.assess_tile("10,20", str(tmp_path), str(tmp_path / "refs.npz"), str(tmp_path / "rock"),
                            {"10,20": ["glo90-463m-w25"]})
    t = "mars-ice-rich-midlatitudes"
    centre = int(np.argmin(np.abs(lat - 10.5) + np.abs(lon - 20.5)))
    near = [r for r in rows if abs(r["lat"] - lat[centre]) < 0.2 * dlat and abs(r["lon"] - lon[centre]) < 0.2 * dlat
            and r.get(f"{t}:windows") == 1]
    assert near and len({r[f"{t}:median"] for r in near}) == 1


def test_validation_reads_the_martian_masked_unit_and_blocks_of_five_windows():
    import types
    v = types.SimpleNamespace(BLOCK_KM={})
    mars_run.configure_validation(v)
    assert v.MASK_SCALE == "glo90-115m-w25"
    assert v.MASK_REACH_KM == pytest.approx(25 * 115.77 / 1000 / math.sqrt(2))
    assert v.BLOCK_KM["mars-ice-rich-midlatitudes"] == pytest.approx(5 * 25 * 463.08 / 1000)
    assert v.PROFILE_KM_PER_DEG == pytest.approx(59.27, abs=0.01)
    assert "D" in v.POSITIVES and v.REPRO["window_px"] == 25


def test_the_mars_release_lists_scenario_d_martian_profiles_and_their_sources(mars):
    import types
    from discovery import release as rel
    r = types.SimpleNamespace(COVERAGE_TEXT=dict(rel.COVERAGE_TEXT))
    mars_run.configure_release(r)
    assert r.BODY == "mars" and r.PROTOCOL == "validation-protocol-mars-v1" and r.SCENARIO_FILES == {"D": "D-mars.yaml"}
    assert "copernicus-dem-glo30" not in r.EARTH_SOURCES
    assert "80%" in r.COVERAGE_TEXT["evaluated"] and set(r.COVERAGE_TEXT) == set(rel.COVERAGE_TEXT)


def test_release_index_keeps_the_lunar_default_and_a_current_release_per_body():
    from discovery.release import keep_releases
    listed = [{"id": f"r-m{k}"} for k in range(4)] + [{"id": "r-x1", "body": "mars"}]
    out = keep_releases(listed, {"id": "r-x2", "body": "mars"})
    assert [r["id"] for r in out] == ["r-x2", "r-m0", "r-m1", "r-m2", "r-m3", "r-x1"]   # no lunar release evicted


def test_tile_lists_name_every_tile_of_the_cube_at_each_scale(tmp_path):
    from discovery.copernicus import tile_name
    for sc in ("glo90-115m-w25", "glo90-463m-w25"):
        (tmp_path / sc).mkdir()
        for la, lo in ((10, 20), (-80, -179)):
            (tmp_path / sc / f"{tile_name(la, lo, 'glo90')}.windows.parquet").write_bytes(b"")
    files = mars_run.tile_lists(tmp_path, tmp_path / "run")
    assert [f.name for f in files] == ["tiles-refine-glo90-115m-w25.txt", "tiles-refine-glo90-463m-w25.txt"]
    assert sorted(files[0].read_text().split()) == ["-80,-179", "10,20"]
