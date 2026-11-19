"""Candidate zones (T26 rule, ADR-001 stage `zones`).

Candidate cells are joined into zones by 8-neighbour connection. Cells come from many local tile projections, so
"neighbour" is read on the sphere: two cells join when their centres are closer than 7.43 km (the 5 km cell
diagonal, plus 5%). Distances are chord lengths in 3D, so the poles and the antimeridian need no special case.
"""
from __future__ import annotations

import numpy as np

EARTH_R_KM = 6371.0088
CELL_KM = 5.0
LINK_KM = CELL_KM * np.sqrt(2) * 1.05


def _xyz(lat: np.ndarray, lon: np.ndarray) -> np.ndarray:
    la, lo = np.radians(lat), np.radians(lon)
    return EARTH_R_KM * np.stack([np.cos(la) * np.cos(lo), np.cos(la) * np.sin(lo), np.sin(la)], axis=1)


def connect_reference(lat: np.ndarray, lon: np.ndarray, link_km: float = LINK_KM) -> np.ndarray:
    """Reference implementation (union-find in Python, one cell at a time): kept for the tests."""
    p = _xyz(np.asarray(lat, float), np.asarray(lon, float))
    n = len(p)
    parent = np.arange(n)

    def find(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    keys = np.floor(p / link_km).astype(np.int64)
    buckets: dict = {}
    for i, k in enumerate(map(tuple, keys)):
        buckets.setdefault(k, []).append(i)
    offsets = [(a, b, c) for a in (-1, 0, 1) for b in (-1, 0, 1) for c in (-1, 0, 1)]
    for k, members in buckets.items():
        cand = [j for d in offsets for j in buckets.get((k[0] + d[0], k[1] + d[1], k[2] + d[2]), [])]
        cand = np.array(cand)
        for i in members:
            near = cand[np.linalg.norm(p[cand] - p[i], axis=1) <= link_km]
            ri = find(i)
            for j in near:
                rj = find(j)
                if rj != ri:
                    parent[rj] = ri
    return np.array([find(i) for i in range(n)])


def connect(lat: np.ndarray, lon: np.ndarray, link_km: float = LINK_KM) -> np.ndarray:
    """Zone label of each cell, vectorised: candidate pairs from a 3D grid hash of cell size link_km, then
    connected components by minimum-label propagation with pointer jumping. Same partition as
    connect_reference, for millions of cells."""
    p = _xyz(np.asarray(lat, float), np.asarray(lon, float))
    n = len(p)
    if n == 0:
        return np.zeros(0, int)
    k = np.floor(p / link_km).astype(np.int64) + 2048              # positive bucket coordinates (< 4096)
    code = (k[:, 0] << 24) | (k[:, 1] << 12) | k[:, 2]
    order = np.argsort(code, kind="stable")
    sc = code[order]
    src, dst = [], []
    for d0 in (-1, 0, 1):
        for d1 in (-1, 0, 1):
            for d2 in (-1, 0, 1):
                tgt = code + ((d0 << 24) + (d1 << 12) + d2)
                lo, hi = np.searchsorted(sc, tgt, "left"), np.searchsorted(sc, tgt, "right")
                cnt = hi - lo
                if not cnt.any():
                    continue
                i = np.repeat(np.arange(n), cnt)
                start = np.repeat(lo, cnt)
                offs = np.arange(cnt.sum()) - np.repeat(np.cumsum(cnt) - cnt, cnt)
                j = order[start + offs]
                keep = (i < j) & (np.linalg.norm(p[i] - p[j], axis=1) <= link_km)
                src.append(i[keep])
                dst.append(j[keep])
    a = np.concatenate(src) if src else np.zeros(0, int)
    b = np.concatenate(dst) if dst else np.zeros(0, int)
    lab = np.arange(n)
    while True:
        m = np.minimum(lab[a], lab[b])
        new = lab.copy()
        np.minimum.at(new, a, m)
        np.minimum.at(new, b, m)
        new = new[new]                                             # pointer jumping
        while not np.array_equal(new, new[new]):
            new = new[new]
        if np.array_equal(new, lab):
            return lab
        lab = new


def zone_table(lat: np.ndarray, lon: np.ndarray, area_km2: np.ndarray, min_cells: int) -> list[dict]:
    """Zones of at least min_cells cells: cell indices, cell count, area, centre (mean of cell centres).
    Grouped by sorting labels; zones below min_cells are dropped before any loop."""
    lat, lon, area_km2 = np.asarray(lat, float), np.asarray(lon, float), np.asarray(area_km2, float)
    lab = connect(lat, lon)
    if lab.size == 0:
        return []
    order = np.argsort(lab, kind="stable")
    sl = lab[order]
    bounds = np.flatnonzero(np.diff(sl)) + 1
    groups = np.split(order, bounds)
    out = []
    for idx in groups:
        if idx.size < min_cells:
            continue
        idx = np.sort(idx)
        c = _xyz(lat[idx], lon[idx]).mean(axis=0)
        out.append({"cells": int(idx.size), "area_km2": float(np.sum(area_km2[idx])),
                    "lat": float(np.degrees(np.arcsin(c[2] / np.linalg.norm(c)))),
                    "lon": float(np.degrees(np.arctan2(c[1], c[0]))), "members": idx.tolist()})
    return out
