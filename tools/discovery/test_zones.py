"""Candidate zones (T26 rule, T43). Synthetic cells only."""
import numpy as np

from discovery.zones import connect, zone_table

KM = 1 / 111.2                                                     # degrees of latitude per km


def _block(lat0, lon0, n):
    lat = np.repeat(lat0 + np.arange(n) * 5 * KM, n)
    lon = np.tile(lon0 + np.arange(n) * 5 * KM / np.cos(np.radians(lat0)), n)
    return lat, lon


def test_eight_neighbour_cells_join_and_isolated_cells_stay_apart():
    la, lo = _block(10.0, 20.0, 3)                                   # 9 touching cells
    lat = np.concatenate([la, [10.5]])                               # one cell 50 km away
    lon = np.concatenate([lo, [20.0]])
    lab = connect(lat, lon)
    assert len(set(lab[:9])) == 1 and lab[9] != lab[0]


def test_cells_join_across_the_antimeridian_and_near_the_pole():
    lab = connect(np.array([-16.0, -16.0]), np.array([179.98, -179.98]))
    assert lab[0] == lab[1]
    lab = connect(np.array([89.98, 89.98]), np.array([0.0, 180.0]))   # 4.4 km apart across the pole
    assert lab[0] == lab[1]


def test_zone_table_drops_zones_below_the_minimum_and_reports_area_and_centre():
    la, lo = _block(-30.0, 120.0, 2)                                 # 4 cells
    lat = np.concatenate([la, [-29.0]])
    lon = np.concatenate([lo, [121.0]])
    z = zone_table(lat, lon, area_km2=np.full(5, 25.0), min_cells=3)
    assert len(z) == 1 and z[0]["cells"] == 4 and z[0]["area_km2"] == 100.0
    assert abs(z[0]["lat"] - (-30.0 + 2.5 * KM)) < 1e-4          # spherical centre: within 11 m


def _same_partition(a, b):
    return len(set(zip(a.tolist(), b.tolist()))) == len(set(a.tolist())) == len(set(b.tolist()))


def test_vectorised_connection_gives_the_same_zones_as_the_reference_on_random_cells():
    from discovery.zones import connect_reference
    rng = np.random.default_rng(3)
    lat = np.concatenate([rng.uniform(-80, 80, 1500), 89.99 - rng.uniform(0, 0.08, 50)])
    lon = np.concatenate([rng.uniform(-180, 180, 1500), rng.uniform(-180, 180, 50)])
    lat = np.concatenate([lat, lat[:300] + rng.normal(0, 0.03, 300)])          # close pairs, so zones exist
    lon = np.concatenate([lon, lon[:300] + rng.normal(0, 0.03, 300)])
    fast, ref = connect(lat, lon), connect_reference(lat, lon)
    assert _same_partition(fast, ref) and len(set(fast.tolist())) < lat.size


def test_a_large_continuous_block_is_one_zone_and_converges_fast():
    import time
    n = 400                                                            # 160,000 cells, 2,000 km across
    lat = np.repeat(np.arange(n) * 5 * KM, n)
    lon = np.tile(np.arange(n) * 5 * KM, n)
    t = time.time()
    lab = connect(lat, lon)
    assert len(set(lab.tolist())) == 1 and time.time() - t < 20
