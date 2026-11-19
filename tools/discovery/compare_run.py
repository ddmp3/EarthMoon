"""Run the comparison engine for one scenario on a set of Earth tiles (T42).

    python tools/discovery/compare_run.py --scenario A --tiles /data/cube/tiles-pilot.txt --cube /data/cube \
        --profiles /data/profiles/moon --out /data/compare --summary data/runs/compare-pilot-A.json

Earth is compared at the pixel scale of each lunar product (T22 decision 1): 40 m against LDEM_85S_40M targets,
59.2 m against SLDEM2015 targets. A target without an Earth cube at its scale is reported as not comparable.
Rules that turn scenario requirements into window tests are in RULES, each with its source.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from discovery.compare import (assess_cells, cell_medians, masked_windows, monte_carlo,  # noqa: E402
                               percentile_typicality)

ROOT = Path(__file__).resolve().parents[2]
SEED, RUNS, SLOPE_SIGMA = 20261119, 500, 0.5
SCALE = {"moon-south-polar-cap-v2": "glo30-40m", "moon-polar-lit-highlands": "glo30-40m", "moon-psr": "glo30-40m",
         "moon-mare-plains": "glo30-59m", "moon-pits": "glo30-59m", "moon-persistently-lit": None}
NOT_COMPARABLE = {"moon-persistently-lit": "100 m windows at 5 m: no Earth cube at 5 m (national lidar only)"}

# Scenario requirement id -> window test. Text values of the scenarios, read as conservative bounds.
RULES = {
    "climbing_limit_lrv": {"param": "traversable_20", "at_least": 0.5, "scale": "glo30-40m",
                           "why": "LRV 20 to 23°, max 25° (NTRS 20250011301); 20° used, the stored lower bound; half of the window (E1)"},
    "climbing_limit_viper": {"param": "traversable_15", "at_least": 0.5, "scale": "glo30-40m",
                             "why": "VIPER 15° not verified (E1); reported, never eliminating"},
    "base_slope": {"param": "slope_mean", "at_most": 10.0, "scale": "glo30-40m",
                   "why": "unsuitable above 10° (E2)"},
}
SUITABILITY = {"A": {"id": "base_slope_suitability", "param": "slope_mean", "good": 5.0, "bad": 10.0, "scale": "glo30-40m",
                     "why": "5° preferred, unsuitable above 10° (E2), linear between"},
               "B": {"id": "traversable_share_20", "param": "traversable_20", "good": 1.0, "bad": 0.0, "scale": "glo30-40m",
                     "why": "share of the window at or below 20°"}}
NOT_EVALUATED = {"base_site_beyond_slope": "value not set (E13); no layer for bearing capacity or boulders",
                 "target_environment": "descriptive: it chooses the targets, it is not a test",
                 "traversable_share": "part of the climbing limit rules (half of the window)"}
WINDOW_COLS = ["i", "j", "slope_mean", "traversable_15", "traversable_20", "wc_tree", "wc_built", "wc_water",
               "wc_snow_ice", "wc_covered"]


def load_windows(folder: Path, tiles: list[str]) -> dict:
    import pyarrow.parquet as pq
    parts = []
    for name in tiles:
        t = pq.read_table(folder / f"{name}.windows.parquet", columns=WINDOW_COLS)
        d = {k: t.column(k).to_numpy() for k in WINDOW_COLS}
        d["cell"] = np.array([f"{name}:{i}:{j}" for i, j in zip(d["i"], d["j"])])
        parts.append(d)
    return {k: np.concatenate([p[k] for p in parts]) for k in parts[0]}


def reference(profiles: Path, target: str) -> np.ndarray:
    import pyarrow.parquet as pq
    if target == "moon-pits":
        sites = json.loads((ROOT / "data/profiles/moon/moon-pits.json").read_text(encoding="utf-8"))["sites"]
        v = np.array([s["context_slope_mean"] for s in sites if s["context_slope_mean"] is not None], dtype="float64")
    else:
        v = pq.read_table(profiles / f"{target}.windows.parquet", columns=["slope_mean"]).column(0).to_numpy()
    v = v[np.isfinite(v)].astype("float64")
    return np.sort(v)


def confidence(valid: int, windows: int, masked: int, unknown_mask: int) -> str:
    """high: at least 20 valid unmasked windows and under 10% of the cell masked or of unknown cover;
    medium: at least 10 valid windows; low otherwise."""
    if valid >= 20 and (masked + unknown_mask) < 0.1 * windows:
        return "high"
    return "medium" if valid >= 10 else "low"


def run(a) -> dict:
    import yaml
    sc = yaml.safe_load((ROOT / f"data/scenarios/{a.scenario}-{'lunar-base' if a.scenario == 'A' else 'lunar-robotics'}.yaml").read_text(encoding="utf-8"))
    from discovery.copernicus import tile_name
    tiles = [tile_name(*(int(v) for v in t.split(",")), "glo30") for t in Path(a.tiles).read_text().split()]
    scales = {s for s in (SCALE[t] for t in sc["targets"]) if s} | {"glo30-40m"}
    win = {s: load_windows(a.cube / s, tiles) for s in scales}
    masks = {}
    for s, w in win.items():
        m, u = masked_windows(w)
        masks[s] = (m, u)
        w["slope_for_similarity"] = np.where(m, np.nan, w["slope_mean"])      # hidden ground is not compared
    cells: dict = {}
    targets_out = {}
    for t in sc["targets"]:
        if SCALE[t] is None:
            targets_out[t] = {"comparable": False, "reason": NOT_COMPARABLE[t]}
            continue
        ref = reference(a.profiles, t)
        w = win[SCALE[t]]
        targets_out[t] = {"comparable": True, "earth_scale": SCALE[t], "reference_windows": int(ref.size),
                          "reference_sha256": hashlib.sha256(ref.tobytes()).hexdigest()}
        res = assess_cells({"cell": w["cell"], "slope_mean": w["slope_for_similarity"]}, {t: ref}, [], None)
        for c, row in res.items():
            cells.setdefault(c, {"similarity": {}, "requirements": {}})["similarity"][t] = row["similarity"][t]
    reqs = [{"id": r["id"], **{k: RULES[r["id"]][k] for k in ("param", "at_least", "at_most") if k in RULES[r["id"]]}}
            for r in sc["requirements"] if r["id"] in RULES]
    base = win["glo30-40m"]
    m40, u40 = masks["glo30-40m"]
    res = assess_cells({"cell": base["cell"], **{k: base[k] for k in ("slope_mean", "traversable_15", "traversable_20")}},
                       {}, reqs, {k: SUITABILITY[a.scenario][k] for k in ("id", "param", "good", "bad")})
    eliminating = set(sc.get("eliminating", []))
    for c, row in res.items():
        out = cells.setdefault(c, {"similarity": {}, "requirements": {}})
        out["requirements"] = row["requirements"]
        out["suitability"] = row["suitability"]
        out["eliminated"] = any(row["requirements"][r]["status"] == "failed" for r in eliminating if r in row["requirements"])
    # coverage and confidence at 40 m
    ids, inv = np.unique(base["cell"], return_inverse=True)
    n = np.bincount(inv)
    valid = np.bincount(inv, weights=np.isfinite(base["slope_for_similarity"]).astype(float)).astype(int)
    nm = np.bincount(inv, weights=m40.astype(float)).astype(int)
    nu = np.bincount(inv, weights=u40.astype(float)).astype(int)
    for k, c in enumerate(ids):
        cells[c]["coverage"] = {"windows": int(n[k]), "valid_unmasked": int(valid[k]), "masked": int(nm[k]),
                                "cover_unknown": int(nu[k])}
        cells[c]["confidence"] = confidence(int(valid[k]), int(n[k]), int(nm[k]), int(nu[k]))
    # uncertainty: Monte Carlo per comparable target
    mc = {}
    for t, info in targets_out.items():
        if not info["comparable"]:
            continue
        w = win[SCALE[t]]
        ref = reference(a.profiles, t)
        rows = monte_carlo({"cell": w["cell"], "slope_mean": w["slope_for_similarity"]}, {t: ref}, t, runs=a.runs,
                           seed=SEED, slope_sigma=SLOPE_SIGMA)
        for r in rows:
            cells[r["cell"]].setdefault("uncertainty", {})[t] = {k: r[k] for k in r if k != "cell"}
        stable = sum(r["share_top_decile"] >= 0.9 for r in rows)
        mc[t] = {"runs": a.runs, "seed": SEED, "slope_sigma_deg": SLOPE_SIGMA, "cells": len(rows),
                 "cells_in_top_decile_in_90pct_of_runs": stable}
    return {"scenario": a.scenario, "tiles": len(tiles), "targets": targets_out, "cells": cells, "monte_carlo": mc}


def smoothing_sensitivity(a, sc: dict, sigma_px: float = 1.0) -> dict:
    """David's decision (T41): no Earth smoothing by default; report the ranking with a 1-pixel Gaussian smoothing.
    The DEM of each tile is read again, smoothed (missing pixels stay missing), measured with the same code, and
    the cell medians of typicality are compared with the unsmoothed run (same masks)."""
    from discovery.copernicus import tile_name
    from discovery.cube import GDAL_ENV, compute_tile, read_dem
    from discovery.grid import tile_grid
    from discovery.resolution import gaussian_smooth_nan
    os.environ.update(GDAL_ENV)
    pixel = {"glo30-40m": 40.0, "glo30-59m": 59.225293836}
    have = {tuple(map(int, k.split(","))) for k in json.loads((a.cube / "glo30-40m" / "listing.json").read_text())}
    pairs = [tuple(int(v) for v in t.split(",")) for t in Path(a.tiles).read_text().split()]
    out = {}
    for scale in sorted({SCALE[t] for t in sc["targets"] if SCALE[t]}):
        raw = load_windows(a.cube / scale, [tile_name(la, lo, "glo30") for la, lo in pairs])
        masked, _ = masked_windows(raw)
        smooth = []
        for la, lo in pairs:
            g = tile_grid(la, lo, pixel[scale], 1000.0)
            z, _ = read_dem(g, "glo30", have, None)
            w, _ = compute_tile(gaussian_smooth_nan(z.astype("float64"), sigma_px).astype("float32"), g)
            smooth.append(w["slope_mean"])
        s_slope = np.concatenate(smooth)
        if s_slope.size != raw["slope_mean"].size:
            raise ValueError(f"{scale}: smoothed windows do not match the cube windows")
        s_slope = np.where(masked, np.nan, s_slope)
        r_slope = np.where(masked, np.nan, raw["slope_mean"])
        ok = np.isfinite(r_slope) & np.isfinite(s_slope) & (r_slope > 0)
        out[scale] = {"sigma_px": sigma_px, "sigma_m": sigma_px * pixel[scale],
                      "earth_slope_median_ratio_smoothed_over_raw": round(float(np.median(s_slope[ok] / r_slope[ok])), 3),
                      "targets": {}}
        for t in sc["targets"]:
            if SCALE[t] != scale:
                continue
            ref = reference(a.profiles, t)
            ids, m_raw = cell_medians(percentile_typicality(r_slope, ref), raw["cell"])
            _, m_s = cell_medians(percentile_typicality(s_slope, ref), raw["cell"])
            both = np.isfinite(m_raw) & np.isfinite(m_s)
            x, y = m_raw[both], m_s[both]
            rx, ry = np.argsort(np.argsort(-x)), np.argsort(np.argsort(-y))
            k = max(int(np.ceil(x.size * 0.1)), 1)
            top_r, top_s = set(np.flatnonzero(rx < k)), set(np.flatnonzero(ry < k))
            out[scale]["targets"][t] = {"cells": int(x.size), "spearman_cell_medians": round(float(np.corrcoef(rx, ry)[0, 1]), 4),
                                        "top_decile_overlap": round(len(top_r & top_s) / k, 3),
                                        "median_typicality_raw": round(float(np.median(x)), 4),
                                        "median_typicality_smoothed": round(float(np.median(y)), 4)}
    return out


def summary(res: dict, top: int = 10) -> dict:
    cells = res["cells"]
    out = {k: res[k] for k in ("scenario", "tiles", "targets", "monte_carlo")}
    out["rules"] = {k: v for k, v in RULES.items()}
    out["suitability_rule"] = SUITABILITY[res["scenario"]]
    out["not_evaluated"] = NOT_EVALUATED
    out["cells"] = len(cells)
    req_ids = sorted({r for c in cells.values() for r in c.get("requirements", {})})
    out["requirements"] = {r: {s: sum(c["requirements"].get(r, {}).get("status") == s for c in cells.values())
                               for s in ("met", "failed", "unknown")} for r in req_ids}
    out["eliminated_cells"] = sum(bool(c.get("eliminated")) for c in cells.values())
    out["confidence"] = {k: sum(c.get("confidence") == k for c in cells.values()) for k in ("high", "medium", "low")}
    out["top"] = {}
    for t, info in res["targets"].items():
        if not info["comparable"]:
            continue
        ranked = sorted((c for c in cells.items() if c[1]["similarity"].get(t, {}).get("median") is not None),
                        key=lambda kv: -kv[1]["similarity"][t]["median"])
        out["top"][t] = [{"cell": k, **v} for k, v in ranked[:top]]
    return out


def write_cells(path: Path, res: dict) -> str:
    """Flat Parquet table, one row per cell, one column per output."""
    import pyarrow as pa
    import pyarrow.parquet as pq
    rows = []
    for c, v in res["cells"].items():
        r = {"cell": c, "confidence": v.get("confidence"), "eliminated": v.get("eliminated")}
        for k, x in v.get("coverage", {}).items():
            r[f"coverage_{k}"] = x
        for t, s in v["similarity"].items():
            for k, x in s.items():
                r[f"sim_{t}_{k}"] = x
        for q, s in v.get("requirements", {}).items():
            r[f"req_{q}"] = s["status"]
        if "suitability" in v:
            r["suitability"] = v["suitability"]["median"]
        for t, u in v.get("uncertainty", {}).items():
            for k, x in u.items():
                r[f"mc_{t}_{k}"] = x
        rows.append(r)
    keys = sorted({k for r in rows for k in r})
    path.parent.mkdir(parents=True, exist_ok=True)
    pq.write_table(pa.table({k: [r.get(k) for r in rows] for k in keys}), path, compression="zstd")
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--scenario", choices=["A", "B"], required=True)
    ap.add_argument("--tiles", required=True)
    ap.add_argument("--cube", type=Path, required=True)
    ap.add_argument("--profiles", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--summary", type=Path, required=True)
    ap.add_argument("--runs", type=int, default=RUNS)
    ap.add_argument("--smoothing", action="store_true", help="add the 1-pixel smoothing sensitivity (streams the DEM)")
    a = ap.parse_args(argv)
    res = run(a)
    sha = write_cells(a.out / f"{a.scenario}.cells.parquet", res)
    s = summary(res)
    s.update({"commit": os.environ.get("EARTHMOON_COMMIT", "unknown"), "cells_parquet_sha256": sha})
    if a.smoothing:
        import yaml
        sc = yaml.safe_load((ROOT / f"data/scenarios/{a.scenario}-{'lunar-base' if a.scenario == 'A' else 'lunar-robotics'}.yaml").read_text(encoding="utf-8"))
        s["smoothing_sensitivity"] = smoothing_sensitivity(a, sc)
        print(json.dumps(s["smoothing_sensitivity"], indent=1))
    a.summary.parent.mkdir(parents=True, exist_ok=True)
    a.summary.write_text(json.dumps(s, indent=1, ensure_ascii=False, default=float) + "\n", encoding="utf-8")
    print(json.dumps({k: s[k] for k in ("cells", "requirements", "eliminated_cells", "confidence", "monte_carlo")}, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
