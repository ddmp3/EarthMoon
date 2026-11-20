"""Offline tests of tools/precompute (no network call) :  python -m pytest tools/precompute -q"""
import json
import math
import os
import sys

import numpy as np
import pytest

sys.path.insert(0, os.path.dirname(__file__))
import enrich_candidates as ec  # noqa: E402
import modis_values as mv  # noqa: E402
import point_geometry as pg  # noqa: E402


# ------------------------------------------------------------------ lunar_reference
def test_lunar_latitude_grid():
    import lunar_reference as lr
    lat = lr.latitude_grid(7584, 40.0)
    assert lat[3791, 3791] < -89.99                               # center = south pole
    assert lat[3791, 0] == pytest.approx(-85.0, abs=0.01)         # edge of the LDEM_85S grid = 85°S


def test_lunar_window_stats_on_inclined_plane():
    import lunar_reference as lr
    x = np.arange(100) * 40.0
    z = np.tile(x * math.tan(math.radians(10)), (100, 1))         # plane tilted at 10°
    st = lr.window_stats(z, 40.0, 1000.0)
    assert st["window_px"] == 25 and st["slope_mean"].size == 16
    assert np.allclose(st["slope_mean"], 10, atol=0.01) and np.allclose(st["slope_max"], 10, atol=0.01)
    mask = np.zeros((100, 100), dtype=bool)
    mask[:25, :25] = True
    assert lr.window_stats(z, 40.0, 1000.0, mask)["slope_mean"].size == 1


def test_lunar_apply_to_profile():
    import lunar_reference as lr
    d = {f"p{p}": float(p) for p in lr.PERCENTILES}
    prof = lr.apply_to_profile({"params": {"wind": {"min": 0}}, "todo": ["slope_mean, slope_max, roughness : LOLA", "solar"]},
                               {"windows": 9, "window_m": 1000.0, "slope_mean": d, "slope_max": d, "roughness": d})
    assert prof["params"]["slope_mean"]["min"] == 25.0 and prof["params"]["slope_mean"]["max"] == 75.0
    assert prof["params"]["wind"] == {"min": 0} and prof["todo"] == ["solar"]


# ------------------------------------------------------------------ point_geometry
def test_tile_names():
    assert pg.tile_name(-24.1, -70.0) == "Copernicus_DSM_COG_10_S25_00_W070_00_DEM"
    assert pg.tile_name(78.2, 15.6) == "Copernicus_DSM_COG_10_N78_00_E015_00_DEM"


def test_point_tile_on_integer_latitude():
    # 25.0°N is the top edge of tile N24 (tile N25 does not contain it: failure observed at Harrat Khaybar).
    assert "N24_00_E039" in pg.point_tile_url(25.0, 39.92)
    assert "S25_00_W070" in pg.point_tile_url(-24.0, -69.5)
    assert "N25_00_E039" in pg.point_tile_url(25.1, 39.92)


def test_geometry_on_inclined_plane():
    dx = dy = 30.0
    rows = np.arange(37)[:, None] * np.ones((1, 37))
    z = 1000 + rows * dy * math.tan(math.radians(10))
    g = pg.geometry_from_array(z, dx, dy)
    assert abs(g["slope_mean"] - 10) < 0.05 and abs(g["slope_max"] - 10) < 0.05
    flat = pg.geometry_from_array(np.full((10, 10), 250.0), dx, dy)
    assert flat["slope_mean"] == 0 and flat["roughness"] == 0 and flat["elevation"] == 250


def test_geometry_all_nodata():
    g = pg.geometry_from_array(np.full((10, 10), np.nan), 30, 30)
    assert g["slope_mean"] is None and g["valid_frac"] == 0


# ------------------------------------------------------------------ enrich_candidates
def fake_geometry(lat, lon, window_m=1000.0):
    if lat < -70:
        raise pg.TileNotFound("pas de tile")
    return {"elevation": 10.0, "slope_mean": 1.0, "slope_max": 2.0, "roughness": 3.0, "valid_frac": 1.0}


def test_enrich_keeps_other_precomputed_values(monkeypatch):
    monkeypatch.setattr(ec.time, "sleep", lambda s: None)
    sites = [{"id": "a", "name": "A", "lat": 1, "lon": 2, "precomputed": {"ndvi": 0.05, "lst_day": 10.0}},
             {"id": "b", "name": "B", "lat": -75, "lon": 2}]
    out = ec.enrich(sites, geometry_fn=fake_geometry)
    a, b = out[0]["precomputed"], out[1]["precomputed"]
    assert a["slope_mean"] == 1.0 and a["ndvi"] == 0.05 and a["lst_day"] == 10.0 and "error" not in a
    assert b["slope_mean"] is None and "pas de tile" in b["error"]


# ------------------------------------------------------------------ modis_values : conversions
def test_lst_conversion():
    assert mv.lst_celsius(0) is None and mv.lst_celsius(7000) is None and mv.lst_celsius(None) is None
    assert abs(mv.lst_celsius(14000) - (14000 * 0.02 - 273.15)) < 1e-9  # 6.85 °C
    assert mv.lst_celsius(float("nan")) is None


def test_ndvi_conversion():
    assert mv.ndvi_value(-3000) is None and mv.ndvi_value(12000) is None
    assert abs(mv.ndvi_value(8500) - 0.85) < 1e-9 and abs(mv.ndvi_value(-500) + 0.05) < 1e-9


def test_sinusoidal_tile():
    # Tuiles MODIS connues : Atacama h11v11 ; Haughton h15v01 (STAC renvoie aussi h14 et h16) ;
    # Changtang h25v05 (STAC only returns h24v05 for a point search).
    assert mv.sinusoidal_tile(-24.5, -69.25) == (11, 11)
    assert mv.sinusoidal_tile(75.38, -89.67) == (15, 1)
    assert mv.sinusoidal_tile(34.5, 85.0) == (25, 5)
    assert mv.sinusoidal_tile(0.5, 0.5) == (18, 8)    # just north-east of (0°, 0°), corner of tiles h17/h18 v8/v9


def test_aggregate_needs_enough_valid_values():
    # 2 valid composites out of 12 (polar winter): no annual mean.
    pairs = [(-40.0, -42.0), (-41.0, -43.0)] + [(None, None)] * 10
    r = mv.aggregate(pairs, [0.05] * 5)
    assert all(r[k] is None for k in mv.KEYS)
    assert mv.aggregate(pairs, [0.05] * 5, min_valid=2)["lst_day"] == -40.5


def test_aggregate():
    r = mv.aggregate([(30.0, 10.0), (20.0, None), (None, 0.0), (40.0, 20.0)], [0.02, None, 0.04, 0.9], min_valid=1)
    assert r["lst_day"] == 30.0 and r["lst_night"] == 10.0
    assert r["lst_amplitude"] == 20.0          # (20 + 20) / 2, complete pairs only
    assert r["ndvi"] == 0.04                    # median of 0.02, 0.04, 0.9
    assert r["modis_samples"] == {"lst": 4, "lst_valid_pairs": 2, "ndvi": 4, "ndvi_valid": 3}
    empty = mv.aggregate([], [])
    assert all(empty[k] is None for k in mv.KEYS)


def test_pick_evenly():
    class It:
        def __init__(self, d):
            self.datetime = d
    items = [It(f"2024-{m:02d}-01") for m in range(12, 0, -1)] * 4  # 48 items, unordered
    picked = mv.pick_evenly(items, 12)
    assert len(picked) == 12 and [str(p.datetime) for p in picked] == sorted(str(p.datetime) for p in picked)
    assert mv.pick_evenly(items[:3], 12) == sorted(items[:3], key=mv._item_date)


# ------------------------------------------------------------------ modis_values : end to end with a fake Planetary Computer
class Asset:
    def __init__(self, href):
        self.href = href


class Item:
    def __init__(self, date, assets):
        self.datetime = date
        self.assets = {k: Asset(v) for k, v in assets.items()}


class FakePC:
    """Desert: day LST 40 °C, night 10 °C, NDVI 0.05. Forest (lat between -10 and 0): NDVI 0.85. Ocean (lon > 170): nothing."""

    def __init__(self):
        self.calls = 0

    def search(self, collection, lat, lon, start, end):
        if lon > 170:
            return []
        if collection == mv.LST_COLLECTION:
            return [Item(f"2024-{m:02d}-01", {mv.LST_DAY: f"day:{lat}", mv.LST_NIGHT: f"night:{lat}"}) for m in range(1, 13)]
        return [Item(f"2024-{m:02d}-15", {mv.NDVI_ASSET: f"ndvi:{lat}"}) for m in range(1, 13)]

    def sample(self, href, lat, lon):
        self.calls += 1
        kind = href.split(":")[0]
        forest = -10 < lat < 0
        return {"day": (40 + 273.15) / 0.02, "night": (10 + 273.15) / 0.02, "ndvi": 8500 if forest else 500}[kind]


def test_enrich_modis_end_to_end():
    pc = FakePC()
    sites = [{"id": "desert", "name": "D", "lat": -24.5, "lon": -69.25, "precomputed": {"slope_mean": 6}},
             {"id": "forest", "name": "F", "lat": -3.47, "lon": -62.37},
             {"id": "ocean", "name": "O", "lat": 0, "lon": 175}]
    out = {s["id"]: s["precomputed"] for s in mv.enrich_modis(sites, io=pc, log=lambda m: None)}
    d = out["desert"]
    assert d["slope_mean"] == 6                                  # the geometry is kept
    assert d["lst_day"] == pytest.approx(40, abs=0.01) and d["lst_night"] == pytest.approx(10, abs=0.01)
    assert d["lst_amplitude"] == pytest.approx(30, abs=0.01) and d["ndvi"] == 0.05
    assert "modis_error" not in d and "Planetary Computer" in d["modis_source"]
    assert out["forest"]["ndvi"] == 0.85                          # will be excluded by the bare-soil filter
    assert all(out["ocean"][k] is None for k in mv.KEYS) and "no MODIS image" in out["ocean"]["modis_error"]


def test_enrich_modis_skips_done_sites_unless_forced():
    pc = FakePC()
    done = [{"id": "x", "lat": 1, "lon": 1, "precomputed": {"ndvi": 0.1, "lst_day": 1, "lst_night": 0, "lst_amplitude": 1}}]
    mv.enrich_modis(done, io=pc, log=lambda m: None)
    assert pc.calls == 0
    mv.enrich_modis(done, io=pc, force=True, log=lambda m: None)
    assert pc.calls > 0


def test_main_writes_file(tmp_path, monkeypatch):
    f = tmp_path / "c.json"
    f.write_text(json.dumps([{"id": "desert", "name": "D", "lat": -24.5, "lon": -69.25}]), encoding="utf-8")
    monkeypatch.setattr(mv, "PlanetaryComputer", FakePC)
    assert mv.main([str(f), "-o", str(tmp_path / "out.json")]) == 0
    out = json.loads((tmp_path / "out.json").read_text(encoding="utf-8"))
    assert out[0]["precomputed"]["ndvi"] == 0.05


# ------------------------------------------------------------------ site_visuals
def test_visuals_bbox_is_a_square_in_metres():
    import site_visuals as sv
    w, s, e, n = sv.bbox_square(75.38, -89.67)
    height_m = math.radians(n - s) * sv.R_EARTH
    width_m = math.radians(e - w) * sv.R_EARTH * math.cos(math.radians(75.38))
    assert height_m == pytest.approx(12_000, rel=1e-6) and width_m == pytest.approx(12_000, rel=1e-6)


def test_visuals_hillshade_and_match_mask():
    import site_visuals as sv
    flat = np.zeros((20, 20))
    assert sv.hillshade(flat, 40.0).std() == 0                       # flat: uniform lighting
    x = np.arange(20) * 40.0
    slope10 = np.tile(x * math.tan(math.radians(10)), (20, 1))
    assert sv.match_mask(slope10, 40.0, 4.5, 13.3).all()             # 10° is in the lunar range
    assert not sv.match_mask(flat, 40.0, 4.5, 13.3).any()
    assert sv.hillshade(np.full((5, 5), np.nan), 40.0).shape == (5, 5)


def test_visuals_find_twin_picks_closest_valid_window():
    import site_visuals as sv
    slope = np.array([[2.0, 8.0], [12.0, 8.1]])
    rough = np.array([[5.0, 40.0], [60.0, 41.0]])
    valid = np.array([[True, False], [True, True]])
    r, c, dist = sv.find_twin(slope, rough, valid, 8.0, 40.0, 7.0, 40.0)
    assert (r, c) == (1, 1) and dist < 0.05                           # (0, 1) is exact but outside the valid area


def test_visuals_polar_latlon():
    import site_visuals as sv
    lat, _ = sv.polar_latlon(3791.5, 3791.5, 7584, 40.0)
    assert lat == pytest.approx(-90.0, abs=1e-6)
    lat, lon = sv.polar_latlon(3791.5, 7583, 7584, 40.0)              # bord droit : 85°S, longitude 90°E
    assert lat == pytest.approx(-85.0, abs=0.01) and lon == pytest.approx(90.0, abs=0.01)


# ------------------------------------------------------------------ site_visuals (T45)
def test_site_relief_values_come_from_terrain_v2_when_the_dataset_has_them():
    pytest.importorskip("rasterio")
    import site_visuals as sv
    site = {"id": "atacama", "precomputed": {"slope_mean": 7.97, "slope_max": 16.64, "roughness": 40.57}}
    dataset = {"sites": {"atacama": {"values": {"slope_mean": {"value": 7.85}, "slope_max": {"value": 15.2},
                                                "roughness": {"value": 38.9}}}}}
    assert sv.relief_values(site, dataset) == {"slope_mean": 7.85, "slope_max": 15.2, "roughness": 38.9, "basis": "terrain_v2"}
    assert sv.relief_values(site, None) == {"slope_mean": 7.97, "slope_max": 16.64, "roughness": 40.57, "basis": "precomputed (v1)"}
    assert sv.relief_values({"id": "x", "precomputed": {}}, dataset) is None


def test_the_match_panel_shows_the_same_relief_values_as_the_scorecard():
    root = os.path.join(os.path.dirname(__file__), "..", "..")
    manifest = json.load(open(os.path.join(root, "apps/web/public/sites/manifest.json"), encoding="utf-8"))
    dataset = json.load(open(os.path.join(root, "data/dataset-v2.json"), encoding="utf-8"))
    for sid, entry in manifest["sites"].items():
        v2 = dataset["sites"][sid]["values"]
        assert entry["earth"]["basis"] == "terrain_v2", sid
        for k in ("slope_mean", "roughness"):
            assert entry["earth"][k] == pytest.approx(v2[k]["value"]), (sid, k)
