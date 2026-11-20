"""Cells in view and custom queries over the cells of a release (T44, ADR-003, ADR-005).

The service reads the release's cells.parquet once at start-up and never writes. A request never reaches an
external source: it filters precomputed cells. Every answer carries the release and the methodology version.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "tools"))
from discovery.healpix import NSIDE, cell_area_km2, corners, pix2ang  # noqa: E402
from discovery.release import coverage_class  # noqa: E402

CELL_CAP = 5000                       # cells in one view (ADR-004)
QUERY_CELL_CAP = 1_000_000            # cells in the area of one query (ADR-003)
MAX_RETURNED = 500
CONFIDENCE_RANK = {"low": 0, "medium": 1, "high": 2}
REQUIREMENTS = ("base_slope", "climbing_limit_lrv", "climbing_limit_viper")
QUERY_FIELDS = {"env", "min_typicality", "min_confidence", "requirements_met", "bbox", "limit"}


class QueryError(ValueError):
    """Invalid or too large request: the message says why."""


class Release:
    def __init__(self, folder: Path, targets: list[str]):
        import pyarrow.parquet as pq
        self.folder = Path(folder)
        head = json.loads((self.folder / "release.json").read_text(encoding="utf-8"))
        self.head = {"release": head["release"], "methodology_version": head["methodology_version"]}
        self.targets = list(targets)
        import pyarrow as pa
        import pyarrow.compute as pc
        need = {"cell", "windows", "valid_unmasked", "masked_share", "cover_unknown", "confidence"}
        need |= {f"req:{r}" for r in REQUIREMENTS}
        need |= {f"{t}:{k}" for t in self.targets for k in ("windows", "valid", "screened_out", "median", "p25", "p75")}
        names = pq.read_schema(self.folder / "cells.parquet").names
        t = pq.read_table(self.folder / "cells.parquet", columns=[n for n in names if n in need])
        ids = np.asarray(t.column("cell").to_numpy(zero_copy_only=False)).astype(np.int64)
        order = np.argsort(ids)
        self._cols = {}
        for k in t.column_names:                     # compact arrays: 6 M Python objects per column took 8 GB
            if k == "cell":
                continue
            col = t.column(k)
            if pa.types.is_string(col.type) or pa.types.is_large_string(col.type):
                enc = pc.dictionary_encode(pc.fill_null(col, "")).combine_chunks()   # no Python object per cell
                a = np.asarray(enc.dictionary.to_pylist(), dtype=str)[enc.indices.to_numpy(zero_copy_only=False)]
            else:
                a = col.cast(pa.float32()).to_numpy(zero_copy_only=False).astype(np.float32)   # null -> NaN
            self._cols[k] = a[order]
        self.ids = ids[order]
        self._cols["cell"] = self.ids.astype(str)
        del t
        pa.default_memory_pool().release_unused()
        self.lat, self.lon = pix2ang(NSIDE, self.ids)

    def col(self, name: str) -> np.ndarray:
        if name not in self._cols:
            return np.full(self.ids.size, None, dtype=object)
        return self._cols[name]


def _txt(v) -> str | None:
    """A text value of a cell, or None when it is missing ('' in the compact column)."""
    return str(v) if v not in ("", None) else None


def _f(a) -> np.ndarray:
    a = np.asarray(a)
    return a if a.dtype.kind == "f" else np.array([np.nan if v is None else v for v in a], dtype=float)


def _bbox(b) -> tuple[float, float, float, float]:
    if not isinstance(b, (list, tuple)) or len(b) != 4 or not all(isinstance(v, (int, float)) for v in b):
        raise QueryError("bbox must be [west, south, east, north] in degrees")
    w, s, e, n = (float(v) for v in b)
    if not (-180 <= w <= 180 and -180 <= e <= 180 and -90 <= s < n <= 90):
        raise QueryError("bbox must be [west, south, east, north] with -180..180 and -90..90, south below north")
    return w, s, e, n


def _in_bbox(rel: Release, b) -> np.ndarray:
    w, s, e, n = _bbox(b)
    inside_lon = (rel.lon >= w) & (rel.lon <= e) if w <= e else (rel.lon >= w) | (rel.lon <= e)   # across 180°
    return inside_lon & (rel.lat >= s) & (rel.lat <= n)


def _env(rel: Release, env) -> str:
    if env not in rel.targets:
        raise QueryError(f"env must be one of {', '.join(rel.targets)}")
    return env


def cells_in_bbox(rel: Release, bbox, env: str) -> dict:
    """GeoJSON polygons of the cells whose centre is in the view, with value, spread, state and coverage."""
    t = _env(rel, env)
    idx = np.flatnonzero(_in_bbox(rel, bbox))
    if idx.size > CELL_CAP:
        raise QueryError(f"{idx.size} cells in this view, {CELL_CAP} at most: zoom in")
    sub = {k: rel.col(k)[idx] for k in ("cell", "windows", "masked_share", "cover_unknown", "confidence",
                                        f"{t}:windows", f"{t}:valid", f"{t}:screened_out")}
    cls = coverage_class(sub, t) if idx.size else np.array([], object)
    clat, clon = corners(NSIDE, rel.ids[idx])
    med, p25, p75 = (_f(rel.col(f"{t}:{k}"))[idx] for k in ("median", "p25", "p75"))
    tv, tw = _f(rel.col(f"{t}:valid"))[idx], _f(rel.col(f"{t}:windows"))[idx]
    num = lambda v: None if not np.isfinite(v) else round(float(v), 4)  # noqa: E731
    feats = []
    for k, i in enumerate(idx):
        ring = [[round(float(clon[k, j]), 5), round(float(clat[k, j]), 5)] for j in range(4)]
        feats.append({"type": "Feature", "geometry": {"type": "Polygon", "coordinates": [ring + [ring[0]]]},
                      "properties": {"id": str(rel.ids[i]), "lat": round(float(rel.lat[i]), 5), "lon": round(float(rel.lon[i]), 5),
                                     "typicality": {"median": num(med[k]), "p25": num(p25[k]), "p75": num(p75[k])},
                                     "windows": {"valid": None if not np.isfinite(tv[k]) else int(tv[k]),
                                                 "total": None if not np.isfinite(tw[k]) else int(tw[k])},
                                     "coverage": str(cls[k]), "confidence": _txt(rel.col("confidence")[i]),
                                     "masked_share": num(_f(rel.col("masked_share"))[i]),
                                     "requirements": {r: _txt(rel.col(f"req:{r}")[i]) for r in REQUIREMENTS}}})
    return {**rel.head, "type": "FeatureCollection", "env": t, "features": feats}


def run_query(rel: Release, q: dict) -> dict:
    """Cells meeting custom criteria: typicality to one target at least x, a minimum confidence, requirements met,
    inside an optional box. Ranked by typicality; at most `limit` cells returned, all of them counted."""
    if not isinstance(q, dict):
        raise QueryError("the query must be a JSON object")
    extra = set(q) - QUERY_FIELDS
    if extra:
        raise QueryError(f"unknown field: {sorted(extra)[0]}")
    t = _env(rel, q.get("env"))
    mt = q.get("min_typicality", 0.0)
    if not isinstance(mt, (int, float)) or not 0 <= mt <= 1:
        raise QueryError("min_typicality must be a number from 0 to 1")
    mc = q.get("min_confidence", "low")
    if mc not in CONFIDENCE_RANK:
        raise QueryError("min_confidence must be low, medium or high")
    reqs = q.get("requirements_met", [])
    if not isinstance(reqs, list) or any(r not in REQUIREMENTS for r in reqs):
        raise QueryError(f"each requirement must be one of {', '.join(REQUIREMENTS)}")
    limit = q.get("limit", 100)
    if not isinstance(limit, int) or not 1 <= limit <= MAX_RETURNED:
        raise QueryError(f"limit must be an integer from 1 to {MAX_RETURNED}")
    area = _in_bbox(rel, q["bbox"]) if "bbox" in q else np.ones(rel.ids.size, bool)
    if int(area.sum()) > QUERY_CELL_CAP:
        raise QueryError(f"{int(area.sum())} cells in the query area, {QUERY_CELL_CAP:,} cells at most: narrow the box")
    med = _f(rel.col(f"{t}:median"))
    conf = rel.col("confidence")
    rank = np.select([conf == k for k in CONFIDENCE_RANK], list(CONFIDENCE_RANK.values()), default=-1)
    keep = area & np.isfinite(med) & (np.nan_to_num(med, nan=-1) >= mt) & (rank >= CONFIDENCE_RANK[mc])
    for r in reqs:
        keep &= rel.col(f"req:{r}") == "met"
    idx = np.flatnonzero(keep)
    top = idx[np.argsort(-med[idx], kind="stable")][:limit]
    return {**rel.head, "env": t, "criteria": {"min_typicality": mt, "min_confidence": mc, "requirements_met": reqs,
                                               **({"bbox": q["bbox"]} if "bbox" in q else {})},
            "matched": int(idx.size), "area_km2": round(idx.size * cell_area_km2(), 1),
            "cells": [{"id": str(rel.ids[i]), "lat": round(float(rel.lat[i]), 5), "lon": round(float(rel.lon[i]), 5),
                       "typicality": round(float(med[i]), 4), "confidence": _txt(conf[i])} for i in top]}
