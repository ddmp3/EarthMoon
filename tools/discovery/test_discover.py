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
    lat = np.concatenate([rng.uniform(10, 11, n), [40.0]])
    lon = np.concatenate([rng.uniform(20, 21, n), [40.0]])
    cells = {"cell": np.array([f"c{i}" for i in range(n + 1)]), "tile": np.array(["10,20"] * (n + 1)),
             "lat": lat, "lon": lon, "area_km2": np.full(n + 1, 25.0), "masked_share": rng.uniform(0, 0.7, n + 1),
             "confidence": np.array(["high"] * (n + 1)), "moon-psr:median": rng.uniform(0, 1, n + 1)}
    for tau in (0.5, 0.7, 0.9):
        counts = zone_counts(cells, "A", "moon-psr", tau, (1, 3, 9))
        for mc in (1, 3, 9):
            full = zones_for(cells, "A", "moon-psr", tau, mc)
            assert counts[mc] == {"zones": len(full), "area_km2": round(sum(z["area_km2"] for z in full), 1)}
