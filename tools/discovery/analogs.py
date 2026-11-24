"""Analog links and place names (T45c part 2, decided by David on 24/11/2026).

**Same-slope link.** Our method compares an Earth zone with the distribution of a planetary environment, not with one
planetary place. So the link shown between the two globes is:
- from an Earth zone: the windows of the target environment whose slope percentile (in the target's own distribution)
  is within 2.5 points of the zone's median slope percentile;
- from a planetary point: the nearest window, then the Earth zones whose percentile is within the same band.

**Names:**
- Earth: OpenStreetMap Nominatim, queried once when the annotations are built. Its usage policy applies: at most 1
  request per second, one thread, an application User-Agent, results cached and never queried twice. Data © OpenStreetMap
  contributors, ODbL: the names file is shared under the ODbL.
- Moon and Mars: the IAU Gazetteer of Planetary Nomenclature (USGS, public domain per its metadata). A point takes the
  smallest named feature whose extent holds it, else "near <nearest feature> (<distance> km)".
"""
from __future__ import annotations

import json
import math
import time
from pathlib import Path
from typing import Callable

import numpy as np

BAND = 0.025                          # half-width of the percentile band of "the same slope"
RULE = ("windows whose slope percentile is within 2.5 points of the zone's, in the target's own distribution "
        "(our method compares a zone with an environment, not with one planetary place)")


def _lon360(lon):
    return np.mod(np.asarray(lon, float), 360.0)


class PlanetNames:
    """Names of the IAU Gazetteer: features with name, lat, lon (east, 0-360), diameter (km) and bbox."""

    def __init__(self, features: list[dict], radius_km: float):
        self.f = features
        self.r = radius_km
        self.lat = np.radians([x["lat"] for x in features])
        self.lon = np.radians([x["lon"] for x in features])
        b = np.array([x["bbox"] for x in features], float)
        self.min_lat, self.max_lat, self.min_lon, self.max_lon = b[:, 0], b[:, 1], b[:, 2], b[:, 3]
        self.diam = np.array([x["diameter"] for x in features], float)

    def name(self, lat: float, lon: float) -> str:
        lo = float(_lon360(lon))
        inside = (self.diam > 0) & (lat >= self.min_lat) & (lat <= self.max_lat) & (
            ((lo >= self.min_lon) & (lo <= self.max_lon)) | ((lo + 360 >= self.min_lon) & (lo + 360 <= self.max_lon)))
        if inside.any():
            k = np.flatnonzero(inside)[np.argmin(self.diam[inside])]
            return self.f[k]["name"]
        la, lr = math.radians(lat), math.radians(lo)
        c = np.sin(la) * np.sin(self.lat) + np.cos(la) * np.cos(self.lat) * np.cos(self.lon - lr)
        d = np.arccos(np.clip(c, -1, 1)) * self.r
        k = int(np.argmin(d))
        return f"near {self.f[k]['name']} ({d[k]:.0f} km)"


def read_gazetteer(shp: Path) -> list[dict]:
    """Approved named features of a USGS nomenclature centre-points shapefile."""
    import shapefile
    out = []
    for rec in shapefile.Reader(str(shp)).records():
        r = rec.as_dict()
        if not str(r.get("approval", "")).startswith("Adopted"):
            continue
        out.append({"name": r["clean_name"] or r["name"], "lat": float(r["center_lat"]), "lon": float(r["center_lon"]) % 360,
                    "diameter": float(r["diameter"] or 0.0), "type": r.get("type"),
                    "bbox": (float(r["min_lat"]), float(r["max_lat"]), float(r["min_lon"]), float(r["max_lon"]))})
    return out


def polar_latlon(x_m, y_m, radius_m: float, south: bool = True):
    """Centre of a window of a polar stereographic grid (pole at the origin): latitude, east longitude (0-360).
    Longitude convention of the LOLA polar products: x = r sin(lon), y = r cos(lon) (checked against Shackleton)."""
    x, y = np.asarray(x_m, float), np.asarray(y_m, float)
    rho = np.hypot(x, y)
    lat_abs = 90 - np.degrees(2 * np.arctan(rho / (2 * radius_m)))
    lon = np.degrees(np.arctan2(x, y)) % 360
    return (-lat_abs if south else lat_abs), lon


def zone_slopes(zones: dict, read_tile: Callable[[str], dict | None]) -> dict:
    """Median window slope of each zone: windows whose centre falls in one of its cells, with less than half of their
    ground hidden (the engine's mask rule outside Antarctica). None when the zone has no such window."""
    from discovery.discover import global_cell
    cache: dict = {}
    out = {}
    for zid, z in zones.items():
        want = np.asarray(z["cells"], np.int64)
        vals = []
        for t in z["tiles"]:
            if t not in cache:
                cache[t] = read_tile(t)
            w = cache[t]
            if not w:
                continue
            c = global_cell(np.asarray(w["lat"], float), np.asarray(w["lon"], float))
            ok = np.isin(c, want) & np.isfinite(np.asarray(w["slope_mean"], float)) & (np.asarray(w["hidden"], float) < 0.5)
            vals.append(np.asarray(w["slope_mean"], float)[ok])
        v = np.concatenate(vals) if vals else np.array([])
        out[zid] = round(float(np.median(v)), 3) if v.size else None
    return out


def percentile(ref_sorted: np.ndarray, slope: float) -> float:
    return float(np.searchsorted(ref_sorted, slope, side="right") / ref_sorted.size)


def same_slope(slope: float, ref_sorted: np.ndarray, windows: dict, band: float = BAND) -> dict:
    """Windows of the target whose slope percentile is within `band` of the zone's."""
    p = percentile(ref_sorted, slope)
    pw = np.searchsorted(ref_sorted, np.asarray(windows["slope"], float), side="right") / ref_sorted.size
    keep = np.flatnonzero(np.abs(pw - p) <= band)
    return {"percentile": round(p, 4), "rule": RULE,
            "windows": [{"lat": float(windows["lat"][k]), "lon": float(windows["lon"][k]),
                         "slope": float(windows["slope"][k]), "name": windows["name"][k]} for k in keep]}


def zones_like(slope: float, ref_sorted: np.ndarray, zones: list[dict], band: float = BAND) -> list[dict]:
    """Earth zones whose median slope percentile is within `band` of a planetary window's, best typicality first."""
    p = percentile(ref_sorted, slope)
    out = [z for z in zones if z.get("slope_median") is not None
           and abs(percentile(ref_sorted, z["slope_median"]) - p) <= band]
    return sorted(out, key=lambda z: -(z.get("typicality") or 0))


def place_label(address: dict) -> str | None:
    """Short Earth place name: locality, region, country (Nominatim address fields)."""
    loc = next((address[k] for k in ("city", "town", "village", "hamlet", "municipality", "county") if address.get(k)), None)
    reg = next((address[k] for k in ("state", "region", "province", "state_district") if address.get(k)), None)
    parts = [p for p in (loc, reg, address.get("country")) if p]
    out: list[str] = []
    for p in parts:
        if p not in out:
            out.append(p)
    return ", ".join(out) or None


def _latin(text: str) -> bool:
    import unicodedata
    letters = [c for c in text if c.isalpha()]
    return bool(letters) and all("LATIN" in unicodedata.name(c, "") for c in letters)


def latin_label(label: str | None) -> str | None:
    """Keep the parts of a place name written in Latin script (OpenStreetMap gives some localities only in their local
    script). A part "Latin - local" keeps its Latin side; a label with no Latin part at all is kept as it is."""
    if not label:
        return label
    parts = []
    for p in label.split(", "):
        sides = [x for x in p.split(" - ") if _latin(x)]
        if sides:
            parts.append(sides[0])
    return ", ".join(parts) if parts else label


def relabel(path: Path) -> int:
    """Apply latin_label to the place names of an annotations file, without any new query; returns how many changed."""
    doc = json.loads(Path(path).read_text(encoding="utf-8"))
    n = 0
    for z in doc["zones"].values():
        for lang, v in (z.get("place") or {}).items():
            w = latin_label(v)
            if w != v:
                z["place"][lang] = w
                n += 1
    Path(path).write_text(json.dumps(doc, ensure_ascii=False, separators=(",", ":")) + chr(10), encoding="utf-8")
    return n


class GeoCache:
    """Reverse geocoding with a persistent cache keyed on 0.01° (about 1 km): a place is never queried twice."""

    def __init__(self, path: Path, fetch: Callable[[float, float, str], dict], sleep: Callable[[], None] = lambda: time.sleep(1.1)):
        self.path, self.fetch, self.sleep = Path(path), fetch, sleep
        self.data = json.loads(self.path.read_text(encoding="utf-8")) if self.path.exists() else {}
        self.queried = 0

    def label(self, lat: float, lon: float, lang: str) -> str | None:
        key = f"{round(lat, 2):.2f},{round(lon, 2):.2f},{lang}"
        if key not in self.data:
            self.sleep()                                          # Nominatim usage policy: at most 1 request per second
            try:
                res = self.fetch(round(lat, 2), round(lon, 2), lang)
                self.data[key] = place_label(res.get("address") or {})
            except OSError:
                return None                                       # not cached: retried by a later build
            self.queried += 1
        return self.data[key]

    def save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(self.data, ensure_ascii=False, indent=0) + "\n", encoding="utf-8")


def nominatim(lat: float, lon: float, lang: str) -> dict:
    import urllib.parse
    import urllib.request
    from discovery.dossier import UA
    q = urllib.parse.urlencode({"lat": f"{lat:.2f}", "lon": f"{lon:.2f}", "format": "jsonv2", "zoom": 10,
                                "addressdetails": 1, "accept-language": lang})
    req = urllib.request.Request(f"https://nominatim.openstreetmap.org/reverse?{q}", headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=30) as r:  # noqa: S310 (fixed host)
        return json.loads(r.read().decode())


# --- build of the annotations of a release (IO) -----------------------------------------------------------------

RADIUS_KM = {"moon": 1737.4, "mars": 3396.19}
POLAR = {"moon-psr", "moon-polar-lit-highlands", "moon-south-polar-cap-v2"}     # windows in LDEM_85S_40M x/y metres
MAX_WINDOWS = 4000                                    # windows kept per target for the globe (seeded sample)
SEED = 20261119


def planet_windows(target: str, profiles: Path, body: str) -> dict | None:
    """All windows of a target (slope), and their centres: from the profile windows, or the pit sites."""
    import pyarrow.parquet as pq
    if target == "moon-pits":
        d = json.loads((Path(__file__).resolve().parents[2] / "data/profiles/moon/moon-pits.json").read_text(encoding="utf-8"))
        s = [x for x in d.get("sites", []) if x.get("context_slope_mean") is not None]
        return {"lat": np.array([x["lat"] for x in s]), "lon": np.array([x["lon"] for x in s]) % 360,
                "slope": np.array([x["context_slope_mean"] for x in s]), "site_names": [x["name"] for x in s]}
    f = profiles / f"{target}.windows.parquet"
    if not f.exists():
        return None
    t = pq.read_table(f).to_pydict()
    if target in POLAR:
        lat, lon = polar_latlon(t["x_m"], t["y_m"], RADIUS_KM["moon"] * 1000, south=True)
    else:
        lat, lon = np.asarray(t["lat"], float), np.asarray(t["lon"], float) % 360
    return {"lat": lat, "lon": lon, "slope": np.asarray(t["slope_mean"], float)}


def build(releases: Path, rid: str, body: str, run: Path, cube: Path, profiles: Path, gazetteer: Path,
          geocache: Path, top: int = 60, geocode: bool = True) -> dict:
    from discovery import discover as d
    from discovery.compare import MASK_CLASSES, masked_windows
    from discovery.copernicus import tile_name
    import pyarrow.parquet as pq
    rel = releases / rid
    scen = json.loads((rel / "scenarios.json").read_text(encoding="utf-8"))["scenarios"]
    names = PlanetNames(read_gazetteer(gazetteer), RADIUS_KM[body])
    rng = np.random.default_rng(SEED)
    out: dict = {"release": rid, "body": body, "rule": RULE, "band": BAND, "targets": {}, "zones": {},
                 "sources": {"planet_names": "IAU Gazetteer of Planetary Nomenclature, USGS (public domain)",
                             "earth_names": "© OpenStreetMap contributors, ODbL (Nominatim); this names file is shared "
                                            "under the ODbL", "pit_names": "LROC Lunar Pits Atlas"}}
    targets = sorted({t for s in scen for t in s["assessed_targets"]})
    for t in targets:
        w = planet_windows(t, profiles, body)
        if w is None:
            out["targets"][t] = {"windows": None, "why": "planetary windows of this target are not stored"}
            continue
        ref = np.sort(w["slope"][np.isfinite(w["slope"])])
        k = np.arange(w["slope"].size)
        if k.size > MAX_WINDOWS:
            k = np.sort(rng.choice(k, MAX_WINDOWS, replace=False))
        nm = [w["site_names"][i] if "site_names" in w else names.name(float(w["lat"][i]), float(w["lon"][i])) for i in k]
        out["targets"][t] = {"ref_quantiles": np.quantile(ref, np.linspace(0, 1, 1001)).round(4).tolist(),
                             "n_windows": int(ref.size), "windows": {
                                 "lat": np.round(w["lat"][k], 4).tolist(), "lon": np.round(w["lon"][k], 4).tolist(),
                                 "slope": np.round(w["slope"][k], 3).tolist(), "name": nm}}
    # Earth zones: the best `top` zones of each target at the nominal tau and size
    grid = json.loads((rel / "release.json").read_text(encoding="utf-8"))["grid"]["nominal"]
    cols = ["lat", "lon", "slope_mean", "wc_covered", *MASK_CLASSES]

    def read_tile(scale):
        def read(tile):
            la, lo = (int(v) for v in tile.split(","))
            f = cube / scale / f"{tile_name(la, lo, d.PRODUCT)}.windows.parquet"
            if not f.exists():
                return None
            w = {k: v.to_numpy(zero_copy_only=False) for k, v in zip(cols, pq.read_table(f, columns=cols).columns)}
            w["hidden"] = masked_windows(w)[0].astype(float)
            return w
        return read

    geo = GeoCache(geocache, nominatim) if geocode else None
    for s in scen:
        for t in s["assessed_targets"]:
            f = rel / "zones" / s["id"] / t / f"t{grid['tau']}-m{grid['min_cells']}.json"
            runz = run / f"zones-{s['id']}-{t}.json"
            if not f.exists() or not runz.exists():
                continue
            zs = json.loads(f.read_text(encoding="utf-8"))["zones"][:top]
            rz = json.loads(runz.read_text(encoding="utf-8"))
            rz = rz["zones"] if isinstance(rz, dict) else rz
            zones = {}
            for z in zs:
                r = rz[z["rank"] - 1]
                assert abs(r["lat"] - z["lat"]) < 1e-6, "release and run zones differ"
                zones[z["id"]] = {"cells": r["cell_ids"], "tiles": z.get("tiles") or r.get("tiles", [])}
            slopes = zone_slopes(zones, read_tile(d.TARGET_SCALE[t]))
            for z in zs:
                rec = {"slope_median": slopes[z["id"]], "target": t, "lat": z["lat"], "lon": z["lon"],
                       "typicality": (z.get("typicality") or {}).get("median")}
                if geo:
                    rec["place"] = {lang: latin_label(geo.label(z["lat"], z["lon"], lang)) for lang in ("en", "fr")}
                out["zones"][z["id"]] = rec
            if geo:
                geo.save()
    return out


def main(argv=None) -> int:
    import argparse
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--releases", type=Path, default=Path("/data/releases"))
    ap.add_argument("--release", required=True)
    ap.add_argument("--body", choices=["moon", "mars"], required=True)
    ap.add_argument("--run", type=Path, required=True)
    ap.add_argument("--cube", type=Path, default=Path("/data/cube"))
    ap.add_argument("--profiles", type=Path, required=True)
    ap.add_argument("--gazetteer", type=Path, required=True)
    ap.add_argument("--geocache", type=Path, default=Path("/data/names/nominatim-cache.json"))
    ap.add_argument("--top", type=int, default=60)
    ap.add_argument("--no-geocode", action="store_true")
    a = ap.parse_args(argv)
    res = build(a.releases, a.release, a.body, a.run, a.cube, a.profiles, a.gazetteer, a.geocache, a.top, not a.no_geocode)
    dest = a.releases / "annotations" / f"{a.release}.json"
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps(res, ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8")
    n_slope = sum(z["slope_median"] is not None for z in res["zones"].values())
    print(dest, len(res["zones"]), "zones,", n_slope, "with a slope;", {t: v.get("n_windows") for t, v in res["targets"].items()})
    return 0


if __name__ == "__main__":
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    sys.exit(main())
