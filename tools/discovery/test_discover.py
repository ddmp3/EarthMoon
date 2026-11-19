"""Global run helpers (T43): candidates, zone ranking, controls, bias bands. Synthetic data only."""
import numpy as np
import pytest

from discovery.discover import (candidates, latitude_bands, locate_points, percentile_rank, rank_zones,
                                rock_masked)


def test_candidate_needs_typicality_no_elimination_and_mostly_unmasked_windows():
    med = np.array([0.6, 0.6, 0.6, 0.4, np.nan])
    elim = np.array([False, True, False, False, False])
    masked_share = np.array([0.1, 0.1, 0.6, 0.1, 0.0])
    assert candidates(med, elim, masked_share, tau=0.5).tolist() == [True, False, False, False, False]


def test_zones_rank_by_median_typicality_then_area():
    zones = [{"median": 0.7, "area_km2": 75}, {"median": 0.9, "area_km2": 75}, {"median": 0.7, "area_km2": 200}]
    assert [z["area_km2"] for z in rank_zones(zones)] == [75, 200, 75] and rank_zones(zones)[0]["median"] == 0.9


def test_points_are_located_in_the_cell_whose_centre_is_nearest_within_reach():
    lat, lon = np.array([10.0, 10.0449]), np.array([20.0, 20.0])          # 5 km apart
    idx = locate_points(np.array([10.01, 30.0]), np.array([20.0, 30.0]), lat, lon, reach_km=3.6)
    assert idx.tolist() == [0, -1]                                          # second point: no cell (missing)


def test_percentile_rank_among_evaluated_cells():
    vals = np.array([0.1, 0.2, 0.3, 0.4, np.nan])
    assert percentile_rank(0.35, vals) == pytest.approx(75.0) and np.isnan(percentile_rank(np.nan, vals))


def test_latitude_bands_count_cells_per_ten_degrees():
    out = latitude_bands(np.array([-85.0, -5.0, 5.0, 5.5, 89.0]), np.array([True, False, True, True, False]))
    assert out["-90..-80"] == {"cells": 1, "selected": 1} and out["0..10"] == {"cells": 2, "selected": 2}
    assert out["-10..0"] == {"cells": 1, "selected": 0}


def test_south_of_sixty_ice_is_masked_and_rock_is_bare_ground():
    share = np.array([0.0, 0.8, np.nan])                  # ice, rock, north of 60°S (WorldCover applies)
    covered = np.array([0.0, 0.0, 1.0])
    masked, known = rock_masked(share, covered)
    assert masked.tolist() == [True, False, False] and known.tolist() == [True, True, False]


def test_scenario_dossier_list_merges_targets_and_keeps_one_zone_per_place():
    from discovery.discover import dossier_zones
    z = lambda t, m, lat: {"target": t, "median": m, "area_km2": 100.0, "lat": lat, "lon": 10.0}
    zones = [z("a", 0.9, 0.0), z("b", 0.95, 0.03), z("a", 0.8, 5.0), z("b", 0.7, 9.0)]
    out = dossier_zones(zones, top=3, same_km=10.0)
    assert [(x["target"], x["median"]) for x in out] == [("b", 0.95), ("a", 0.8), ("b", 0.7)]
    assert out[0]["also_for"] == ["a"]


def test_monte_carlo_share_counts_runs_where_a_zone_reaches_the_sample_top_decile():
    from discovery.discover import top_decile_share
    rng = np.random.default_rng(0)
    sample = [rng.normal(0.3, 0.1, 1000) for _ in range(20)]        # sampled cell medians per run
    strong = [np.array([0.9]) for _ in range(20)]
    weak = [np.array([0.3]) for _ in range(20)]
    assert top_decile_share(strong, sample) == 1.0 and top_decile_share(weak, sample) == 0.0


def test_tile_rows_are_written_with_the_fixed_schema_and_missing_columns_are_null(tmp_path):
    import pyarrow.parquet as pq
    from discovery.discover import CELL_SCHEMA, write_rows
    rows = [{"cell": "t:0:0", "tile": "1,2", "lat": 1.5, "lon": 2.5, "moon-psr:median": 0.7, "req:base_slope": "met"},
            {"cell": "t:0:1", "tile": "1,2", "lat": 1.5, "lon": 2.6, "moon-psr:screened_out": True}]
    f = tmp_path / "a.parquet"
    assert write_rows(f, rows) == 2
    t = pq.read_table(f)
    assert t.schema.equals(CELL_SCHEMA)
    assert t.column("moon-psr:median").to_pylist() == [0.7, None]
    assert t.column("moon-mare-plains:median").to_pylist() == [None, None]


def test_a_tile_is_read_only_at_the_scales_where_this_run_refined_it(tmp_path):
    from discovery.discover import refined_scales
    a, b = tmp_path / "tiles-refine-glo30-40m.txt", tmp_path / "tiles-refine-glo30-59m.txt"
    a.write_text("1,2\n3,4\n")
    b.write_text("3,4\n")
    by_tile = refined_scales([str(a), str(b)])
    assert by_tile == {"1,2": ["glo30-40m"], "3,4": ["glo30-40m", "glo30-59m"]}


def test_numeric_columns_are_used_as_they_are_and_object_columns_get_nan_for_null():
    from discovery.discover import _num
    f = np.array([1.0, np.nan])
    assert _num(f) is f
    assert np.isnan(_num(np.array([None, 2.0], dtype=object))[0]) and _num([None, 3])[1] == 3.0


def test_light_zone_counts_equal_the_full_zone_computation():
    from discovery.discover import zone_counts, zones_for
    rng = np.random.default_rng(5)
    n = 3000
    from discovery.discover import cell_centre, global_cell
    ids = np.unique(global_cell(np.concatenate([rng.uniform(10, 10.5, n), [40.0]]),
                                np.concatenate([rng.uniform(20, 20.5, n), [40.0]])))
    lat, lon = cell_centre(ids)
    n = ids.size - 1
    cells = {"cell": ids.astype(str), "tile": np.array(["10,20"] * (n + 1)),
             "lat": lat, "lon": lon, "area_km2": np.full(n + 1, 25.0), "masked_share": rng.uniform(0, 0.7, n + 1),
             "confidence": rng.choice(["high", "medium"], n + 1), "moon-psr:median": rng.uniform(0, 1, n + 1)}
    for tau in (0.5, 0.7, 0.9):
        counts = zone_counts(cells, "A", "moon-psr", tau, (1, 3, 9))
        for mc in (1, 3, 9):
            full = zones_for(cells, "A", "moon-psr", tau, mc)
            assert counts[mc] == {"zones": len(full), "area_km2": round(sum(z["area_km2"] for z in full), 1)}


def test_global_cells_join_windows_across_a_tile_edge_and_have_one_owner_tile():
    """Protocol v3: one HEALPix cell, not two parts cut by the 1° tile edge."""
    from discovery.discover import cell_centre, global_cell, owner_tile
    from discovery.healpix import NSIDE, ang2pix, pix2ang
    c0 = ang2pix(NSIDE, 10.5, 20.0)                                          # the cell holding the point 10.5°N 20°E
    clat, clon = pix2ang(NSIDE, c0)
    lat = np.full(2, clat[0])
    lon = clon[0] + np.array([-0.015, 0.015])                                # 3 km apart, inside that 5 km cell
    c = global_cell(lat, lon)
    assert c[0] == c[1] == c0[0]
    blat, blon = cell_centre(c[:1])
    assert abs(blat[0] - 10.5) < 0.05 and abs(blon[0] - 20.0) < 0.05
    assert owner_tile(blat, blon)[0] in ("10,19", "10,20")
    assert global_cell(np.array([10.5]), np.array([20.2]))[0] != c[0]


def test_global_cells_keep_their_shape_near_the_poles():
    """Windows 1 km apart near 80°S stay in compact cells: no cell spans more than about 10 km."""
    from discovery.discover import cell_centre, global_cell
    lat, lon = np.meshgrid(np.linspace(-80.2, -79.8, 45), np.linspace(10, 12.3, 45), indexing="ij")
    c = global_cell(lat.ravel(), lon.ravel())
    span = []
    for k in np.unique(c):
        m = c == k
        km_n = (lat.ravel()[m].max() - lat.ravel()[m].min()) * 111.2
        km_e = (lon.ravel()[m].max() - lon.ravel()[m].min()) * 111.2 * np.cos(np.radians(80))
        span.append(max(km_n, km_e))
    assert max(span) < 10.0


def test_protocol_v3_candidates_must_have_high_confidence():
    med = np.array([0.8, 0.8, 0.8])
    conf = np.array(["high", "medium", "low"], dtype=object)
    out = candidates(med, np.zeros(3, bool), np.zeros(3), 0.5, confidence=conf)
    assert out.tolist() == [True, False, False]
    assert candidates(med, np.zeros(3, bool), np.zeros(3), 0.5).tolist() == [True, True, True]   # v2 behaviour kept


def _cube(tmp_path, tiles):
    """Synthetic 40 m cube: windows on a 1 km grid, each tile holding the windows inside its 1° square."""
    import json
    import pyarrow as pa
    import pyarrow.parquet as pq
    from discovery.compare import MASK_CLASSES
    from discovery.copernicus import tile_name
    rng = np.random.default_rng(7)
    (tmp_path / "glo30-40m").mkdir()
    lat, lon = np.meshgrid(np.arange(10.40, 10.60, 0.009), np.arange(19.90, 20.10, 0.009), indexing="ij")
    lat, lon = lat.ravel(), lon.ravel()
    for key in tiles:
        la, lo = (int(v) for v in key.split(","))
        m = (np.floor(lat) == la) & (np.floor(lon) == lo)
        n = int(m.sum())
        cols = {"i": np.arange(n), "j": np.zeros(n, int), "lat": lat[m], "lon": lon[m],
                "slope_mean": rng.uniform(0, 20, n), "traversable_15": rng.uniform(0, 1, n),
                "traversable_20": rng.uniform(0, 1, n), "wc_covered": np.ones(n)}
        cols.update({c: np.zeros(n) for c in MASK_CLASSES})
        pq.write_table(pa.table(cols), tmp_path / "glo30-40m" / f"{tile_name(la, lo, 'glo30')}.windows.parquet")
    from discovery.discover import TARGET_SCALE
    np.savez(tmp_path / "refs.npz", **{t: np.sort(rng.uniform(0, 20, 500)) for t in TARGET_SCALE})
    np.save(tmp_path / "rock.npy", np.zeros((2, 2), "uint8"))
    (tmp_path / "rock.json").write_text(json.dumps({"transform": [1, 0, 0, 0, -1, 0]}))
    return lat, lon


def test_v3_assessment_gives_each_global_cell_once_with_its_windows_from_both_sides_of_a_tile_edge(tmp_path):
    import discovery.discover as d
    from discovery.healpix import NSIDE, ang2pix
    lat, lon = _cube(tmp_path, ["10,19", "10,20"])
    d._CTX.clear()
    refined = {"10,19": ["glo30-40m"], "10,20": ["glo30-40m"]}
    rows = []
    for key in ("10,19", "10,20"):
        rows += d.assess_tile(key, str(tmp_path), str(tmp_path / "refs.npz"), str(tmp_path / "rock"),
                              {k: v for k, v in refined.items() if k in d.neighbour_keys(key)})
    ids = [r["cell"] for r in rows]
    assert len(ids) == len(set(ids))                                         # one owner per cell
    cell = ang2pix(NSIDE, lat, lon)
    edge = np.unique(cell[lon < 20])[np.isin(np.unique(cell[lon < 20]), cell[lon >= 20])]
    assert edge.size > 0                                                      # cells that straddle 20°E
    by = {r["cell"]: r for r in rows}
    inner = (lat > 10.45) & (lat < 10.55)
    checked = 0
    for c in edge:
        if not inner[cell == c].all():
            continue                                                          # cells cut by the synthetic area itself
        r = by[str(c)]
        assert r["windows"] == int((cell == c).sum())                         # windows of both tiles
        assert r["moon-psr:windows"] == r["windows"]
        assert abs(r["area_km2"] - 25.035) < 0.01
        checked += 1
    assert checked >= 1


def test_tiles_next_to_refined_tiles_own_cells_too():
    import discovery.discover as d
    keys = d.assessed_keys({"10,20": ["glo30-40m"]})
    assert {"9,19", "10,19", "11,21", "10,20"} <= set(keys) and len(keys) == 9
    assert "80,0" in d.neighbour_keys("80,1") and "80,4" not in d.neighbour_keys("80,1")
    assert len(d.assessed_keys({"89,0": ["glo30-40m"]})) > 9                 # near the pole a cell spans many tiles


def test_window_tiles_hold_every_point_of_the_cells():
    """The tiles to recompute for a cell (checks.py): every point of the cell lies in one of them."""
    from discovery.discover import global_cell, window_tiles
    from discovery.healpix import NSIDE, ang2pix, pix2ang
    rng = np.random.default_rng(9)
    for lat0, lon0 in ((10.0, 20.0), (-79.99, 0.0), (45.5, 179.99), (88.7, 33.0)):
        c = ang2pix(NSIDE, lat0, lon0)
        la, lo = pix2ang(NSIDE, c)
        plat = la[0] + rng.uniform(-0.1, 0.1, 20000)
        plon = lo[0] + rng.uniform(-1, 1, 20000) * min(180, 0.1 / np.cos(np.radians(min(89.9, abs(la[0]) + 0.1))))
        plat = np.clip(plat, -89.999, 89.999)
        inside = global_cell(plat, plon) == c[0]
        assert inside.sum() > 50
        tiles = {f"{int(np.floor(a))},{int(np.floor((b + 180) % 360 - 180))}" for a, b in zip(plat[inside], plon[inside])}
        assert tiles <= set(window_tiles([str(c[0])])), (lat0, lon0)
