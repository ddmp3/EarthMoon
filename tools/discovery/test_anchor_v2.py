"""Regression anchor: the v3 window code gives the v2 terrain values of the 37 sites from the same grids (T40)."""
import json

import numpy as np
import pytest

from discovery.anchor_v2 import DATASET, FIXTURE, recompute
from discovery.windows import ALL_METRICS

pytestmark = pytest.mark.skipif(not FIXTURE.exists(), reason="fixture not built (python tools/discovery/anchor_v2.py build)")


def test_v3_windows_reproduce_every_v2_terrain_value_and_sigma():
    sites = json.loads(DATASET.read_text(encoding="utf-8"))["sites"]
    grids = np.load(FIXTURE)
    assert sorted(grids.files) == sorted(sites)
    diffs = []
    for sid, site in sites.items():
        got = recompute(grids[sid])
        for k in ALL_METRICS:
            ref = site["values"][k]
            for field in ("value", "sigma"):
                a, b = ref[field], got[k][field]
                if a is None or b is None:
                    assert a == b, (sid, k, field, a, b)
                else:
                    diffs.append(abs(a - b))
                    assert b == pytest.approx(a, abs=0.0015), (sid, k, field, a, b)
    assert len(diffs) == 37 * len(ALL_METRICS) * 2
