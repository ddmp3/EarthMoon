"""Pipeline tail: structured export for the React + TypeScript frontend (replaces folium/HTML maps).

Output  <out_dir>/analogs_results.json   { meta, sites: [AnalogSite, ...] }      (types: schema/analogs.ts)
        <out_dir>/analogs_results.geojson (optional; same properties, GeoJSON order [lon, lat])
Per-site keys are EXACTLY:
  id, name, coordinates[lat, lon], datasetSource, targetBody, regimeCluster,
  comparison{similarityIndex, noveltyScore, geometryMatch, thermalQuantileMatch},
  dataGaps{temporalGapRatio, spatialUncertainty, isCriticalZone},
  variables{tempQuantile, radiation, soilMoisture, windSpeed, slope, roughness}
Non-finite values are written as null (RCM cells have no thermal/atmospheric variables).
"""
from __future__ import annotations
import json
import os
from datetime import datetime, timezone
import numpy as np
import pandas as pd

SCHEMA_VERSION = "1.0"
SITE_KEYS = ["id", "name", "coordinates", "datasetSource", "targetBody", "regimeCluster", "comparison", "dataGaps", "variables"]
COMPARISON_KEYS = ["similarityIndex", "noveltyScore", "geometryMatch", "thermalQuantileMatch"]
GAPS_KEYS = ["temporalGapRatio", "spatialUncertainty", "isCriticalZone"]
VARIABLE_KEYS = ["tempQuantile", "radiation", "soilMoisture", "windSpeed", "slope", "roughness"]
SOURCES = ("NLDAS", "RCM_Arctic", "RCM_Antarctic")


def _num(x, nd=5):
    try:
        v = float(x)
    except (TypeError, ValueError):
        return None
    return round(v, nd) if np.isfinite(v) else None


def _hemi(lat, lon):
    return f"{abs(lat):.3f}°{'N' if lat >= 0 else 'S'} {abs(lon):.3f}°{'E' if lon >= 0 else 'W'}"


def build_sites(df: pd.DataFrame, target_body: str = "Moon", nov_scale_km: float = 1500.0) -> list[dict]:
    """df columns used: source, lat, lon, regime, mcsi, novelty_km, geometry_match, thermal_match, missing_frac, gap_index,
    critical, t_p05_q, sw_net_mean, soil_moist_mean, wind_mean, slope_deg, roughness_m."""
    g = df.get
    sites = []
    for r in df.itertuples(index=False):
        lat, lon = float(r.lat), float(r.lon)
        reg = getattr(r, "regime", np.nan)
        nov = getattr(r, "novelty_km", np.nan)
        sites.append({
            "id": f"{r.source}_{lat:.3f}_{lon:.3f}",
            "name": f"{r.source} cell {_hemi(lat, lon)}",
            "coordinates": [round(lat, 5), round(lon, 5)],
            "datasetSource": r.source,
            "targetBody": target_body,
            "regimeCluster": int(reg) if pd.notna(reg) else None,
            "comparison": {
                "similarityIndex": _num(getattr(r, "mcsi", np.nan)),
                "noveltyScore": _num(np.clip(nov / nov_scale_km, 0, 1)) if pd.notna(nov) else None,
                "geometryMatch": _num(getattr(r, "geometry_match", np.nan)),
                "thermalQuantileMatch": _num(getattr(r, "thermal_match", np.nan)) if pd.notna(getattr(r, "t_p05", np.nan)) else None,
            },
            "dataGaps": {
                "temporalGapRatio": _num(getattr(r, "missing_frac", np.nan)),
                "spatialUncertainty": _num(getattr(r, "gap_index", np.nan)),
                "isCriticalZone": bool(getattr(r, "critical", False)),
            },
            "variables": {
                "tempQuantile": _num(getattr(r, "t_p05_q", np.nan)),
                "radiation": _num(getattr(r, "sw_net_mean", np.nan), 3),
                "soilMoisture": _num(getattr(r, "soil_moist_mean", np.nan), 3),
                "windSpeed": _num(getattr(r, "wind_mean", np.nan), 3),
                "slope": _num(getattr(r, "slope_deg", np.nan), 3),
                "roughness": _num(getattr(r, "roughness_m", np.nan), 3),
            },
        })
    return sites


def select_candidates(df: pd.DataFrame, top_n: int = 500, max_critical: int = 300) -> pd.DataFrame:
    """Top-N by priority UNION the most poorly observed critical zones."""
    d = df.dropna(subset=["mcsi"])
    top = d.nlargest(top_n, "priority")
    crit = d[d["critical"].astype(bool)].nlargest(max_critical, "gap_index") if "critical" in d else d.iloc[0:0]
    return pd.concat([top, crit]).drop_duplicates(["source", "lat", "lon"]).sort_values("priority", ascending=False)


def validate(payload: dict) -> None:
    """Raises AssertionError if any site deviates from the contract."""
    assert set(payload) >= {"meta", "sites"}
    for s in payload["sites"]:
        assert list(s) == SITE_KEYS, list(s)
        assert list(s["comparison"]) == COMPARISON_KEYS
        assert list(s["dataGaps"]) == GAPS_KEYS
        assert list(s["variables"]) == VARIABLE_KEYS
        assert s["datasetSource"] in SOURCES and len(s["coordinates"]) == 2
        assert isinstance(s["dataGaps"]["isCriticalZone"], bool)


def to_geojson(sites: list[dict]) -> dict:
    feats = []
    for s in sites:
        lat, lon = s["coordinates"]
        props = {k: v for k, v in s.items() if k != "coordinates"}
        feats.append({"type": "Feature", "id": s["id"], "geometry": {"type": "Point", "coordinates": [lon, lat]}, "properties": props})
    return {"type": "FeatureCollection", "features": feats}


def export_results(df: pd.DataFrame, out_dir: str, meta: dict, top_n: int = 500, max_critical: int = 300,
                   target_body: str = "Moon", geojson: bool = True) -> dict:
    os.makedirs(out_dir, exist_ok=True)
    cand = select_candidates(df, top_n, max_critical)
    sites = build_sites(cand, target_body)
    payload = {"meta": {"schemaVersion": SCHEMA_VERSION, "generatedAt": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                        "targetBody": target_body, "nSites": len(sites), "nCellsScored": int(df["mcsi"].notna().sum()), **meta},
               "sites": sites}
    validate(payload)
    paths = {"json": os.path.join(out_dir, "analogs_results.json")}
    with open(paths["json"], "w", encoding="utf-8") as fh:
        json.dump(payload, fh, ensure_ascii=False, allow_nan=False, indent=1)
    if geojson:
        paths["geojson"] = os.path.join(out_dir, "analogs_results.geojson")
        with open(paths["geojson"], "w", encoding="utf-8") as fh:
            json.dump(to_geojson(sites), fh, ensure_ascii=False, allow_nan=False)
    return paths
