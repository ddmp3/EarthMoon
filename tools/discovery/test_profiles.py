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
