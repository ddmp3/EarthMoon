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
