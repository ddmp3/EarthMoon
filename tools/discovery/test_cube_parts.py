"""Keys, source listing, tile grids and cell statistics (T40). No network."""
import math

import numpy as np
import pytest

from discovery.cells import cell_table
from discovery.copernicus import PRODUCTS, neighbours, parse_listing, tile_key, tile_name
from discovery.grid import tile_grid
from discovery.keys import content_key


def test_content_key_is_order_independent_and_changes_with_any_input():
    a = content_key({"x": {"etag": "1"}, "y": {"etag": "2"}}, "abc", {"px": 40})
    assert a == content_key({"y": {"etag": "2"}, "x": {"etag": "1"}}, "abc", {"px": 40})
    assert a != content_key({"x": {"etag": "9"}, "y": {"etag": "2"}}, "abc", {"px": 40})
    assert a != content_key({"x": {"etag": "1"}, "y": {"etag": "2"}}, "abd", {"px": 40})
    assert a != content_key({"x": {"etag": "1"}, "y": {"etag": "2"}}, "abc", {"px": 90})
    assert len(a) == 64


def test_tile_names_follow_the_bucket_convention():
    assert tile_name(41, -122, "glo30") == "Copernicus_DSM_COG_10_N41_00_W122_00_DEM"
    assert tile_name(-1, 5, "glo90") == "Copernicus_DSM_COG_30_S01_00_E005_00_DEM"
    assert tile_key(41, -122, "glo30") == "Copernicus_DSM_COG_10_N41_00_W122_00_DEM/Copernicus_DSM_COG_10_N41_00_W122_00_DEM.tif"
    assert PRODUCTS["glo90"]["bucket"].startswith("https://copernicus-dem-90m")


def test_listing_keeps_dem_tiffs_with_their_change_signal():
    xml = ("<ListBucketResult><Contents><Key>Copernicus_DSM_COG_10_N41_00_W122_00_DEM/Copernicus_DSM_COG_10_N41_00_W122_00_DEM.tif</Key>"
           "<LastModified>2022-05-01T10:00:00.000Z</LastModified><ETag>&quot;abc-3&quot;</ETag><Size>123</Size></Contents>"
           "<Contents><Key>Copernicus_DSM_COG_10_N41_00_W122_00_DEM/AUXFILES/x.xml</Key><LastModified>x</LastModified>"
           "<ETag>&quot;z&quot;</ETag><Size>1</Size></Contents>"
           "<IsTruncated>true</IsTruncated><NextContinuationToken>TOK</NextContinuationToken></ListBucketResult>")
    objects, token = parse_listing(xml)
    assert token == "TOK"
    assert objects == {(41, -122): {"key": "Copernicus_DSM_COG_10_N41_00_W122_00_DEM/Copernicus_DSM_COG_10_N41_00_W122_00_DEM.tif",
                                    "etag": "abc-3", "size": 123, "last_modified": "2022-05-01T10:00:00.000Z"}}


def test_neighbours_wrap_the_antimeridian_and_skip_missing_tiles():
    have = {(0, 179), (0, -180), (1, 179)}
    assert set(neighbours(0, 179, have)) == {(0, 179), (0, -180), (1, 179)}
    assert neighbours(89, 0, {(89, 0)}) == [(89, 0)]


@pytest.mark.parametrize("lat", [0, 45, 75, -60])
def test_tile_grid_covers_the_tile_with_whole_windows_and_owns_each_window_once(lat):
    g = tile_grid(lat, 10, pixel_m=90.0, window_m=990.0)
    assert g.window_px == 11 and g.margin_px >= 1
    assert g.shape[0] == g.rows * 11 + 2 * g.margin_px and g.shape[1] == g.cols * 11 + 2 * g.margin_px
    lat_c, lon_c = g.window_centres_latlon()
    own = g.owned()
    assert own.shape == (g.rows, g.cols)
    assert np.all((lat_c[own] >= lat) & (lat_c[own] < lat + 1) & (lon_c[own] >= 10) & (lon_c[own] < 11))
    # owned windows tile the 1° cell: their count matches its area within the window-size quantisation
    area_km2 = 111.32 ** 2 * (math.sin(math.radians(lat + 1)) - math.sin(math.radians(lat))) * 180 / math.pi
    assert own.sum() * 0.99 ** 2 == pytest.approx(area_km2, rel=0.03)


def test_neighbouring_tiles_together_own_every_window_position_once():
    a, b = tile_grid(45, 10, 90.0, 990.0), tile_grid(45, 11, 90.0, 990.0)
    la, loa = a.window_centres_latlon()
    lb, lob = b.window_centres_latlon()
    assert not np.any((loa[a.owned()] >= 11)) and not np.any(lob[b.owned()] < 11)


def test_cell_table_reports_counts_spread_and_state_and_never_fills_missing():
    win = {"slope_mean": np.array([[1.0, 2.0, np.nan], [3.0, np.nan, np.nan]]),
           "valid_frac": np.array([[1.0, 1.0, 0.2], [1.0, 0.0, 0.1]])}
    cell = np.array([[0, 0, 1], [0, 1, 1]])
    owned = np.ones((2, 3), bool)
    t = cell_table(win, cell, owned, ("slope_mean",))
    c0 = t[0]
    assert c0["n_windows"] == 3 and c0["n_valid"] == 3 and c0["state"] == "evaluated"
    assert c0["slope_mean_median"] == 2.0 and c0["slope_mean_p5"] == pytest.approx(1.1)
    assert c0["slope_mean_sigma"] == pytest.approx(1.4826)
    c1 = t[1]
    assert c1["n_valid"] == 0 and c1["state"] == "missing" and np.isnan(c1["slope_mean_median"])


def test_cell_below_half_valid_windows_is_partial_and_unowned_windows_do_not_count():
    win = {"slope_mean": np.array([[1.0, np.nan, np.nan, 5.0]]), "valid_frac": np.array([[1, 0, 0, 1.0]])}
    cell = np.zeros((1, 4), int)
    owned = np.array([[True, True, True, False]])
    t = cell_table(win, cell, owned, ("slope_mean",))
    assert t[0]["n_windows"] == 3 and t[0]["n_valid"] == 1 and t[0]["state"] == "partial"
    assert t[0]["slope_mean_median"] == 1.0


def test_compute_tile_on_a_tilted_plane_with_a_lake_and_a_hole():
    from discovery.cube import compute_tile, coverage
    g = tile_grid(45, 10, 90.0, 990.0)
    h, w = g.shape
    z = np.tile(np.arange(w) * 90.0 * np.tan(np.radians(5)), (h, 1))
    z[:, : w // 2] = np.nan                                  # west half missing (e.g. ocean)
    water = np.zeros(g.shape, "float32")
    water[: h // 2] = 1.0                                    # north half is water
    windows, cells = compute_tile(z, g, {"water": water})
    ok = np.isfinite(windows["slope_mean"])
    assert np.allclose(windows["slope_mean"][ok], 5.0, atol=1e-6)
    assert len(windows["row"]) == g.owned().sum()
    cov = coverage(cells)
    assert cov["evaluated"] > 0 and cov["missing"] > 0       # missing cells are kept as missing, never filled
    assert all(np.isnan(r["slope_mean_median"]) for r in cells.values() if r["state"] == "missing")
    fr = [r["wc_water"] for r in cells.values()]
    assert min(fr) == 0.0 and max(fr) == 1.0
    assert sum(r["area_km2"] for r in cells.values()) == pytest.approx(g.owned().sum() * 0.99 ** 2)


def test_random_tiles_are_seeded_distinct_and_existing():
    from discovery.measure import pick
    have = {(la, lo) for la in range(-60, 80) for lo in range(-180, 180) if lo % 3 == 0}
    a = pick(20261120, 100, have)
    assert a == pick(20261120, 100, have) and len(set(a)) == 100 and all(t in have for t in a)


def test_projection_scales_median_tile_time_by_tiles_share_and_workers():
    from discovery.measure import projection
    recs = [{"seconds": {"total": 10.0, "read": 8.0, "mask": 1.0}}] * 5
    p = projection(recs, workers=8, n_tiles=26450, share=0.5)
    assert p["projected_hours"] == round(26450 * 0.5 * 10 / 8 / 3600, 1)


def test_worldcover_overview_is_the_coarsest_not_coarser_than_the_pixel():
    from discovery.worldcover import overview_level, tiles_around
    assert overview_level(90.0) == 2 and overview_level(40.0) == 1 and overview_level(15.0) is None
    assert tiles_around(1, 10) == ["N00E009"] and len(tiles_around(2, 2)) == 4


def test_rebuild_gives_byte_identical_parquet(tmp_path):
    from discovery.cube import _write, compute_tile
    g = tile_grid(10, 20, 90.0, 990.0)
    rng = np.random.default_rng(3)
    z = np.cumsum(rng.normal(0, 5, g.shape), axis=1)
    shas = []
    for i in range(2):
        windows, _ = compute_tile(z, g)
        shas.append(_write(tmp_path / f"w{i}.parquet", windows))
    assert shas[0] == shas[1]


def test_a_tile_reruns_when_its_code_or_any_neighbour_etag_changes(tmp_path):
    from discovery.cube import _up_to_date
    listing = {(0, 0): {"key": "a", "etag": "1"}, (0, 1): {"key": "b", "etag": "2"}}
    rec = {"code": "c1", "inputs": {"a": {"etag": "1"}, "b": {"etag": "2"}}}
    name = "Copernicus_DSM_COG_30_N00_00_E000_00_DEM"
    for t in ("windows", "cells"):
        (tmp_path / f"{name}.{t}.parquet").write_bytes(b"x")
    assert _up_to_date(rec, (0, 0), listing, "c1", tmp_path, "glo90")
    assert not _up_to_date(rec, (0, 0), listing, "c2", tmp_path, "glo90")
    listing[(0, 1)]["etag"] = "3"
    assert not _up_to_date(rec, (0, 0), listing, "c1", tmp_path, "glo90")
    assert not _up_to_date(None, (0, 0), listing, "c1", tmp_path, "glo90")


def test_code_version_ignores_line_endings_and_changes_with_the_source(tmp_path):
    from discovery.cube import CODE_FILES, code_version
    for name in CODE_FILES:
        (tmp_path / name).parent.mkdir(parents=True, exist_ok=True)
        (tmp_path / name).write_bytes(b"a = 1\n")
    v = code_version(tmp_path)
    (tmp_path / CODE_FILES[0]).write_bytes(b"a = 1\r\n")
    assert code_version(tmp_path) == v
    (tmp_path / CODE_FILES[0]).write_bytes(b"a = 2\n")
    assert code_version(tmp_path) != v


def test_summary_keeps_the_latest_record_per_tile_and_reports_coverage_shares():
    from discovery.measure import summary
    old = {"tile": "A", "code": "old", "commit": "c0", "windows": 9, "valid_windows": 9,
           "cells": {"evaluated": 9, "partial": 0, "missing": 0}, "seconds": {"total": 9.0, "read": 1.0, "mask": 1.0}}
    a = {**old, "code": "new", "commit": "c1", "cells": {"evaluated": 6, "partial": 1, "missing": 3}, "windows": 10,
         "valid_windows": 7, "seconds": {"total": 2.0, "read": 1.0, "mask": 0.5}}
    b = {**a, "tile": "B", "cells": {"evaluated": 0, "partial": 0, "missing": 10}, "valid_windows": 0,
         "seconds": {"total": 4.0, "read": 2.0, "mask": 0.5}}
    s = summary([old, a, b])
    assert s["tiles"] == 2 and s["code"] == ["new"] and s["commits"] == ["c1"]
    assert s["cells"] == {"evaluated": 6, "partial": 1, "missing": 13, "total": 20}
    assert s["cell_shares"] == {"evaluated": 0.3, "partial": 0.05, "missing": 0.65}
    assert s["windows"] == {"total": 20, "valid": 7} and s["seconds"]["median_total"] == 3.0


def test_provenance_commit_comes_from_the_runner_when_given(monkeypatch):
    from discovery.cube import git_commit
    monkeypatch.setenv("EARTHMOON_COMMIT", "abc123")
    assert git_commit() == "abc123"


def test_pixels_without_worldcover_are_unknown_not_absent():
    from discovery.worldcover import fractions
    fr = fractions(np.array([[0, 70], [10, 0]], dtype="uint8"))
    assert np.isnan(fr["snow_ice"][0, 0]) and fr["snow_ice"][0, 1] == 1.0 and fr["snow_ice"][1, 0] == 0.0
    assert np.array_equal(fr["covered"], [[0.0, 1.0], [1.0, 0.0]])


def test_cells_outside_worldcover_have_unknown_mask_fractions_and_zero_cover():
    from discovery.cube import compute_tile
    g = tile_grid(-76, -6, 90.0, 990.0)                          # south of 60°S: no WorldCover tile
    z = np.tile(np.arange(g.shape[1]) * 90.0 * np.tan(np.radians(5)), (g.shape[0], 1))
    nan = np.full(g.shape, np.nan, "float32")
    windows, cells = compute_tile(z, g, {"snow_ice": nan, "covered": np.zeros(g.shape, "float32")})
    assert np.isnan(windows["wc_snow_ice"]).all() and (windows["wc_covered"] == 0).all()
    assert all(np.isnan(r["wc_snow_ice"]) and r["wc_covered"] == 0 for r in cells.values())


def test_window_mask_fraction_uses_its_covered_pixels_only():
    from discovery.cube import compute_tile
    g = tile_grid(45, 10, 90.0, 990.0)
    z = np.zeros(g.shape) + np.arange(g.shape[1]) * 5.0
    ice = np.ones(g.shape, "float32")
    ice[:, ::2] = np.nan                                         # every other column has no WorldCover value
    windows, _ = compute_tile(z, g, {"snow_ice": ice, "covered": np.isfinite(ice).astype("float32")})
    assert np.allclose(windows["wc_snow_ice"], 1.0) and np.all((windows["wc_covered"] > 0.4) & (windows["wc_covered"] < 0.6))


def test_missing_cells_are_split_into_water_outside_worldcover_and_land():
    from discovery.measure import missing_breakdown
    nan = float("nan")
    cells = {"state": ["missing", "missing", "missing", "missing", "evaluated"],
             "wc_water": [0.9, nan, 0.1, 0.5, 0.0], "wc_covered": [1.0, 0.0, 1.0, 1.0, 1.0]}
    assert missing_breakdown(cells) == {"water": 2, "outside_worldcover": 1, "land": 1}


def test_latest_keeps_the_last_record_of_each_tile_in_order_of_first_appearance():
    from discovery.measure import latest
    recs = [{"tile": "A", "v": 1}, {"tile": "B", "v": 1}, {"tile": "A", "v": 2}]
    assert latest(recs) == [{"tile": "A", "v": 2}, {"tile": "B", "v": 1}]


def test_worldcover_fractions_cover_the_seven_hidden_ground_classes():
    from discovery.worldcover import MASK_CLASSES, fractions
    assert MASK_CLASSES == {10: "tree", 40: "cropland", 50: "built", 70: "snow_ice", 80: "water", 90: "wetland",
                            95: "mangroves"}
    fr = fractions(np.array([[40, 90], [95, 30]], dtype="uint8"))
    assert fr["cropland"][0, 0] == 1 and fr["wetland"][0, 1] == 1 and fr["mangroves"][1, 0] == 1
    assert all(fr[n][1, 1] == 0 for n in MASK_CLASSES.values())              # grassland (30) is bare enough
