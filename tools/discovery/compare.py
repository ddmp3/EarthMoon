"""Comparison engine (T42, method of T23, ADR-001 stage `compare`).

Outputs stay separate and are never combined into one score:
- similarity: per parameter and target profile, the two-sided percentile typicality of each window
  (2 min(F, 1 - F) against the lunar windows), summarised per cell by its distribution (median, quartiles,
  share above 0.5), never by one number alone;
- requirements: `met`, `failed` or `unknown` per window, then per cell; a failed requirement is reported next to
  the similarity, never averaged with it;
- operational suitability: its own value;
- coverage and confidence: counts of valid windows, masked and unknown ground.
A missing value counts neither for nor against a cell (v2 semantics).
"""
from __future__ import annotations

import numpy as np

PERCENTILES = (25, 50, 75)


# --- methods (moved from tools/research/compare_methods.py, T23) -------------------------------------------

def interval_score(x: np.ndarray, q: dict) -> np.ndarray:
    """v2: 1 inside [p25, p75], linear to 0 at p5 and p95, 0 outside."""
    x = np.asarray(x, dtype="float64")
    lo = np.clip((x - q["p5"]) / (q["p25"] - q["p5"]), 0, 1)
    hi = np.clip((q["p95"] - x) / (q["p95"] - q["p75"]), 0, 1)
    return np.minimum(np.minimum(lo, hi), 1.0)


def percentile_typicality(x: np.ndarray, ref: np.ndarray) -> np.ndarray:
    """2 min(F, 1 - F) with F the empirical CDF of the reference (mid-rank for ties). NaN stays NaN."""
    x = np.asarray(x, dtype="float64")
    s = np.sort(ref)
    f = (np.searchsorted(s, x, "left") + np.searchsorted(s, x, "right")) / (2 * len(s))
    return np.where(np.isfinite(x), 2 * np.minimum(f, 1 - f), np.nan)


# --- per cell ----------------------------------------------------------------------------------------------

def cell_similarity(typ: np.ndarray, cell: np.ndarray) -> dict:
    """Per cell: window count, valid count, median, quartiles and share above 0.5 of the valid typicalities."""
    out = {}
    order = np.argsort(cell, kind="stable")
    c, t = cell[order], typ[order]
    bounds = np.flatnonzero(c[1:] != c[:-1]) + 1                      # works for text cell ids
    for ids, vals in zip(np.split(c, bounds), np.split(t, bounds)):
        v = vals[np.isfinite(vals)]
        row = {"windows": int(vals.size), "valid": int(v.size)}
        if v.size:
            q25, q50, q75 = np.percentile(v, PERCENTILES)
            row.update({"median": round(float(q50), 6), "share_above_half": float((v > 0.5).mean()),
                        "p25": round(float(q25), 6), "p75": round(float(q75), 6)})
        else:
            row.update({"median": None, "share_above_half": None, "p25": None, "p75": None})
        out[ids[0].item()] = row
    return out


def window_requirement(values: np.ndarray, at_least: float | None = None, at_most: float | None = None) -> np.ndarray:
    """'met', 'failed' or 'unknown' (missing value) per window."""
    v = np.asarray(values, dtype="float64")
    ok = (v >= at_least) if at_least is not None else (v <= at_most)
    return np.where(np.isfinite(v), np.where(ok, "met", "failed"), "unknown")


def cell_requirement(status: np.ndarray, cell: np.ndarray) -> dict:
    """A cell meets a requirement when at least half of its windows with data meet it; with no data, unknown.
    (Same 'half' rule as the traversable share of scenario B, expert decision E1.)"""
    out = {}
    for c in np.unique(cell):
        s = status[cell == c]
        met, failed, unknown = int((s == "met").sum()), int((s == "failed").sum()), int((s == "unknown").sum())
        st = "unknown" if met + failed == 0 else ("met" if met >= (met + failed) / 2 else "failed")
        out[c.item()] = {"status": st, "met": met, "failed": failed, "unknown": unknown}
    return out


def linear_suitability(x: np.ndarray, good: float, bad: float) -> np.ndarray:
    """1 at or below `good`, 0 at or above `bad`, linear between; NaN when the value is missing."""
    x = np.asarray(x, dtype="float64")
    return np.where(np.isfinite(x), np.clip((bad - x) / (bad - good), 0.0, 1.0), np.nan)


def assess_cells(windows: dict, refs: dict, requirements: list[dict], suitability: dict | None,
                 param: str = "slope_mean") -> dict:
    """All outputs per cell, side by side. `refs`: target id -> sorted lunar values of `param`."""
    cell = np.asarray(windows["cell"])
    out: dict = {}
    for tid, ref in refs.items():
        for c, row in cell_similarity(percentile_typicality(windows[param], ref), cell).items():
            out.setdefault(c, {"similarity": {}, "requirements": {}})["similarity"][tid] = row
    for r in requirements:
        bound = {k: r[k] for k in ("at_least", "at_most") if k in r}
        for c, row in cell_requirement(window_requirement(windows[r["param"]], **bound), cell).items():
            out.setdefault(c, {"similarity": {}, "requirements": {}})["requirements"][r["id"]] = row
    if suitability:
        s = linear_suitability(windows[suitability["param"]], suitability["good"], suitability["bad"])
        for c, row in cell_similarity(s, cell).items():
            out.setdefault(c, {"similarity": {}, "requirements": {}})["suitability"] = {
                "id": suitability["id"], "median": row["median"], "valid": row["valid"]}
    return out


def cell_medians(values: np.ndarray, cell: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Median of the finite values of each cell, vectorised (NaN when a cell has none). Same as cell_similarity."""
    v = np.asarray(values, dtype="float64")
    ids, inv = np.unique(cell, return_inverse=True)
    ok = np.isfinite(v)
    key = np.where(ok, v, np.inf)
    order = np.lexsort((key, inv))
    n = np.bincount(inv[ok], minlength=ids.size)
    start = np.concatenate([[0], np.cumsum(np.bincount(inv, minlength=ids.size))[:-1]])
    sv = key[order]
    lo = start + np.maximum((n - 1) // 2, 0)
    hi = start + np.maximum(n // 2, 0)
    med = np.where(n > 0, (sv[np.minimum(lo, sv.size - 1)] + sv[np.minimum(hi, sv.size - 1)]) / 2, np.nan)
    return ids, med


MASK_CLASSES = ("wc_tree", "wc_built", "wc_water", "wc_snow_ice")


def masked_windows(w: dict, share: float = 0.5) -> tuple[np.ndarray, np.ndarray]:
    """Windows whose ground is hidden (forest, buildings, water, snow or ice cover at least `share`), and windows
    whose cover is unknown (no WorldCover data): those stay unknown, never treated as bare ground or as masked."""
    covered = np.nan_to_num(np.asarray(w["wc_covered"], dtype="float64")) > 0
    total = sum(np.nan_to_num(np.asarray(w[k], dtype="float64")) for k in MASK_CLASSES)
    return covered & (total >= share), ~covered


# --- uncertainty -------------------------------------------------------------------------------------------

def monte_carlo(windows: dict, refs: dict, target: str, runs: int, seed: int, slope_sigma: float,
                param: str = "slope_mean") -> list[dict]:
    """Rank of each cell by median typicality under `runs` draws of Gaussian noise on the parameter.
    Rank 1 is the most typical. Returns, per cell, the rank median and 5-95% interval and the share of runs in
    the top decile. Same seed, same output."""
    rng = np.random.default_rng(seed)
    cell = np.asarray(windows["cell"])
    ids = np.unique(cell)
    ranks = np.zeros((runs, ids.size))
    base = np.asarray(windows[param], dtype="float64")
    for i in range(runs):
        noisy = base + rng.normal(0.0, slope_sigma, base.size)
        _, med = cell_medians(percentile_typicality(noisy, refs[target]), cell)
        med = np.where(np.isfinite(med), med, -1.0)
        order = np.argsort(-med, kind="stable")
        ranks[i, order] = np.arange(1, ids.size + 1)
    top = max(int(np.ceil(ids.size * 0.1)), 1)
    return [{"cell": c.item(), "rank_median": float(np.median(ranks[:, j])),
             "rank_p5": float(np.percentile(ranks[:, j], 5)), "rank_p95": float(np.percentile(ranks[:, j], 95)),
             "share_top_decile": float((ranks[:, j] <= top).mean())} for j, c in enumerate(ids)]
