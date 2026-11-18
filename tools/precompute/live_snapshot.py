"""Freezes the live sources (NASA POWER, USGS ComCat, Smithsonian GVP) for every candidate site.

Why: v1 read these sources at request time, so a score could change from one day to the next (the USGS count
grows daily, POWER climatologies are re-issued) and no result could be reproduced. v2 scores a frozen,
dated snapshot; refreshing it is an explicit, versioned act.

Per site:
    power      25-year climatology (annual value "ANN" and the 12 monthly values) of each POWER parameter,
               plus the elevation of the MERRA-2 grid cell POWER used (needed for the lapse-rate correction)
    usgs       number of earthquakes within 300 km between START and END (fixed dates), for M >= 2.5 and M >= 4.5
    volcano    nearest Holocene volcano of the GVP list: distance, name, rock type, landform, type

    python live_snapshot.py ../../data/candidates.json -o ../../data/snapshots/live-sources.json --end 2026-11-01

Standard library only.
"""
from __future__ import annotations

import argparse
import json
import math
import sys
import time
import urllib.request
from datetime import datetime, timezone

POWER_PARAMS = ("T2M", "T2M_MIN", "T2M_MAX", "T2M_RANGE", "WS2M", "RH2M", "QV2M", "PRECTOTCORR", "ALLSKY_SFC_SW_DWN")
POWER_URL = ("https://power.larc.nasa.gov/api/temporal/climatology/point?parameters={params}&community=RE"
             "&longitude={lon}&latitude={lat}&format=JSON")
USGS_URL = ("https://earthquake.usgs.gov/fdsnws/event/1/count?format=geojson&latitude={lat}&longitude={lon}"
            "&maxradiuskm={radius}&minmagnitude={mag}&starttime={start}&endtime={end}")
GVP_URL = ("https://webservices.volcano.si.edu/geoserver/GVP-VOTW/ows?service=WFS&version=2.0.0&request=GetFeature"
           "&typeName=GVP-VOTW:Smithsonian_VOTW_Holocene_Volcanoes&outputFormat=application/json&srsName=EPSG:4326")
RADIUS_KM, START = 300, "2000-01-01"
MAGNITUDES = (2.5, 4.5)
POWER_FILL = -999
EARTH_RADIUS_KM = 6371.0088


def fetch_json(url: str, timeout: float = 90, retries: int = 3):
    last: Exception | None = None
    for attempt in range(retries + 1):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "earthmoon-snapshot"})
            with urllib.request.urlopen(req, timeout=timeout) as res:
                return json.load(res)
        except OSError as e:  # URLError, HTTPError and timeouts
            last = e
            time.sleep(2 * (attempt + 1))
    raise RuntimeError(f"unreachable: {url}") from last


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    rad = math.pi / 180
    a = (math.sin((lat2 - lat1) * rad / 2) ** 2
         + math.cos(lat1 * rad) * math.cos(lat2 * rad) * math.sin((lon2 - lon1) * rad / 2) ** 2)
    return 2 * EARTH_RADIUS_KM * math.asin(min(1.0, math.sqrt(a)))


def parse_power(body: dict) -> dict:
    """{'cell_elevation_m', 'period', 'values': {PARAM: {'ANN': x, 'JAN': ...}}}; fill values become None."""
    params = body["properties"]["parameter"]
    clean = {name: {k: (None if v == POWER_FILL else v) for k, v in months.items()} for name, months in params.items()}
    return {"cell_elevation_m": body["geometry"]["coordinates"][2], "period": body.get("header", {}).get("range"),
            "api_version": body.get("header", {}).get("api", {}).get("version"), "values": clean}


def nearest_volcano(features: list[dict], lat: float, lon: float) -> dict:
    best, best_d = None, math.inf
    for f in features:
        p = f.get("properties") or {}
        vlat, vlon = p.get("Latitude"), p.get("Longitude")
        if not isinstance(vlat, (int, float)) or not isinstance(vlon, (int, float)):
            continue
        d = haversine_km(lat, lon, vlat, vlon)
        if d < best_d:
            best, best_d = p, d
    if best is None:
        raise ValueError("GVP list without usable volcano")
    return {"distance_km": round(best_d, 1), "name": best.get("Volcano_Name"), "number": best.get("Volcano_Number"),
            "major_rock_type": best.get("Major_Rock_Type"), "landform": best.get("Volcanic_Landform"),
            "primary_type": best.get("Primary_Volcano_Type"), "last_eruption_year": best.get("Last_Eruption_Year"),
            "evidence_category": best.get("Evidence_Category")}


def snapshot(sites: list[dict], end: str, fetch=fetch_json, log=print) -> dict:
    gvp = fetch(GVP_URL, timeout=180)["features"]
    out = {}
    for s in sites:
        lat, lon = float(s["lat"]), float(s["lon"])
        rec: dict = {"lat": lat, "lon": lon}
        try:
            rec["power"] = parse_power(fetch(POWER_URL.format(params=",".join(POWER_PARAMS), lat=lat, lon=lon)))
        except (RuntimeError, KeyError, IndexError, TypeError) as e:
            rec["power"], rec["power_error"] = None, f"{type(e).__name__}: {e}"
        usgs = {}
        for mag in MAGNITUDES:
            try:
                count = fetch(USGS_URL.format(lat=lat, lon=lon, radius=RADIUS_KM, mag=mag, start=START, end=end))["count"]
                usgs[f"m{mag}"] = count if isinstance(count, int) and count >= 0 else None
            except (RuntimeError, KeyError, TypeError) as e:
                usgs[f"m{mag}"], rec["usgs_error"] = None, f"{type(e).__name__}: {e}"
        rec["usgs"] = usgs
        rec["volcano"] = nearest_volcano(gvp, lat, lon)
        out[s["id"]] = rec
        log(f"  {s['id']}: cell {rec['power'] and rec['power']['cell_elevation_m']} m, quakes {usgs}, "
            f"volcano {rec['volcano']['name']} at {rec['volcano']['distance_km']} km")
    return {
        "created_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "sources": {
            "power": {"url": "https://power.larc.nasa.gov/", "parameters": list(POWER_PARAMS), "community": "RE"},
            "usgs": {"url": "https://earthquake.usgs.gov/fdsnws/event/1/", "radius_km": RADIUS_KM, "start": START, "end": end},
            "gvp": {"url": "https://volcano.si.edu/", "layer": "Smithsonian_VOTW_Holocene_Volcanoes", "volcanoes": len(gvp)},
        },
        "sites": out,
    }


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("candidates")
    ap.add_argument("-o", "--output", required=True)
    ap.add_argument("--end", required=True, help="end date of the earthquake count (YYYY-MM-DD), fixed for reproducibility")
    a = ap.parse_args(argv)
    with open(a.candidates, encoding="utf-8") as fh:
        sites = json.load(fh)
    snap = snapshot(sites, a.end)
    with open(a.output, "w", encoding="utf-8") as fh:
        json.dump(snap, fh, ensure_ascii=False, indent=1)
        fh.write("\n")
    bad = [i for i, r in snap["sites"].items() if "power_error" in r or "usgs_error" in r]
    print(f"{len(snap['sites']) - len(bad)}/{len(snap['sites'])} sites complete" + (f" | incomplete: {bad}" if bad else ""))
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
