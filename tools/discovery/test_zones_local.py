"""Local zone update (T52): only the zones that touch changed cells are recomputed, and the result equals a full
recomputation. Synthetic candidate sets on the real HEALPix grid."""
import numpy as np
import pytest

from discovery.healpix import NSIDE, neighbours
from discovery.zones import connect_cells
from discovery.zones_local import update_zones


def patch(seed: int, centre: int = 5_000_000, size: int = 400) -> np.ndarray:
    """A connected block of cells around `centre` (breadth-first on HEALPix neighbours)."""
    seen, front = {centre}, [centre]
    while len(seen) < size:
        nb = neighbours(NSIDE, np.array(front, np.int64)).ravel()
        front = [int(c) for c in nb if c >= 0 and c not in seen]
        seen.update(front)
    return np.array(sorted(seen), np.int64)


def full(cand: np.ndarray, min_cells: int) -> set:
    lab = connect_cells(cand)
    out = set()
    for v in np.unique(lab):
        m = cand[lab == v]
        if m.size >= min_cells:
            out.add(frozenset(m.tolist()))
    return out


@pytest.mark.parametrize("seed", range(8))
def test_local_update_equals_a_full_recomputation(seed):
    rng = np.random.default_rng(seed)
    area = patch(seed)
    cand_old = np.sort(area[rng.random(area.size) < 0.55])
    old = full(cand_old, 3)
    changed_ids = rng.choice(area, size=25, replace=False)
    changed = {int(c): bool(rng.random() < 0.5) for c in changed_ids}
    zones, cand_new, stats = update_zones([sorted(z) for z in old], cand_old, changed, 3)
    expect = full(np.array(sorted(set(cand_old.tolist()) - {c for c, v in changed.items() if not v}
                                  | {c for c, v in changed.items() if v}), np.int64), 3)
    assert {frozenset(z) for z in zones} == expect
    assert stats["visited"] < area.size                       # it never walks every candidate


def test_no_change_keeps_every_zone_and_visits_nothing():
    area = patch(0)
    cand = area[::2]
    old = [sorted(z) for z in full(cand, 1)]
    zones, _, stats = update_zones(old, cand, {}, 1)
    assert sorted(map(tuple, zones)) == sorted(map(tuple, old)) and stats["visited"] == 0


def test_a_change_far_from_a_zone_leaves_it_untouched():
    a, b = patch(0, centre=5_000_000, size=30), patch(0, centre=2_000_000, size=30)
    cand = np.sort(np.concatenate([a, b]))
    old = [sorted(z) for z in full(cand, 3)]
    zones, _, stats = update_zones(old, cand, {int(b[0]): False}, 3)
    assert sorted(a.tolist()) in [sorted(z) for z in zones]
    assert stats["recomputed_zones"] == 1
