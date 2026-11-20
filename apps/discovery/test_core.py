"""Internal discovery service (T44, ADR-005): cells in view and custom queries over a release. Synthetic release."""
import sys
from pathlib import Path

import numpy as np
import pyarrow as pa
import pyarrow.parquet as pq
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "tools"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from core import CELL_CAP, QueryError, Release, cells_at, cells_in_bbox, run_query  # noqa: E402
from discovery.healpix import NSIDE, ang2pix  # noqa: E402


@pytest.fixture()
def release(tmp_path):
    rng = np.random.default_rng(1)
    lat, lon = np.meshgrid(np.linspace(10.02, 10.98, 25), np.linspace(20.02, 20.98, 25), indexing="ij")
    ids = np.unique(ang2pix(NSIDE, lat.ravel(), lon.ravel()))
    n = ids.size
    t = "moon-psr"
    cols = {"cell": ids.astype(str), "windows": np.full(n, 25.0), "valid_unmasked": np.full(n, 24.0),
            "masked_share": np.zeros(n), "cover_unknown": np.zeros(n),
            "confidence": np.where(np.arange(n) % 3 == 0, "medium", "high"),
            f"{t}:windows": np.full(n, 25.0), f"{t}:valid": np.full(n, 24.0),
            f"{t}:median": rng.uniform(0, 1, n), f"{t}:p25": np.full(n, 0.1), f"{t}:p75": np.full(n, 0.9),
            f"{t}:screened_out": pa.array([None] * n, pa.bool_()),
            "req:climbing_limit_lrv": np.where(np.arange(n) % 2 == 0, "met", "failed"),
            "req:base_slope": np.full(n, "met"), "req:climbing_limit_viper": np.full(n, "unknown")}
    d = tmp_path / "r-00000000"
    d.mkdir()
    pq.write_table(pa.table(cols), d / "cells.parquet")
    (d / "release.json").write_text('{"release": "r-00000000", "methodology_version": "v3"}')
    return Release(d, targets=[t])


def test_cells_in_view_are_polygons_with_their_spread_state_and_coverage(release):
    fc = cells_in_bbox(release, (20.2, 10.2, 20.4, 10.4), "moon-psr")
    assert fc["type"] == "FeatureCollection" and fc["release"] == "r-00000000" and fc["methodology_version"] == "v3"
    f = fc["features"][0]
    ring = f["geometry"]["coordinates"][0]
    assert f["geometry"]["type"] == "Polygon" and len(ring) == 5 and ring[0] == ring[-1]
    p = f["properties"]
    assert set(p["typicality"]) == {"median", "p25", "p75"} and p["coverage"] in ("evaluated", "low_confidence")
    assert p["windows"] == {"valid": 24, "total": 25} and p["confidence"] in ("high", "medium")
    lats = [x["properties"]["lat"] for x in fc["features"]]
    assert min(lats) >= 10.15 and max(lats) <= 10.45


def test_a_view_with_too_many_cells_is_refused_with_a_reason(release, monkeypatch):
    import core
    monkeypatch.setattr(core, "CELL_CAP", 10)
    with pytest.raises(QueryError, match="zoom in"):
        cells_in_bbox(release, (20.0, 10.0, 21.0, 11.0), "moon-psr")
    assert CELL_CAP == 5000


def test_query_filters_on_typicality_confidence_and_requirements(release):
    out = run_query(release, {"env": "moon-psr", "min_typicality": 0.5, "min_confidence": "high",
                              "requirements_met": ["climbing_limit_lrv"], "limit": 500})
    med = release.col("moon-psr:median")
    conf = release.col("confidence")
    req = release.col("req:climbing_limit_lrv")
    expect = int(((med >= 0.5) & (conf == "high") & (req == "met")).sum())
    assert out["matched"] == expect and len(out["cells"]) == expect
    assert all(c["typicality"] >= 0.5 for c in out["cells"])
    assert out["cells"] == sorted(out["cells"], key=lambda c: -c["typicality"])
    assert out["area_km2"] == pytest.approx(expect * 25.04, rel=1e-3)


@pytest.mark.parametrize("bad, why", [
    ({"env": "moon-nowhere"}, "env"),
    ({"env": "moon-psr", "min_typicality": 1.5}, "min_typicality"),
    ({"env": "moon-psr", "min_confidence": "very"}, "min_confidence"),
    ({"env": "moon-psr", "requirements_met": ["fly"]}, "requirement"),
    ({"env": "moon-psr", "limit": 10_000}, "limit"),
    ({"env": "moon-psr", "bbox": [0, 0, 400, 1]}, "bbox"),
    ({"env": "moon-psr", "colour": "red"}, "unknown field"),
])
def test_query_rejects_invalid_input_with_the_reason(release, bad, why):
    with pytest.raises(QueryError, match=why):
        run_query(release, bad)


def test_query_area_is_limited_to_one_million_cells(release, monkeypatch):
    import core
    monkeypatch.setattr(core, "QUERY_CELL_CAP", 5)
    with pytest.raises(QueryError, match="1,000,000 cells|cells at most"):
        run_query(release, {"env": "moon-psr"})


def test_columns_are_compact_arrays_once_loaded_so_a_request_never_walks_millions_of_python_objects(release):
    for name in ("windows", "valid_unmasked", "masked_share", "moon-psr:median", "moon-psr:p25", "moon-psr:windows",
                 "moon-psr:screened_out"):
        assert release.col(name).dtype.kind == "f", name                   # booleans with nulls: 1, 0, NaN
    for name in ("confidence", "req:climbing_limit_lrv"):
        assert release.col(name).dtype.kind == "U", name                   # text: fixed-width, '' for missing


def test_a_missing_text_value_is_returned_as_null_not_as_an_empty_string(tmp_path):
    n = 3
    ids = np.unique(ang2pix(NSIDE, np.array([10.1, 10.2, 10.3]), np.array([20.1, 20.1, 20.1])))
    n = ids.size
    cols = {"cell": ids.astype(str), "windows": np.full(n, 25.0), "valid_unmasked": np.full(n, 24.0),
            "masked_share": np.zeros(n), "cover_unknown": np.zeros(n),
            "confidence": pa.array([None] + ["high"] * (n - 1), pa.string()),
            "moon-psr:windows": np.full(n, 25.0), "moon-psr:valid": np.full(n, 24.0), "moon-psr:median": np.full(n, 0.5),
            "moon-psr:p25": np.full(n, 0.4), "moon-psr:p75": np.full(n, 0.6),
            "moon-psr:screened_out": pa.array([None] * n, pa.bool_()),
            "req:climbing_limit_lrv": pa.array([None] * n, pa.string()), "req:base_slope": np.full(n, "met"),
            "req:climbing_limit_viper": np.full(n, "unknown")}
    d = tmp_path / "r-11111111"
    d.mkdir()
    pq.write_table(pa.table(cols), d / "cells.parquet")
    (d / "release.json").write_text('{"release": "r-11111111", "methodology_version": "v3"}')
    rel = Release(d, targets=["moon-psr"])
    props = [f["properties"] for f in cells_in_bbox(rel, (20.0, 10.0, 20.2, 10.4), "moon-psr")["features"]]
    assert any(p["confidence"] is None for p in props)
    assert all(p["requirements"]["climbing_limit_lrv"] is None for p in props)
    out = run_query(rel, {"env": "moon-psr", "min_confidence": "medium"})
    assert out["matched"] == n - 1                                          # the cell without a confidence is not counted


def test_the_service_loads_the_current_release_at_start_up(tmp_path, release, monkeypatch):
    import json as _json
    import app as service
    root = release.folder.parent
    (root / "index.json").write_text(_json.dumps({"current": "r-00000000", "releases": [{"id": "r-00000000"}]}))
    (release.folder / "scenarios.json").write_text(_json.dumps({"scenarios": [{"assessed_targets": ["moon-psr"]}]}))
    monkeypatch.setattr(service, "ROOT", root)
    service._RELEASES.clear()
    service.preload()
    assert list(service._RELEASES) == ["r-00000000"]


def test_values_at_named_points_give_the_cell_of_each_point_or_say_it_was_not_assessed(release):
    pts = [{"id": "inside", "lat": 10.5, "lon": 20.5}, {"id": "sea", "lat": -40.0, "lon": -30.0}]
    out = cells_at(release, pts, ["moon-psr"])
    assert out["release"] == "r-00000000" and out["methodology_version"] == "v3"
    by = {p["id"]: p for p in out["points"]}
    v = by["inside"]["values"]["moon-psr"]
    assert by["inside"]["cell"] == str(int(np.asarray(ang2pix(NSIDE, np.array([10.5]), np.array([20.5]))).ravel()[0]))
    assert set(v["typicality"]) == {"median", "p25", "p75"} and v["coverage"] in ("evaluated", "low_confidence")
    assert by["sea"]["cell"] is None and by["sea"]["values"] is None
    assert "not assessed" in by["sea"]["reason"]


@pytest.mark.parametrize("bad, why", [
    ([{"id": "x", "lat": 95, "lon": 0}], "lat"),
    ([{"id": "x", "lat": 0}], "lon"),
    ([{"id": "x", "lat": 0, "lon": 0}] * 101, "100 points"),
])
def test_points_are_checked(release, bad, why):
    with pytest.raises(QueryError, match=why):
        cells_at(release, bad, ["moon-psr"])
