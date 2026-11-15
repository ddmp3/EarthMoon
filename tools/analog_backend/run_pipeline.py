#!/usr/bin/env python3
"""analog_finder orchestrator: audit -> ingest (Earth domains + LRO) -> gaps -> Earth/Moon similarity -> JSON export.

    python run_pipeline.py --config config.json [--output-dir output] [--top-n 500] [--no-geojson] [--audit-only]

Docker:
    docker run --rm -v /host/data:/data:ro -v /host/output:/app/output analog-finder --config /data/config.json
"""
from __future__ import annotations
import argparse
import json
import logging
import os
import sys
import time

import numpy as np
import pandas as pd

from analog_finder import p4_model as p4, p5_similarity as p5
from analog_finder.domains import CLUSTER_OFFSET, DomainSpec, audit_domain, build_domain
from analog_finder.export_results import export_results
from analog_finder.lro import LROConfig, audit_lro, load_lunar_table

log = logging.getLogger("pipeline")

DEFAULTS = {
    "target_body": "Moon",
    "geometry_baseline_m": 120.0,      # shared by Earth DEMs and LOLA -> geometry compared at the same scale
    "sun_elevation_deg": 1.5,          # shared by Earth and Moon shadow modelling
    "weights": {"slope_deg": 1.5, "roughness_m": 1.0, "shadow_frac": 2.0, "t_p05": 2.0, "amp_ratio": 1.0, "ati": 1.0},
    "alpha": 0.7,
    "hard_limits": {},                 # e.g. {"slope_deg": [0, 45]}
    "robustness_runs": 0,              # >0 adds weight-sensitivity stability to meta (slow on big tables)
    "top_n": 500,
    "max_critical": 300,
}


def load_config(path: str) -> dict:
    with open(path, encoding="utf-8") as fh:
        cfg = json.load(fh)
    return {**DEFAULTS, **cfg}


def run_audit(cfg: dict) -> dict:
    """Phase 1: header-only audit of every input. Fails fast on missing required variables."""
    rep = {"domains": [audit_domain(DomainSpec.from_dict(d)) for d in cfg["domains"]]}
    lro = LROConfig.from_dict(cfg["lro"], baseline_m=cfg["geometry_baseline_m"], sun_elevation_deg=cfg["sun_elevation_deg"])
    rep["lro"] = audit_lro(lro)
    for d in rep["domains"]:
        for grp in ("noah", "fora", "thermal"):
            v = d.get(grp, {}).get("value")
            if v and v["missing_needed"]:
                log.warning("%s/%s missing needed variables: %s (value score %.0f)", d["domain"], grp, v["missing_needed"], v["score"])
    return rep


def run(cfg: dict, output_dir: str, geojson: bool = True) -> dict:
    t0 = time.time()
    os.makedirs(output_dir, exist_ok=True)
    cfg = {**DEFAULTS, **cfg}
    base, sun = cfg["geometry_baseline_m"], cfg["sun_elevation_deg"]

    # ---- Phase 1 ----
    audit = run_audit(cfg)
    with open(os.path.join(output_dir, "audit.json"), "w") as fh:
        json.dump(audit, fh, indent=1, default=str)

    # ---- Phase 2 + 3: Earth domains, processed independently ----
    frames, infos, specs = [], {}, [DomainSpec.from_dict(d) for d in cfg["domains"]]
    for spec in specs:
        log.info("Domain %s ...", spec.name)
        df, info = build_domain(spec, base, sun)
        frames.append(df); infos[spec.name] = info
    earth = pd.concat(frames, ignore_index=True)

    # ---- Phase 2 + 5: lunar reference ----
    lro = LROConfig.from_dict(cfg["lro"], baseline_m=base, sun_elevation_deg=sun)
    moon, aoi = load_lunar_table(lro)
    target = p5.build_target_from_rasters(moon, aoi)
    log.info("Lunar cells: %d (target AOI: %d)", len(moon), int(aoi.sum()))

    # ---- Phase 5: normalise per planet, score with ONE shared tau ----
    w = cfg["weights"]
    hl = {k: tuple(v) for k, v in cfg["hard_limits"].items()}
    norm_e = p5.PlanetNormalizer(target).fit(earth)
    norm_m = p5.PlanetNormalizer(target).fit(moon)
    ms = p5.mcsi(moon, norm_m, w, alpha=cfg["alpha"])
    tau = float(ms["d_w"].median())
    es = p5.mcsi(earth, norm_e, w, alpha=cfg["alpha"], tau=tau, hard_limits=hl)
    earth = pd.concat([earth, es], axis=1)
    earth["mcsi_raw"] = earth["mcsi"]
    earth["mcsi"], prior = p5.shrink_partial(earth["mcsi_raw"], earth["coverage"])      # partial-evidence shrinkage
    earth["moon_pctile"] = p5.percentile_vs_moon(earth["mcsi"], ms["mcsi"])
    earth["t_p05_q"] = norm_e.quantile("t_p05", earth["t_p05"].values) if "t_p05" in earth else np.nan
    if cfg["robustness_runs"] > 0:
        earth["stability"] = p5.weight_robustness(earth, norm_e, w, n=cfg["robustness_runs"], tau=tau, alpha=cfg["alpha"])

    # ---- Phase 4: regimes (per domain), novelty, priority ----
    earth["regime"] = np.nan
    for name, info in infos.items():
        idx = earth.index[earth["source"] == name]
        feats = info["cluster_features"]
        if len(feats) >= 2:
            lab, k = p4.cluster_regimes(earth.loc[idx], feats)
            if k:
                earth.loc[lab.index, "regime"] = lab.values + CLUSTER_OFFSET[name]
                info["k"] = int(k)
    earth["novelty_km"] = p4.novelty_km(earth)
    earth["priority"] = p4.rank_analogs(earth)

    # ---- Export ----
    meta = {"geometryBaselineM": base, "sunElevationDeg": sun, "lunarCells": int(len(moon)), "lunarTargetCells": int(aoi.sum()),
            "tau": tau, "partialScorePrior": prior, "weights": w, "alpha": cfg["alpha"], "domains": infos,
            "medianEarthPercentileVsMoon": float(earth["moon_pctile"].median()),
            "notes": "RCM cells lack thermal data: scored on geometry only, then shrunk toward the median full-coverage score by missing weight (partialScorePrior); thermalQuantileMatch=null."}
    paths = export_results(earth, output_dir, meta, cfg["top_n"], cfg["max_critical"], cfg["target_body"], geojson)
    earth.to_parquet(os.path.join(output_dir, "scored_cells.parquet")) if _has_parquet() else \
        earth.to_csv(os.path.join(output_dir, "scored_cells.csv"), index=False)
    log.info("Done in %.1fs -> %s", time.time() - t0, paths)
    return {"paths": paths, "meta": meta, "n_earth": len(earth)}


def _has_parquet() -> bool:
    try:
        import pyarrow  # noqa: F401
        return True
    except ImportError:
        return False


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--config", required=True)
    ap.add_argument("--output-dir", default=None, help="default: config.output_dir or ./output")
    ap.add_argument("--top-n", type=int, default=None)
    ap.add_argument("--no-geojson", action="store_true")
    ap.add_argument("--audit-only", action="store_true", help="Phase 1 only: print audit, download/process nothing")
    ap.add_argument("--log-level", default="INFO")
    a = ap.parse_args(argv)
    logging.basicConfig(level=a.log_level, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    cfg = load_config(a.config)
    if a.top_n:
        cfg["top_n"] = a.top_n
    out = a.output_dir or cfg.get("output_dir") or "output"
    if a.audit_only:
        os.makedirs(out, exist_ok=True)
        rep = run_audit(cfg)
        with open(os.path.join(out, "audit.json"), "w") as fh:
            json.dump(rep, fh, indent=1, default=str)
        print(json.dumps(rep, indent=1, default=str)[:4000])
        return 0
    run(cfg, out, geojson=not a.no_geojson)
    return 0


if __name__ == "__main__":
    sys.exit(main())
