"""Builds the frozen, versioned dataset scored by the API (data/dataset-v2.json).

Inputs (all versioned in the repository):
    data/candidates-precomputed.json   terrain (terrain_v2, site_terrain.py) and MODIS (modis_values.py)
    data/snapshots/live-sources.json   NASA POWER, USGS and GVP frozen by live_snapshot.py
    data/evidence/lava-tubes.json      curated, referenced evidence of lava tubes

Each value carries: `value` (None = no measurement, never a default), `sigma` (1-sigma uncertainty, None when
it has not been quantified), `sigma_basis` and `flags`. Transformations applied here, each documented in
docs/METHOD.md:

    air temperatures   corrected from the elevation of the reanalysis grid cell to the elevation of the site
                       with the standard lapse rate (6.5 K/km)
    t2m_min            lowest monthly T2M_MIN of the climatology
    specific_humidity  POWER QV2M (g/kg): absolute water vapour content, replaces relative humidity
    wind, humidity, precipitation, solar
                       left missing when the reanalysis grid cell is more than 1 km above or below the site
    quake_m45_count    earthquakes M >= 4.5 (magnitude above which the catalog is reported worldwide)
    lava_tube_evidence ordinal 1 to 3, None when not assessed

    python build_dataset.py            # writes data/dataset-v2.json
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import sys

DATASET_VERSION = "2.0.0"
LAPSE_RATE_K_PER_M = 0.0065
LAPSE_RATE_SIGMA_K_PER_M = 0.002
REANALYSIS_T_SIGMA_K = 1.5
ELEVATION_FLAG_M = 500.0
LARGE_CORRECTION_M = 1000.0
PREDISPOSITION_RADIUS_KM = 30.0
BASALTIC_ROCKS = ("Basalt / Picro-Basalt", "Trachybasalt / Tephrite Basanite")
TERRAIN = ("slope_mean", "slope_p95", "slope_max", "roughness", "roughness_detrended",
           "traversable_15", "traversable_20", "traversable_25")
POWER_DIRECT = {"wind": "WS2M", "humidity": "RH2M", "specific_humidity": "QV2M", "precipitation": "PRECTOTCORR",
                "solar": "ALLSKY_SFC_SW_DWN"}
POWER_TEMPERATURE = {"t2m_mean": "T2M", "t2m_min": "T2M_MIN", "t2m_max": "T2M_MAX"}
MODIS = ("lst_day", "lst_night", "lst_amplitude", "ndvi")
HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "..", "..", "data")


def entry(value, sigma=None, basis=None, flags=None) -> dict:
    ok = isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)
    return {"value": value if ok else None, "sigma": sigma if ok else None,
            "sigma_basis": basis if ok and sigma is not None else None, "flags": sorted(flags or [])}


def corrected_temperature(t_cell, cell_elev_m: float, site_elev_m: float) -> tuple[float | None, float | None]:
    """Temperature at the site elevation and its 1-sigma uncertainty (reanalysis error + lapse-rate error)."""
    if t_cell is None:
        return None, None
    dz = site_elev_m - cell_elev_m
    sigma = math.hypot(REANALYSIS_T_SIGMA_K, LAPSE_RATE_SIGMA_K_PER_M * abs(dz))
    return round(t_cell - LAPSE_RATE_K_PER_M * dz, 2), round(sigma, 2)


def lava_tube_level(site_id: str, volcano: dict | None, curated: dict) -> tuple[int | None, list[str]]:
    if site_id in curated:
        return int(curated[site_id]["level"]), ["curated_reference"]
    if (volcano and volcano.get("distance_km") is not None and volcano["distance_km"] <= PREDISPOSITION_RADIUS_KM
            and volcano.get("major_rock_type") in BASALTIC_ROCKS):
        return 1, ["predisposition_only"]
    return None, ["not_assessed"]


def site_values(site: dict, live: dict | None, curated: dict) -> dict:
    out: dict[str, dict] = {}
    pre = site.get("precomputed") or {}
    terrain = site.get("terrain_v2") or {}
    t_value, t_sigma, t_flags = terrain.get("value") or {}, terrain.get("sigma") or {}, terrain.get("flags") or []
    for k in TERRAIN:
        out[k] = entry(t_value.get(k), t_sigma.get(k), "spread of the 3 x 3 neighbouring 1 km windows", t_flags)
    elevation = pre.get("elevation")
    out["elevation"] = entry(elevation)
    out["latitude_abs"] = entry(abs(float(site["lat"])), 0.0, "exact")

    power = (live or {}).get("power")
    values = (power or {}).get("values") or {}
    cell = (power or {}).get("cell_elevation_m")
    has_dz = isinstance(cell, (int, float)) and isinstance(elevation, (int, float))
    dz = (elevation - cell) if has_dz else None
    mismatch = ["cell_elevation_mismatch"] if dz is not None and abs(dz) > ELEVATION_FLAG_M else []
    for k, name in POWER_TEMPERATURE.items():
        raw = (values.get(name) or {}).get("ANN")
        if dz is None:
            out[k] = entry(raw, REANALYSIS_T_SIGMA_K, "assumed reanalysis error; no elevation correction possible",
                           ["no_elevation_correction"])
            continue
        value, sigma = corrected_temperature(raw, cell, elevation)
        flags = ["elevation_corrected"] + (["large_elevation_correction"] if abs(dz) > LARGE_CORRECTION_M else [])
        out[k] = entry(value, sigma, "assumed reanalysis error (1.5 K) and lapse-rate error (2 K/km)", flags)
    for k, name in POWER_DIRECT.items():
        if dz is not None and abs(dz) > LARGE_CORRECTION_M:
            # A reanalysis grid cell more than 1 km above or below the site does not measure the site (humidity
            # falls off with height, precipitation and wind change across a relief). Unlike temperature there is
            # no accepted correction, so the value is left missing rather than replaced by a guess.
            out[k] = entry(None, flags=["not_representative_elevation"])
            continue
        out[k] = entry((values.get(name) or {}).get("ANN"), None, None, mismatch)

    usgs = (live or {}).get("usgs") or {}
    m45 = usgs.get("m4.5")
    out["quake_m45_count"] = entry(m45, None if m45 is None else round(math.sqrt(max(m45, 1)), 2), "Poisson counting error")
    out["quake_count"] = entry(usgs.get("m2.5"), None, None, ["incomplete_catalog"])

    volcano = (live or {}).get("volcano")
    out["volcano_distance"] = entry((volcano or {}).get("distance_km"), None, None, ["deprecated"])
    level, flags = lava_tube_level(site["id"], volcano, curated)
    out["lava_tube_evidence"] = entry(level, None, None, flags)

    samples = pre.get("modis_samples") or {}
    gaps = ["seasonal_gaps"] if 0 < samples.get("lst_valid_pairs", 0) < samples.get("lst", 0) else []
    for k in MODIS:
        out[k] = entry(pre.get(k), None, None, gaps if k.startswith("lst") else [])
    return out


def sha256(path: str) -> str:
    with open(path, "rb") as fh:
        return hashlib.sha256(fh.read()).hexdigest()


def build(precomputed: list[dict], snapshot: dict, evidence: dict) -> dict:
    live = snapshot.get("sites") or {}
    curated = evidence.get("sites") or {}
    return {
        "version": DATASET_VERSION,
        "snapshot_created_at": snapshot.get("created_at"),
        "sources": snapshot.get("sources"),
        "constants": {
            "lapse_rate_K_per_km": LAPSE_RATE_K_PER_M * 1000, "lapse_rate_sigma_K_per_km": LAPSE_RATE_SIGMA_K_PER_M * 1000,
            "reanalysis_temperature_sigma_K": REANALYSIS_T_SIGMA_K, "predisposition_radius_km": PREDISPOSITION_RADIUS_KM,
            "basaltic_rock_types": list(BASALTIC_ROCKS),
        },
        "sites": {s["id"]: {"lat": s["lat"], "lon": s["lon"], "values": site_values(s, live.get(s["id"]), curated)}
                  for s in precomputed},
    }


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--precomputed", default=os.path.join(DATA, "candidates-precomputed.json"))
    ap.add_argument("--snapshot", default=os.path.join(DATA, "snapshots", "live-sources.json"))
    ap.add_argument("--evidence", default=os.path.join(DATA, "evidence", "lava-tubes.json"))
    ap.add_argument("-o", "--output", default=os.path.join(DATA, "dataset-v2.json"))
    a = ap.parse_args(argv)
    loaded = []
    for path in (a.precomputed, a.snapshot, a.evidence):
        with open(path, encoding="utf-8") as fh:
            loaded.append(json.load(fh))
    dataset = build(*loaded)
    dataset["inputs"] = {os.path.basename(p): sha256(p) for p in (a.precomputed, a.snapshot, a.evidence)}
    with open(a.output, "w", encoding="utf-8") as fh:
        json.dump(dataset, fh, ensure_ascii=False, indent=1)
        fh.write("\n")
    for site_id, s in dataset["sites"].items():
        keys = [k for k, v in s["values"].items() if v["value"] is None and k != "lava_tube_evidence"]
        if keys:
            print(f"  {site_id}: no value for {', '.join(keys)}")
    print(f"{len(dataset['sites'])} sites written to {a.output}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
