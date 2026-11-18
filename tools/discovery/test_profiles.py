"""Planetary profiles (T41): window selection, distributions, the v2 lunar anchor."""
import json
import os
from pathlib import Path

import numpy as np
import pytest

from discovery.profiles import PERCENTILES, select_windows, summarise

ROOT = Path(__file__).resolve().parents[2]
LDEM = Path(os.environ.get("EARTHMOON_DATA", "/data")) / "lola" / "ldem_85s_40m.img"


def test_a_window_is_selected_only_when_all_its_pixels_are_inside_the_mask():
    mask = np.ones((10, 10), bool)
    mask[0, 9] = False                         # one pixel out: window (0, 1) of 5 px is dropped
    sel = select_windows(mask, 5)
    assert sel.tolist() == [[True, False], [True, True]]


def test_summary_gives_counts_and_numpy_percentiles_and_skips_invalid_windows():
    v = np.arange(100, dtype=float)
    v[:10] = np.nan                             # 10 invalid windows (below 90% valid pixels)
    out = summarise({"slope_mean": v}, np.ones(100, bool), ("slope_mean",))
    assert out["windows"] == {"selected": 100, "valid": 90}
    ref = np.percentile(np.arange(10, 100, dtype=float), PERCENTILES)
    assert [out["metrics"]["slope_mean"][f"p{p}"] for p in PERCENTILES] == pytest.approx(ref)
    assert out["metrics"]["slope_mean"]["n"] == 90


def test_summary_of_an_empty_selection_has_no_percentiles():
    out = summarise({"slope_mean": np.ones(4)}, np.zeros(4, bool), ("slope_mean",))
    assert out["windows"]["selected"] == 0 and out["metrics"]["slope_mean"]["p50"] is None


def test_committed_south_polar_cap_reproduces_the_v2_percentiles():
    v2 = json.loads((ROOT / "data/reference/moon-south-pole.json").read_text(encoding="utf-8"))["terrain_v2"]
    v3 = json.loads((ROOT / "data/profiles/moon/moon-south-polar-cap-v2.json").read_text(encoding="utf-8"))
    assert v3["windows"]["selected"] == v2["windows"] == 71731
    assert v3["inputs"]["lro-lola-ldem-85s-40m"]["sha256"] == v2["file_sha256"]
    for k, p in v2["params"].items():
        for q, value in p["distribution"].items():
            assert v3["metrics"][k][q] == pytest.approx(value, abs=0.01), (k, q)


@pytest.mark.skipif(not LDEM.exists(), reason="LDEM_85S_40M not present (data folder)")
def test_south_polar_cap_recomputed_from_ldem_matches_the_committed_profile():
    from discovery.profiles import south_polar_cap
    out = south_polar_cap(LDEM)
    v3 = json.loads((ROOT / "data/profiles/moon/moon-south-polar-cap-v2.json").read_text(encoding="utf-8"))
    assert out["metrics"] == v3["metrics"] and out["windows"] == v3["windows"]


def test_window_fraction_is_the_mean_of_a_pixel_mask_and_nan_where_unknown():
    from discovery.profiles import window_fraction
    m = np.zeros((4, 4))
    m[:2, :2] = 1.0
    m[3, 3] = np.nan
    out = window_fraction(m, 2)
    assert out[0, 0] == 1.0 and out[0, 1] == 0.0 and out[1, 1] == pytest.approx(0.0)
    assert np.isnan(window_fraction(np.full((2, 2), np.nan), 2)[0, 0])


def test_threshold_selection_keeps_windows_on_the_right_side_and_never_unknown_ones():
    from discovery.profiles import threshold
    frac = np.array([[0.0, 0.05, 0.5], [0.9, np.nan, 1.0]])
    assert threshold(frac, at_most=0.05).tolist() == [[True, True, False], [False, False, False]]
    assert threshold(frac, at_least=0.75).tolist() == [[False, False, False], [True, False, True]]


def test_connected_areas_above_q_drop_isolated_pixels_below_min_pixels():
    from discovery.profiles import lit_areas
    ill = np.zeros((6, 6))
    ill[0:3, 0:3] = 0.8                          # a 9-pixel area
    ill[5, 5] = 0.9                               # one isolated pixel
    out = lit_areas(ill, q=0.6, min_pixels=2)
    assert out[:3, :3].all() and not out[5, 5] and out.sum() == 9


def _profile(name):
    return json.loads((ROOT / f"data/profiles/moon/{name}.json").read_text(encoding="utf-8"))


def test_polar_profiles_are_subsets_of_the_cap_and_thresholds_act_monotonically():
    cap = _profile("moon-south-polar-cap-v2")["windows"]["selected"]
    lit, psr = _profile("moon-polar-lit-highlands"), _profile("moon-psr")
    assert 0 < psr["windows"]["selected"] < lit["windows"]["selected"] < cap
    km = lambda p, k: [s["selected"] for s in p["sensitivity"] if s["window_m"] == 1000.0 and k in s]
    assert km(lit, "f_lit") == sorted(km(lit, "f_lit"))                 # looser shadow limit, more windows
    assert km(psr, "f_psr") == sorted(km(psr, "f_psr"), reverse=True)   # stricter shadow limit, fewer windows
    assert lit["params"]["f_lit"] == 0.05 and psr["params"]["f_psr"] == 0.75
    for p in (lit, psr):
        assert p["inputs"]["lro-lola-ldem-85s-40m"]["sha256"] == _profile("moon-south-polar-cap-v2")["inputs"]["lro-lola-ldem-85s-40m"]["sha256"]


PSR = LDEM.parent / "pgda" / "LPSR_85S_060M_201608.TIF"


@pytest.mark.skipif(not (LDEM.exists() and PSR.exists()), reason="LDEM or PSR map not present (data folder)")
def test_psr_map_is_read_in_the_ldem_orientation_shadow_lies_in_topographic_lows():
    import sys
    sys.path.insert(0, str(ROOT / "tools" / "precompute"))
    from lunar_reference import read_ldem
    from discovery.profiles import read_polar
    from discovery.resolution import gaussian_smooth
    z = read_ldem(str(LDEM), 7584).astype("float64")[::4, ::4]
    rel = z - gaussian_smooth(z, 25)
    p = read_polar(PSR, 7584, 40.0, psr=True)[::4, ::4]
    as_read = np.nanmedian(rel[p == 1])
    flipped = [np.nanmedian(rel[f(p) == 1]) for f in (np.flipud, np.fliplr, lambda a: a.T)]
    assert as_read < -100 and all(as_read < 3 * f for f in flipped)     # measured: -215 m against -18 to -39 m


PITS_HTML = """<table><tr><th>Host Feat.</th><th>Name</th><th>Lat.</th><th>Long.</th><th>Funnel Max Diam. (m)</th>
<th>Funnel Min Diam. (m)</th><th>Inner Max Diam. (m)</th><th>Inner Max Diam. Sorting</th><th>Inner Min Diam. (m)</th>
<th>Inner Min Diam. Sorting</th><th>Azimuth</th><th>Depth (m)</th><th>Depth Sorting</th></tr>
<tr><td>Mare Tranquillitatis</td><td><a href="/atlases/pits/3">Mare Tranquillitatis Pit</a></td><td>8.3355</td>
<td>33.222</td><td>140</td><td>100</td><td>88</td><td>88</td><td>N/A</td><td></td><td>170</td><td>105.0</td><td>105.0</td></tr>
<tr><td>Aristarchus</td><td><a href="/atlases/pits/33">Aristarchus 5</a></td><td>23.5984</td><td>312.4196</td>
<td>16</td><td>21</td><td>7</td><td>7</td><td>N/A</td><td></td><td>75</td><td>&gt;17.0</td><td>17.0</td></tr></table>"""


def test_pits_atlas_rows_are_parsed_with_lower_bounds_marked_and_east_longitudes():
    from discovery.profiles import parse_pits
    pits = parse_pits(PITS_HTML)
    assert [p["id"] for p in pits] == [3, 33]
    assert pits[0] == {"id": 3, "name": "Mare Tranquillitatis Pit", "host": "Mare Tranquillitatis", "lat": 8.3355,
                       "lon": 33.222, "funnel_max_m": 140.0, "funnel_min_m": 100.0, "inner_max_m": 88.0,
                       "inner_min_m": None, "azimuth": 170.0, "depth_m": 105.0, "depth_is_lower_bound": False}
    assert pits[1]["depth_m"] == 17.0 and pits[1]["depth_is_lower_bound"] and pits[1]["lon"] == 312.4196
