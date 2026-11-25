"""Geology dimension (T46): the lithology of Earth map units against lunar environments.

Source: Macrostrat (CC-BY 4.0), `carto` vector tiles at zoom 8, which hold the finest map unit Macrostrat has at each
place. Crosswalk: expert decision E17 (docs/wiki/methods/geology-crosswalk.md), delegated by David to Claude on
20/11/2026 and to be reviewed by lunar geologists before G5.

States of a map unit for a lunar environment: match, partial, no match, unresolved. A unit without a lithology, or
with only a generic one ("igneous", "plutonic", "mafic"...), is unresolved: never "no match".
"""
from __future__ import annotations

import json
import re
from functools import lru_cache
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
GROUPS = ("highland", "mare", "pits", "mars-volcanic")
TARGET_GROUP = {
    "moon-polar-lit-highlands": "highland", "moon-psr": "highland", "moon-south-polar-cap-v2": "highland",
    "moon-persistently-lit": "highland", "moon-mare-plains": "mare", "moon-pits": "pits",
    "mars-volcanic-plains": "mars-volcanic",
}
# E17, rows of docs/wiki/methods/geology-crosswalk.md
CROSSWALK = {
    "highland": {"match": {"anorthosite"},
                 "partial": {"norite", "troctolite", "gabbro", "metagabbro", "metaanorthosite"}},
    "mare": {"match": {"basalt"},
             "partial": {"dolerite", "diabase", "metabasalt", "basanite", "picrite", "mafite"}},
    "pits": {"match": set(), "partial": {"basalt"}},
}
# names that say only a class or a type: they cannot tell anorthosite or basalt from other rocks
GENERIC = {"igneous", "plutonic", "volcanic", "mafic", "ultramafic", "metamorphic", "metaigneous", "metavolcanic"}


def _macrostrat_volcanic() -> set[str]:
    """Lithologies Macrostrat itself types as volcanic (data/geology/macrostrat-lithologies.json)."""
    d = json.loads((ROOT / "data/geology/macrostrat-lithologies.json").read_text(encoding="utf-8"))
    return {x["name"].lower() for x in d["lithologies"] if x.get("type") == "volcanic"}


# E20 (David, 20/11/2026): the volcanic units of the Tanaka 2014 Mars map match Earth basalt; the other volcanic rocks
# (Macrostrat's own type "volcanic", not a hand-made list) are partial; class names stay unresolved
CROSSWALK["mars-volcanic"] = {"match": {"basalt"}, "partial": _macrostrat_volcanic() - {"basalt"} - GENERIC}
# words of map legends that name a Macrostrat lithology in another form (whole words only)
ALIASES = {"granitic": "granite", "gabbroic": "gabbro", "anorthositic": "anorthosite", "tholeiite": "basalt",
           "tholeiitic basalt": "basalt", "metaanorthosite": "metaanorthosite", "noritic": "norite",
           # compound names: the noun names the rock, the adjective qualifies it (read whole, before the single words)
           "anorthositic gabbro": "gabbro", "gabbroic anorthosite": "anorthosite", "anorthositic norite": "norite",
           "noritic anorthosite": "anorthosite", "anorthositic gneiss": "gneiss", "granitic gneiss": "gneiss",
           "gabbroic gneiss": "gneiss", "basaltic andesite": "andesite", "olivine basalt": "basalt", "alkali basalt": "basalt"}


@lru_cache(maxsize=1)
def _names() -> tuple[str, ...]:
    d = json.loads((ROOT / "data/geology/macrostrat-lithologies.json").read_text(encoding="utf-8"))
    known = {x["name"].lower() for x in d["lithologies"]} | set(ALIASES)
    return tuple(sorted(known, key=len, reverse=True))           # longest first: "basaltic andesite" before "andesite"


def _find(text: str) -> list[str]:
    t = text.lower()
    hits: list[tuple[int, str]] = []
    taken = [False] * len(t)
    for name in _names():
        for m in re.finditer(rf"(?<![a-z]){re.escape(name)}(?![a-z])", t):
            if any(taken[m.start():m.end()]):
                continue
            for k in range(m.start(), m.end()):
                taken[k] = True
            hits.append((m.start(), ALIASES.get(name, name)))
    out: list[str] = []
    for _, n in sorted(hits):
        if n not in out:
            out.append(n)
    return out


def lith_names(text: str | None) -> tuple[list[str], list[str] | None]:
    """Lithology names in a map-unit text, in order, and the Major ones when the text marks them (Major:{...})."""
    text = text or ""
    names = _find(text)
    m = re.search(r"major:\s*\{([^}]*)\}", text, flags=re.IGNORECASE)
    return names, (_find(m.group(1)) if m else None)


def _state(name: str, group: str) -> str:
    if name in CROSSWALK[group]["match"]:
        return "match"
    if name in CROSSWALK[group]["partial"]:
        return "partial"
    return "unresolved" if name in GENERIC else "no match"


def unit_state(text: str | None, group: str) -> tuple[str, bool]:
    """State of a map unit for a group of lunar environments, and whether the unit mixes rock families.

    E17, as amended on 20/11/2026 after the first global run: a unit that lists the lunar rock among other rock
    families counts as match or partial only when the map lists that rock first; otherwise the unit contains the rock
    somewhere and is unresolved (large undivided units of small-scale maps named every rock of a shield)."""
    names, major = lith_names(text)
    considered = major if major else names
    states = [_state(n, group) for n in considered]
    specific = [s for s in states if s != "unresolved"]
    if not specific:
        return "unresolved", False
    mixed = "no match" in specific and ("match" in specific or "partial" in specific)
    for best in ("match", "partial"):
        if best in specific:
            if mixed and specific[0] != best:
                return "unresolved", True
            return best, mixed
    return "no match", False


# --- sampling and tiles --------------------------------------------------------------------------------------

Z = 8                      # carto tiles at zoom 8 hold the finest unit Macrostrat draws at each place (measured 20/11/2026)
OFFSET_KM = 1.6            # 8 samples around the centre, inside the 5 km cell
STATES = ("match", "partial", "no match", "unresolved")


def sample_points(lat, lon):
    """Centre and 8 points around it (3 x 3 at 1.6 km) for each cell: arrays (n, 9)."""
    import numpy as np
    lat = np.asarray(lat, float)[:, None]
    lon = np.asarray(lon, float)[:, None]
    d = np.array([0, -1, 1])
    dy, dx = (g.ravel() for g in np.meshgrid(d, d, indexing="ij"))
    order = np.argsort((dy != 0) | (dx != 0), kind="stable")           # centre first
    dy, dx = dy[order], dx[order]
    dlat = dy * OFFSET_KM / 111.2
    dlon = dx * OFFSET_KM / (111.2 * np.maximum(np.cos(np.radians(lat)), 0.05))
    return lat + dlat, lon + dlon


def tile_xy(lat, lon, z: int = Z):
    """Web Mercator tile and pixel (extent 4096) of points."""
    import numpy as np
    n = 2 ** z
    lat = np.clip(np.asarray(lat, float), -85.0511, 85.0511)
    xf = (np.asarray(lon, float) + 180) / 360 * n
    r = np.radians(lat)
    yf = (1 - np.log(np.tan(r) + 1 / np.cos(r)) / np.pi) / 2 * n
    x, y = np.floor(xf).astype(int) % n, np.clip(np.floor(yf).astype(int), 0, n - 1)
    return x, y, (xf - np.floor(xf)) * 4096, (yf - np.floor(yf)) * 4096


def cell_shares(states: list) -> dict:
    """Share of the samples of a cell in each state; None (no map unit at the sample) counts as 'no map'."""
    n = len(states) or 1
    out = {s: sum(1 for x in states if x == s) / n for s in STATES}
    out["no map"] = sum(1 for x in states if x is None) / n
    return out


def classify_points(data: bytes, z: int, x: int, y: int, lats, lons) -> dict:
    """State of each point for every group of lunar environments, from one carto tile; None where no unit."""
    import mapbox_vector_tile
    import numpy as np
    from shapely import STRtree, points
    from shapely.geometry import shape
    n = len(lats)
    out = {g: [None] * n for g in GROUPS} | {"source_id": [None] * n, "mixed": [False] * n}
    if not data:
        return out
    feats = mapbox_vector_tile.decode(data, default_options={"y_coord_down": True}).get("units", {}).get("features", [])
    geoms, props = [], []
    for f in feats:
        try:
            g = shape(f["geometry"])
        except Exception:  # noqa: BLE001 - a malformed polygon of a tile is skipped, never fatal
            continue
        if g.is_valid and not g.is_empty:
            geoms.append(g)
            props.append(f["properties"])
    if not geoms:
        return out
    _, _, px, py = tile_xy(np.asarray(lats), np.asarray(lons), z)
    pts = points(np.c_[px, py])
    pi, gi = STRtree(geoms).query(pts, predicate="within")
    first: dict[int, int] = {}
    for p, g in zip(pi.tolist(), gi.tolist()):
        first.setdefault(p, g)
    states = {}
    for p, g in first.items():
        if g not in states:
            states[g] = {grp: unit_state(props[g].get("lith"), grp) for grp in GROUPS}
        for grp in GROUPS:
            out[grp][p] = states[g][grp][0]
        out["mixed"][p] = any(states[g][grp][1] for grp in GROUPS)
        out["source_id"][p] = props[g].get("source_id")
    return out


# --- command line: harvest the tiles once, then assess every cell of a run ---------------------------------------

UA = "earthmoon-research/1.0"
TILE_URL = "https://tiles.macrostrat.org/carto/{z}/{x}/{y}"
CODE = {None: 0, "match": 1, "partial": 2, "no match": 3, "unresolved": 4}


def _cells(run: Path):
    import numpy as np
    import pyarrow.parquet as pq
    t = pq.read_table(run / "cells.parquet", columns=["cell", "lat", "lon"])
    return (t.column("cell").to_numpy(zero_copy_only=False).astype(str),
            t.column("lat").to_numpy(zero_copy_only=False).astype(float),
            t.column("lon").to_numpy(zero_copy_only=False).astype(float)) if t.num_rows else (np.array([]),) * 3


def _fetch(task) -> tuple[str, int, str | None]:
    import time
    import urllib.request
    path, url = task
    for attempt in range(4):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            data = urllib.request.urlopen(req, timeout=120).read()
            tmp = path.with_suffix(".part")
            tmp.write_bytes(data)
            tmp.replace(path)
            return str(path), len(data), None
        except Exception as e:  # noqa: BLE001 - retried, then reported
            err = f"{type(e).__name__}: {e}"
            time.sleep(2 ** attempt)
    return str(path), 0, err


def harvest(run: Path, cache: Path, workers: int = 4) -> dict:
    """Download the zoom-8 carto tiles that hold a sample point of a cell of the run (cached: run again to resume)."""
    import numpy as np
    from concurrent.futures import ThreadPoolExecutor
    _, lat, lon = _cells(run)
    slat, slon = sample_points(lat, lon)
    x, y, _, _ = tile_xy(slat.ravel(), slon.ravel())
    tiles = np.unique(np.c_[x, y], axis=0)
    todo = []
    for tx, ty in tiles.tolist():
        p = cache / str(Z) / str(tx) / f"{ty}.mvt"
        if not p.exists():
            p.parent.mkdir(parents=True, exist_ok=True)
            todo.append((p, TILE_URL.format(z=Z, x=tx, y=ty)))
    done, failed, size = 0, [], 0
    with ThreadPoolExecutor(max_workers=workers) as pool:
        for path, n, err in pool.map(_fetch, todo):
            done += 1
            size += n
            if err:
                failed.append((path, err))
            if done % 500 == 0:
                print(f"{done}/{len(todo)} tiles, {size / 1e6:.0f} MB", flush=True)
    return {"tiles": int(len(tiles)), "downloaded": done - len(failed), "failed": failed[:20], "n_failed": len(failed), "bytes": size}


def _assess_tiles(task):
    import numpy as np
    cache, items = task
    res = []
    for (tx, ty), idx, la, lo in items:
        p = cache / str(Z) / str(tx) / f"{ty}.mvt"
        data = p.read_bytes() if p.exists() else b""
        out = classify_points(data, Z, tx, ty, la, lo)
        codes = np.array([[CODE[out[g][k]] for g in GROUPS] for k in range(len(idx))], dtype=np.int8)
        src = np.array([s if s is not None else -1 for s in out["source_id"]], dtype=np.int32)
        res.append((idx, codes, src, np.array(out["mixed"], bool), p.exists()))
    return res


def assess(run: Path, cache: Path, out: Path, workers: int = 8) -> dict:
    """Shares of each state per cell and per group of lunar environments (9 samples per cell), written as parquet."""
    import numpy as np
    import pyarrow as pa
    import pyarrow.parquet as pq
    from collections import defaultdict
    from concurrent.futures import ProcessPoolExecutor
    cell, lat, lon = _cells(run)
    slat, slon = sample_points(lat, lon)
    flat_lat, flat_lon = slat.ravel(), slon.ravel()
    x, y, _, _ = tile_xy(flat_lat, flat_lon)
    groups: dict = defaultdict(list)
    for i, key in enumerate(zip(x.tolist(), y.tolist())):
        groups[key].append(i)
    items = [(k, np.array(v), flat_lat[v], flat_lon[v]) for k, v in groups.items()]
    chunks = [items[i::workers * 8] for i in range(workers * 8)]
    codes = np.zeros((flat_lat.size, len(GROUPS)), np.int8)
    src = np.full(flat_lat.size, -1, np.int32)
    mixed = np.zeros(flat_lat.size, bool)
    missing_tiles = 0
    with ProcessPoolExecutor(max_workers=workers) as pool:
        for res in pool.map(_assess_tiles, [(cache, c) for c in chunks if c]):
            for idx, c, s, m, present in res:
                codes[idx], src[idx], mixed[idx] = c, s, m
                missing_tiles += 0 if present else 1
    n = cell.size
    codes = codes.reshape(n, 9, len(GROUPS))
    cols = {"cell": pa.array(cell), "geo:source_id": pa.array(src.reshape(n, 9)[:, 0]),
            "geo:mixed_share": pa.array(mixed.reshape(n, 9).mean(axis=1).astype(np.float32))}
    for gi, g in enumerate(GROUPS):
        for state, code in (("match", 1), ("partial", 2), ("no_match", 3), ("unresolved", 4), ("no_map", 0)):
            cols[f"geo:{g}:{state}"] = pa.array((codes[:, :, gi] == code).mean(axis=1).astype(np.float32))
    pq.write_table(pa.table(cols), out, compression="zstd")
    summary = {"cells": int(n), "tiles": len(items), "missing_tiles": missing_tiles,
               "no_map_share": float((codes[:, :, 0] == 0).mean())}
    for gi, g in enumerate(GROUPS):
        summary[g] = {s: round(float((codes[:, :, gi] == c).mean()), 4) for s, c in
                      (("match", 1), ("partial", 2), ("no match", 3), ("unresolved", 4), ("no map", 0))}
    return summary


def main(argv=None) -> int:
    import argparse
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("step", choices=["harvest", "assess"])
    ap.add_argument("--run", type=Path, required=True)
    ap.add_argument("--cache", type=Path, default=Path("/data/macrostrat"))
    ap.add_argument("--workers", type=int, default=4)
    a = ap.parse_args(argv)
    if a.step == "harvest":
        s = harvest(a.run, a.cache, a.workers)
    else:
        s = assess(a.run, a.cache, a.run / "geology.parquet", a.workers)
        (a.run / "geology.json").write_text(json.dumps(s, indent=1) + "\n")
    print(json.dumps(s, indent=1))
    return 0 if not s.get("n_failed") else 1


if __name__ == "__main__":
    import sys
    sys.exit(main())
