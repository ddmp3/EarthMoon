"""Synthetic release for the Docker end-to-end test (T44). TEST DATA, NOT A RESULT.

It is written by the real exporter (release.py, tiles.py) from synthetic cells, so the e2e test runs the same
code path as a real release. Its run is named "synthetic-fixture" in every file, and its values are random.

    PYTHONPATH=tools python tools/discovery/fixture_release.py --out data/releases-fixture
"""
from __future__ import annotations

import argparse
import json
import shutil
import sys
import tempfile
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

SEED = 20261119


def build(out: Path) -> str:
    import pyarrow as pa
    import pyarrow.parquet as pq
    from discovery.discover import CELL_SCHEMA, SCENARIO_TARGETS, TARGET_SCALE, cell_centre, global_cell, write_rows
    from discovery.release import export
    from discovery.tiles import render_release
    rng = np.random.default_rng(SEED)
    lat, lon = np.meshgrid(np.arange(20.01, 21.0, 0.03), np.arange(10.01, 11.0, 0.03), indexing="ij")
    ids = np.unique(global_cell(lat.ravel(), lon.ravel()))
    clat, clon = cell_centre(ids)
    rows = []
    for k, c in enumerate(ids.tolist()):
        valid = int(rng.integers(5, 26))
        masked = 25 - valid if k % 7 == 0 else 0
        r = {"cell": str(c), "tile": f"{int(np.floor(clat[k]))},{int(np.floor(clon[k]))}", "lat": float(clat[k]),
             "lon": float(clon[k]), "area_km2": 25.035, "windows": 25, "valid_unmasked": valid, "masked": masked,
             "cover_unknown": 0, "masked_share": masked / 25, "assessed_at": "glo30-40m",
             "confidence": "high" if valid >= 20 and masked < 3 else ("medium" if valid >= 10 else "low"),
             "suitability_A": float(rng.uniform()), "suitability_B": float(rng.uniform()),
             "req:base_slope": "met", "req:climbing_limit_lrv": "met" if k % 3 else "failed", "req:climbing_limit_viper": "unknown"}
        for t in TARGET_SCALE:
            m = float(np.clip(0.5 + 0.4 * np.sin(clat[k] * 9) * np.cos(clon[k] * 7) + rng.normal(0, 0.05), 0, 1))
            r.update({f"{t}:windows": 25, f"{t}:valid": valid, f"{t}:median": m, f"{t}:p25": max(0.0, m - 0.15),
                      f"{t}:p75": min(1.0, m + 0.15), f"{t}:share_above_half": float(m > 0.5)})
        rows.append(r)
    with tempfile.TemporaryDirectory() as tmp:
        run, cube = Path(tmp) / "synthetic-fixture", Path(tmp) / "cube"
        run.mkdir()
        (cube / "glo90-90m").mkdir(parents=True)
        write_rows(run / "cells.parquet", rows)
        assert pq.read_schema(run / "cells.parquet").equals(CELL_SCHEMA)
        land = {"lat": lat.ravel(), "lon": lon.ravel()}                       # one synthetic 1 km window per point
        pq.write_table(pa.table(land), cube / "glo90-90m" / "fixture.windows.parquet")
        (run / "validation.json").write_text(json.dumps({"note": "synthetic fixture: no validation was run"}))
        np.save(run / "land-cells.npy", ids)
        if out.exists():
            shutil.rmtree(out)
        rid = export(run, cube, out, commit="synthetic-fixture")
        render_release(run, out / rid, run / "land-cells.npy", workers=1)
    assert SCENARIO_TARGETS
    return rid


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", type=Path, required=True)
    print(build(ap.parse_args(argv).out))
    return 0


if __name__ == "__main__":
    sys.exit(main())
