"""Local zone update (T52, ADR-009 section 2): only the zones that touch changed cells are recomputed.

A zone is a connected set of candidate cells (HEALPix neighbours, protocol v3). When the candidacy of some cells
changes, a zone can change only if it holds a changed cell or touches one. Those zones are removed, and their cells,
with the changed cells that are now candidates, seed a walk over the candidate cells through HEALPix neighbours. The
walk stops at the edge of each component, so its cost is the size of the zones touched, never the planet. The result
equals a full recomputation (tests/test_zones_local.py).
"""
from __future__ import annotations

import numpy as np

from discovery.healpix import NSIDE, neighbours


def _nb(cells) -> set[int]:
    if not cells:
        return set()
    n = neighbours(NSIDE, np.fromiter(cells, np.int64, len(cells))).ravel()
    return {int(c) for c in n if c >= 0}


def update_zones(old_zones: list[list[int]], cand_old: np.ndarray, changed: dict[int, bool],
                 min_cells: int) -> tuple[list[list[int]], np.ndarray, dict]:
    """New zones, new sorted candidate ids and counts. `changed` maps a cell to its new candidacy."""
    cand = set(np.asarray(cand_old, np.int64).tolist())
    for c, v in changed.items():
        (cand.add if v else cand.discard)(int(c))
    near = set(changed) | _nb(set(changed))
    keep, seeds, recomputed = [], set(), 0
    for z in old_zones:
        if near.isdisjoint(z):
            keep.append(list(z))
        else:
            recomputed += 1
            seeds.update(int(c) for c in z)
    seeds.update(c for c in near if c in cand)
    seeds &= cand
    visited: set[int] = set()
    new = []
    for s in seeds:
        if s in visited:
            continue
        comp, front = {s}, {s}
        while front:
            front = {c for c in _nb(front) if c in cand and c not in comp}
            comp |= front
        visited |= comp
        if len(comp) >= min_cells:
            new.append(sorted(comp))
    out = np.array(sorted(cand), np.int64)
    return keep + new, out, {"visited": len(visited), "recomputed_zones": recomputed, "new_zones": len(new)}
