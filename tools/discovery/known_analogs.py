"""Known analog sites against the criteria science uses, and against our protocol (task T53).

Sites and features: The Catalogue of Planetary Analogues (Preston, Grady and Barber, Open University for ESA, 2012),
extracted in data/validation/known-analogs/catalogue.yaml. Criteria and pass rules: criteria.yaml in the same folder.
Both were frozen (commit d075808) before any value was read at the sites.

For each catalogue feature with an Earth layer, the rule is applied at every catalogue point:
- rocks: the Macrostrat map unit at the point and 8 points at 1.6 km (cached carto tiles of geology.py);
- ground ice and aridity: the context values of the 5 km cell holding the point (run-002 context.parquet).
Our current protocol is read at the same cells: the median typicality for the target each feature is closest to.

    python discovery/known_analogs.py run --data <earthmoon-data> --out ../data/runs/known-analogs/results.json
"""
from __future__ import annotations

import json
import math
import re
from functools import lru_cache
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
FOLDER = ROOT / "data/validation/known-analogs"
TAU = 0.5                                   # zone rule of protocol v3: a cell is a candidate at median typicality >= 0.5
RECOVERY = 0.75                             # pass rules of criteria.yaml
MIN_CHAPTERS = 3
MAX_FALSE_ALARMS = 1
GATE_ABOVE = 0.10
ICE_PROB = 0.5
ARID_BELOW = 0.2
ORDER = ("strict", "found", "absent", "unknown")


class NotAPoint(ValueError):
    """The catalogue gives a range, a region or nothing, not a point."""


# --- coordinates ----------------------------------------------------------------------------------------------

_PRE = re.compile(r"(?<![A-Za-z])([NSEW])\s+(\d+(?:\.\d+)?)\s*°\s*(?:(\d+(?:\.\d+)?)\s*'\s*)?(?:(\d+(?:\.\d+)?)\s*\"\s*)?")
_SUF = re.compile(r"(\d+(?:\.\d+)*)\s*°?\s*(?:(\d+(?:\.\d+)?)\s*'\s*)?(?:(\d+(?:\.\d+)?)\s*\"\s*)?([NSEW])(?![a-z])")
_SIGNED = re.compile(r"(-?\d+(?:\.\d+)?)\s*°\s*,\s*(-?\d+(?:\.\d+)?)\s*°")


def _norm(text: str) -> str:
    t = text.replace("′", "'").replace("’", "'").replace("‘", "'").replace("″", '"').replace("”", '"').replace("“", '"')
    return re.sub(r"(\d),(\d)", r"\1.\2", t)                      # decimal comma: 21,7 -> 21.7


def _dms(deg: str, minutes: str | None, seconds: str | None) -> float:
    if deg.count(".") >= 2:                                         # 75.21.5 or 75.21.26.8: degrees.minutes.seconds
        p = deg.split(".")
        deg, minutes, seconds = p[0], p[1], ".".join(p[2:])
    return float(deg) + float(minutes or 0) / 60 + float(seconds or 0) / 3600


def parse_coord(text: str) -> tuple[float, float]:
    """Latitude and longitude (degrees, east and north positive) of a coordinate as the catalogue prints it."""
    t = _norm(text or "")
    if not t.strip() or re.search(r"\bto\b", t):
        raise NotAPoint(text)
    comps = [(m.group(1), _dms(m.group(2), m.group(3), m.group(4))) for m in _PRE.finditer(t)]
    if len(comps) < 2:
        comps = [(m.group(4), _dms(m.group(1), m.group(2), m.group(3))) for m in _SUF.finditer(t)]
    if len(comps) < 2:
        m = _SIGNED.search(t)
        if not m:
            raise NotAPoint(text)
        return float(m.group(1)), float(m.group(2))
    lat = [v * (-1 if h == "S" else 1) for h, v in comps if h in "NS"]
    lon = [v * (-1 if h == "W" else 1) for h, v in comps if h in "EW"]
    if not lat or not lon:
        raise NotAPoint(text)
    return lat[0], lon[0]


# --- frozen inputs --------------------------------------------------------------------------------------------

@lru_cache(maxsize=1)
def catalogue() -> dict:
    return yaml.safe_load((FOLDER / "catalogue.yaml").read_text(encoding="utf-8"))


@lru_cache(maxsize=1)
def criteria() -> dict:
    return yaml.safe_load((FOLDER / "criteria.yaml").read_text(encoding="utf-8"))


def load_sites() -> tuple[list[dict], list[dict]]:
    """Usable catalogue points (chapter, name, lat, lon) and the excluded entries with their reason."""
    sites, excluded = [], []
    for ch, c in sorted(catalogue()["chapters"].items()):
        entries = [{"name": c["name"], **{k: c[k] for k in ("at", "excluded", "note") if k in c}}]
        entries += c.get("sites", [])
        for e in entries:
            if e.get("excluded"):
                excluded.append({"chapter": ch, "name": e["name"], "at": e["at"], "reason": e["excluded"]})
                continue
            lat, lon = parse_coord(e.get("fix") or e["at"])
            sites.append({"chapter": ch, "chapter_name": c["name"], "name": e["name"], "lat": lat, "lon": lon,
                          **({"note": e["note"]} if e.get("note") else {})})
    return sites, excluded


def chapters_of(body: str, feature: str) -> list[int]:
    if feature == "present-day-aridity":
        return list(criteria()["context"]["aridity"]["chapters"])
    return list(catalogue()["directory"][body].get(feature, []))


def feature_rules() -> list[dict]:
    """One row per (body, feature): its rule kind and name. Features without a layer have kind 'no data'."""
    k = criteria()
    rows = []
    for rule, spec in k["lithology"].items():
        for body, feats in spec["features"].items():
            rows += [{"body": body, "feature": f, "kind": "rock", "rule": rule} for f in feats]
    for rule, spec in k["context"].items():
        for body, feats in spec["features"].items():
            rows += [{"body": body, "feature": f, "kind": "context", "rule": rule} for f in feats]
    for group, spec in k["no_data"].items():
        for body, feats in spec["features"].items():
            rows += [{"body": body, "feature": f, "kind": "no data", "rule": group, "needs": spec["needs"]} for f in feats]
    return rows


# --- rules ----------------------------------------------------------------------------------------------------

@lru_cache(maxsize=1)
def rock_rules() -> dict[str, set[str]]:
    d = json.loads((ROOT / "data/geology/macrostrat-lithologies.json").read_text(encoding="utf-8"))
    out = {}
    for rule, spec in criteria()["lithology"].items():
        if "macrostrat_type" in spec:
            out[rule] = {x["name"].lower() for x in d["lithologies"] if x.get("type") == spec["macrostrat_type"]}
        else:
            out[rule] = {n.lower() for n in spec["names"]}
    return out


def _generic() -> set[str]:
    from discovery.geology import GENERIC
    return set(GENERIC) | {"sedimentary", "metasedimentary"}


def _point_state(text: str | None, names: set[str]) -> str:
    from discovery.geology import lith_names
    if text is None:
        return "unknown"
    found, major = lith_names(text)
    considered = major or found
    if considered and considered[0] in names:
        return "strict"
    if names & set(found):
        return "found"
    if not found or set(found) <= _generic():
        return "unknown"
    return "absent"


def _best(states: list[str]) -> str:
    for s in ORDER:
        if s in states:
            return s
    return "unknown"


def rock_state(texts: list[str | None], names: set[str]) -> str:
    """State of a rock at a set of sample points: strict, found, absent or unknown (criteria.yaml)."""
    return _best([_point_state(t, names) for t in texts])


def chapter_state(states: list[str]) -> str:
    """A feature is found at a chapter when one of its points has it."""
    return _best(states)


def _missing(v) -> bool:
    return v is None or (isinstance(v, float) and math.isnan(v))


def ground_ice(prob) -> str:
    return "unknown" if _missing(prob) else ("strict" if float(prob) >= ICE_PROB else "absent")


def arid(index) -> str:
    return "unknown" if _missing(index) else ("strict" if float(index) < ARID_BELOW else "absent")


def recovery(states: dict) -> dict:
    with_data = [s for s in states.values() if s != "unknown"]
    found = sum(1 for s in with_data if s in ("strict", "found"))
    share = found / len(with_data) if with_data else None
    if len(with_data) < MIN_CHAPTERS:
        verdict = "not testable"
    else:
        verdict = "recovered" if share >= RECOVERY else "not recovered"
    return {"with_data": len(with_data), "found": found, "share": share, "verdict": verdict}


def discrimination(false_alarms: int, base_rate: float | None) -> str:
    if false_alarms > MAX_FALSE_ALARMS:
        return "false alarms"
    if base_rate is None:
        return "base rate not computed"
    return "gate only" if base_rate > GATE_ABOVE else "discriminating"


def recognised(median) -> bool | None:
    return None if _missing(median) else bool(float(median) >= TAU)


# --- data access ----------------------------------------------------------------------------------------------

def units_from_tile(data: bytes, lats, lons) -> list[str | None]:
    """Lithology text of the map unit holding each point, from one carto tile; None where no unit."""
    import mapbox_vector_tile
    import numpy as np
    from shapely import STRtree, points
    from shapely.geometry import shape
    from discovery.geology import tile_xy
    out: list[str | None] = [None] * len(lats)
    if not data:
        return out
    feats = mapbox_vector_tile.decode(data, default_options={"y_coord_down": True}).get("units", {}).get("features", [])
    geoms, liths = [], []
    for f in feats:
        try:
            g = shape(f["geometry"])
        except Exception:  # noqa: BLE001 - a malformed polygon of a tile is skipped, as in geology.py
            continue
        if g.is_valid and not g.is_empty:
            geoms.append(g)
            liths.append(f["properties"].get("lith"))
    if not geoms:
        return out
    _, _, px, py = tile_xy(np.asarray(lats, float), np.asarray(lons, float))
    pi, gi = STRtree(geoms).query(points(np.c_[px, py]), predicate="within")
    for p, g in zip(pi.tolist(), gi.tolist()):
        if out[p] is None:
            out[p] = liths[g]
    return out


def units_at(lat: float, lon: float, cache: Path) -> list[str | None]:
    """Unit texts at the point and its 8 neighbours at 1.6 km; a missing tile is fetched once and cached."""
    import numpy as np
    from discovery.geology import TILE_URL, Z, _fetch, sample_points, tile_xy
    slat, slon = sample_points([lat], [lon])
    slat, slon = slat.ravel(), slon.ravel()
    x, y, _, _ = tile_xy(slat, slon)
    out: list[str | None] = [None] * len(slat)
    for tx, ty in sorted(set(zip(x.tolist(), y.tolist()))):
        p = cache / str(Z) / str(tx) / f"{ty}.mvt"
        if not p.exists():
            p.parent.mkdir(parents=True, exist_ok=True)
            _fetch((p, TILE_URL.format(z=Z, x=tx, y=ty)))
        data = p.read_bytes() if p.exists() else b""
        idx = np.flatnonzero((x == tx) & (y == ty))
        for i, t in zip(idx.tolist(), units_from_tile(data, slat[idx], slon[idx])):
            out[i] = t
    return out


def _cell_rows(path: Path, cells: list[int], columns: list[str]) -> dict[int, dict]:
    import pyarrow.compute as pc
    import pyarrow.parquet as pq
    t = pq.read_table(path, columns=["cell", *columns])
    typ = t.schema.field("cell").type
    import pyarrow as pa
    keys = pa.array([str(c) if pa.types.is_string(typ) else int(c) for c in cells], type=typ)
    t = t.filter(pc.is_in(t.column("cell"), value_set=keys))
    rows = t.to_pylist()
    return {int(r.pop("cell")): r for r in rows}


def _column(path: Path, column: str):
    import numpy as np
    import pyarrow.parquet as pq
    a = pq.read_table(path, columns=[column]).column(0).to_numpy(zero_copy_only=False)
    return np.asarray(a, dtype=float)


def _base_rates(data: Path) -> dict:
    """Share of land cells where the strict rule holds, from existing run files (no new global pass)."""
    import numpy as np
    out = {}
    g = data / "run002" / "geology.parquet"
    out["basalt"] = float(np.mean(_column(g, "geo:mare:match") > 0))
    out["anorthosite"] = float(np.mean(_column(g, "geo:highland:match") > 0))
    gm = data / "run-mars-002" / "geology.parquet"
    out["volcanic"] = float(np.mean((_column(gm, "geo:mars-volcanic:match") + _column(gm, "geo:mars-volcanic:partial")) > 0))
    c = data / "run002" / "context.parquet"
    ice = _column(c, "ctx:permafrost_prob")
    out["ground-ice"] = float(np.mean(np.nan_to_num(ice, nan=0.0) >= ICE_PROB))
    ai = _column(c, "ctx:aridity_index")
    out["aridity"] = float(np.mean(np.nan_to_num(ai, nan=np.inf) < ARID_BELOW))
    out["_note"] = ("shares of all assessed land cells; rock rules use the first-listed (strict) rule of geology.py; "
                    "a missing value counts as not passing")
    return out


def _percentiles(path: Path, target: str, values: dict[int, float]) -> dict[int, float | None]:
    from discovery.discover import percentile_rank
    col = _column(path, f"{target}:median")
    return {c: (None if _missing(v) else round(percentile_rank(v, col), 1)) for c, v in values.items()}


def assess(data: Path) -> dict:
    """Every rule at every catalogue point and negative, our protocol at the same cells, and the verdicts."""
    from discovery.discover import global_cell
    import numpy as np
    sites, excluded = load_sites()
    neg = yaml.safe_load((ROOT / "data/validation/negatives.yaml").read_text(encoding="utf-8"))["negatives"]
    negatives = [{"name": f"negative {i + 1} ({n['class_name']})", "lat": n["lat"], "lon": n["lon"]} for i, n in enumerate(neg)]
    points = sites + negatives
    lat = np.array([p["lat"] for p in points])
    lon = np.array([p["lon"] for p in points])
    cells = global_cell(lat, lon).astype(int).tolist()
    for p, c in zip(points, cells):
        p["cell"] = c
    cache = data / "macrostrat"
    rules = rock_rules()
    for p in points:
        texts = units_at(p["lat"], p["lon"], cache)
        p["units"] = sorted({t for t in texts if t})
        p["rocks"] = {r: rock_state(texts, names) for r, names in rules.items()}
    ctx = _cell_rows(data / "run002" / "context.parquet", cells, ["ctx:permafrost_prob", "ctx:aridity_index"])
    for p in points:
        r = ctx.get(p["cell"], {})
        p["context"] = {"ground-ice": ground_ice(r.get("ctx:permafrost_prob")), "aridity": arid(r.get("ctx:aridity_index")),
                        "permafrost_prob": r.get("ctx:permafrost_prob"), "aridity_index": r.get("ctx:aridity_index")}
    # our protocol at the same cells
    proto = {}
    for body, spec in criteria()["current_protocol"].items():
        if body not in ("moon", "mars"):
            continue
        run = data / ("run002" if spec["run"] == "run-002" else spec["run"])
        targets = sorted(set(spec["targets"].values()))
        rows = _cell_rows(run / "cells.parquet", [p["cell"] for p in sites],
                          [f"{t}:median" for t in targets] + ["confidence"])
        pct = {t: _percentiles(run / "cells.parquet", t, {c: r.get(f"{t}:median") for c, r in rows.items()}) for t in targets}
        proto[body] = {"run": spec["run"], "targets": spec["targets"], "rows": rows, "percentiles": pct}
    # verdicts per feature
    base = _base_rates(data)
    features = []
    for fr in feature_rules():
        body, feat = fr["body"], fr["feature"]
        chs = chapters_of(body, feat)
        row = {**fr, "chapters": chs}
        if fr["kind"] != "no data":
            def state(p):
                return p["rocks"][fr["rule"]] if fr["kind"] == "rock" else p["context"][fr["rule"]]
            per_ch = {ch: chapter_state([state(p) for p in sites if p["chapter"] == ch]) for ch in chs}
            per_ch = {ch: s for ch, s in per_ch.items() if any(p["chapter"] == ch for p in sites)}
            others = {ch: chapter_state([state(p) for p in sites if p["chapter"] == ch])
                      for ch in sorted({p["chapter"] for p in sites}) if ch not in chs}
            fa = sum(1 for p in negatives if state(p) in ("strict", "found"))
            br = base.get(fr["rule"])
            row.update({"per_chapter": per_ch, "recovery": recovery(per_ch),
                        "other_chapters_found": sum(1 for s in others.values() if s in ("strict", "found")),
                        "other_chapters_with_data": sum(1 for s in others.values() if s != "unknown"),
                        "false_alarms": fa, "base_rate": br, "discrimination": discrimination(fa, br)})
        target = criteria()["current_protocol"].get(body, {}).get("targets", {}).get(feat)
        if target:
            pr = proto[body]
            cur = {}
            for ch in chs:
                vals = [(p["name"], pr["rows"].get(p["cell"], {}).get(f"{target}:median"),
                         pr["percentiles"][target].get(p["cell"]), pr["rows"].get(p["cell"], {}).get("confidence"))
                        for p in sites if p["chapter"] == ch]
                if vals:
                    cur[ch] = [{"site": n, "median": None if _missing(m) else round(float(m), 3), "percentile": q,
                                "confidence": c, "recognised": recognised(m)} for n, m, q, c in vals]
            rec = [any(v["recognised"] for v in vs) for vs in cur.values() if any(v["recognised"] is not None for v in vs)]
            row["current_protocol"] = {"target": target, "per_chapter": cur,
                                       "recognised_chapters": sum(rec), "chapters_with_value": len(rec)}
        features.append(row)
    return {"task": "T53", "frozen_in": "d075808", "sites": sites, "excluded": excluded, "negatives": negatives,
            "base_rates": base, "features": features}


def main(argv=None) -> int:
    import argparse
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("run")
    r.add_argument("--data", required=True, type=Path)
    r.add_argument("--out", required=True, type=Path)
    a = ap.parse_args(argv)
    res = assess(a.data)
    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_text(json.dumps(res, indent=1, ensure_ascii=False, default=str) + "\n", encoding="utf-8")
    print(json.dumps([{k: f.get(k) for k in ("body", "feature", "kind", "recovery", "discrimination")} for f in res["features"]],
                     ensure_ascii=False, default=str))
    return 0


if __name__ == "__main__":
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    raise SystemExit(main())
