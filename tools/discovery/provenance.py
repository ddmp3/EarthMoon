"""Provenance of every Earth tile of a release, and the changes between two releases (T52, David 23/11/2026).

For researchers: which source files (with their version and date at the source) each tile was computed from, when it
was computed, with which code, and in which release it last changed. With incremental updates a release mixes tiles
computed at different dates, so this is published with every release (`provenance.json`, `changes.json`).

Compact form: source items are stored once in `items`; each tile lists the indices of the items it read.
"""
from __future__ import annotations

import json
from pathlib import Path

NOT_RECORDED = "not recorded (computed before T52)"


def _records(cube: Path, scale: str) -> dict:
    out = {}
    f = cube / scale / "manifest.jsonl"
    if not f.exists():
        return out
    with f.open(encoding="utf-8") as fh:
        for line in fh:
            if line.strip():
                r = json.loads(line)
                out[f"{r['lat']},{r['lon']}"] = r                 # the last record of a tile wins
    return out


def build(cube: Path, scales: list[str], release: str, previous: dict | None) -> dict:
    items: list = []
    index: dict = {}
    tiles: dict = {}
    for scale in scales:
        for key, r in _records(Path(cube), scale).items():
            ids = []
            for item, v in sorted((r.get("inputs") or {}).items()):
                sig = (item, v.get("etag"), v.get("size"), v.get("last_modified"), v.get("sha256"))
                if sig not in index:
                    index[sig] = len(items)
                    items.append({"item": item, "etag": v.get("etag"), "size": v.get("size"),
                                  "last_modified": v.get("last_modified"), "sha256": v.get("sha256")})
                ids.append(index[sig])
            out_sha = (r.get("outputs") or {}).get("windows")
            tiles.setdefault(key, {})[scale] = [r.get("computed_at"), r.get("code"), r.get("commit"), out_sha, ids]
    last = {}
    for key, sc in tiles.items():
        prev_t = ((previous or {}).get("tiles") or {}).get(key)
        same = prev_t is not None and all(prev_t.get(s, [None] * 4)[3] == v[3] for s, v in sc.items()) and \
            set(prev_t) == set(sc)
        last[key] = (previous or {}).get("last_changed_in", {}).get(key, release) if same else release
    return {"release": release, "scales": scales, "items": items, "tiles": tiles, "last_changed_in": last}


def tile(p: dict, key: str) -> dict | None:
    """Expanded provenance of one tile, as the API serves it."""
    sc = p["tiles"].get(key)
    if sc is None:
        return None
    scales, dates = {}, []
    for scale, (computed, code, commit, out_sha, ids) in sc.items():
        inputs = [p["items"][i] for i in ids]
        dates += [i["last_modified"] for i in inputs if i.get("last_modified")]
        scales[scale] = {"computed_at": computed, **({} if computed else {"computed_at_note": NOT_RECORDED}),
                         "code": code, "commit": commit, "outputs": out_sha, "inputs": inputs}
    return {"tile": key, "release": p["release"], "last_changed_in": p["last_changed_in"][key],
            "data_date": max(dates)[:10] if dates else None, "scales": scales}


def changes(previous: dict | None, new: dict, events: list, decision: dict) -> dict:
    """What changed from the previous release: tiles recomputed and the source items whose version changed."""
    prev_tiles = (previous or {}).get("tiles") or {}
    recomputed = sorted(k for k, v in new["last_changed_in"].items() if v == new["release"] and k in prev_tiles)
    old_items = {(i["item"], i["etag"], i["size"]) for i in (previous or {}).get("items", [])}
    changed_items = sorted({i["item"] for i in new["items"]
                            if (i["item"], i["etag"], i["size"]) not in old_items and any(
                                o[0] == i["item"] for o in old_items)})
    added = sorted(k for k in new["tiles"] if k not in prev_tiles)
    removed = sorted(k for k in prev_tiles if k not in new["tiles"])
    return {"release": new["release"], "previous": (previous or {}).get("release"), "events": events,
            "tiles_recomputed": recomputed, "tiles_added": added, "tiles_withdrawn": removed,
            "source_items_changed": changed_items, "decision": decision}
