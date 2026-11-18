"""Statistics of 5 km cells from their 1 km windows (T22 decision 3).

Per cell: windows owned, valid windows, valid fraction, median, quartiles, p5, p95 and robust sigma
(1.4826 x MAD, NaN below 3 windows). State: `missing` with no valid window, `partial` below 50% valid windows,
otherwise `evaluated`. A missing value is NaN, never a number.
"""
from __future__ import annotations

import numpy as np

PARTIAL_BELOW = 0.5


def cell_table(windows: dict[str, np.ndarray], cell: np.ndarray, owned: np.ndarray, params: tuple[str, ...]) -> dict:
    out = {}
    for cid in np.unique(cell[owned]):
        sel = owned & (cell == cid)
        n = int(sel.sum())
        nv = int(np.isfinite(windows[params[0]][sel]).sum())
        row: dict = {"n_windows": n, "n_valid": nv, "valid_frac": nv / n,
                     "state": "missing" if nv == 0 else ("partial" if nv / n < PARTIAL_BELOW else "evaluated")}
        for p in params:
            v = windows[p][sel]
            v = v[np.isfinite(v)]
            if v.size:
                q = [float(x) for x in np.percentile(v, [5, 25, 50, 75, 95])]
                sigma = float(1.4826 * np.median(np.abs(v - q[2]))) if v.size >= 3 else float("nan")
            else:
                q, sigma = [float("nan")] * 5, float("nan")
            row.update({f"{p}_p5": q[0], f"{p}_q25": q[1], f"{p}_median": q[2], f"{p}_q75": q[3], f"{p}_p95": q[4],
                        f"{p}_sigma": sigma})
        out[int(cid)] = row
    return out
