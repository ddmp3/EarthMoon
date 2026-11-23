"""Incremental recompute planner (T52 step 3, ADR-009 section 2).

Every unit of every step gets a key, sha256(input keys + step code version + parameters). A unit reruns only when its
key differs from the one of the current release. The inputs:
- features (one per 1° Earth tile): the source items that cover the tile (Copernicus tile, WorldCover 3° tiles);
- profiles (one per planetary target): the items of its planetary sources;
- assess (one per tile): features of the tile and of its 8 neighbours (cells near a tile edge read both), every
  profile, and the Earth sources used everywhere (Antarctic rock outcrop);
- zones (one per target), validate (global, ADR-009: always whole), context (the Earth context layers, global),
  export (one per target: its zones and the context).
"""
from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass, field
from pathlib import Path

STEPS = ("features", "profiles", "assess", "zones", "context", "validate", "export")


@dataclass(frozen=True)
class World:
    tiles: list[str]                                   # "lat,lon" of every 1° tile of the cube
    targets: dict[str, list[str]]                      # planetary target -> catalogue ids of its sources
    tile_sources: list[str] = field(default_factory=list)      # Earth sources split in tiles
    global_sources: list[str] = field(default_factory=list)    # Earth sources read by every assessment
    context_sources: list[str] = field(default_factory=list)   # Earth context layers (E18), never compared


def _h(*parts) -> str:
    return hashlib.sha256(json.dumps(parts, sort_keys=True, default=str).encode()).hexdigest()


def code_version(paths: list[Path]) -> str:
    """sha256 of a step's source files: tests and docs do not count, so they never cause a rerun."""
    files = []
    for p in map(Path, paths):
        files += sorted(f for f in p.rglob("*.py")) if p.is_dir() else [p]
    h = hashlib.sha256()
    for f in files:
        if f.name.startswith("test_") or f.suffix == ".md":
            continue
        h.update(f.name.encode() + b"\0" + f.read_bytes())
    return h.hexdigest()


_DEM = re.compile(r"_([NS])(\d{2})_00_([EW])(\d{3})_00_DEM")
_WC = re.compile(r"_([NS])(\d{2})([EW])(\d{3})_Map\.tif$")


def tiles_of_item(source: str, item: str) -> set[str]:
    """1° tiles covered by one source item: a Copernicus tile is one tile, a WorldCover tile 3° x 3°."""
    m = _DEM.search(item) if source.startswith("copernicus-dem") else _WC.search(item)
    if not m:
        return set()
    la = int(m.group(2)) * (1 if m.group(1) == "N" else -1)
    lo = int(m.group(4)) * (1 if m.group(3) == "E" else -1)
    n = 1 if source.startswith("copernicus-dem") else 3
    return {f"{la + i},{lo + j}" for i in range(n) for j in range(n)}


def _neighbours(tile: str, have: set[str]) -> list[str]:
    la, lo = (int(v) for v in tile.split(","))
    return sorted(t for t in (f"{la + i},{lo + j}" for i in (-1, 0, 1) for j in (-1, 0, 1)) if t in have)


def keys(world: World, signals: dict, code: dict, params: dict) -> tuple[dict, list[str]]:
    item = {src: {k: _h(v) for k, v in (signals.get(src) or {}).items()} for src in signals}
    by_tile: dict[str, list[str]] = {t: [] for t in world.tiles}
    has_dem = set()
    for src in world.tile_sources:
        for k, hk in item.get(src, {}).items():
            for t in tiles_of_item(src, k):
                if t in by_tile:
                    by_tile[t].append(f"{src}/{k}/{hk}")
                    if src.startswith("copernicus-dem"):
                        has_dem.add(t)
    withdrawn = sorted(t for t in world.tiles if t not in has_dem)
    out: dict[str, dict[str, str]] = {s: {} for s in STEPS}
    for t in world.tiles:
        out["features"][t] = _h("withdrawn") if t in withdrawn else _h(sorted(by_tile[t]), code["features"], params)
    for tg, srcs in world.targets.items():
        out["profiles"][tg] = _h([sorted(item.get(s, {}).items()) for s in srcs], code["profiles"], params)
    glob = [sorted(item.get(s, {}).items()) for s in world.global_sources]
    have = set(world.tiles)
    for t in world.tiles:
        feats = [out["features"][n] for n in _neighbours(t, have)]
        out["assess"][t] = _h(feats, sorted(out["profiles"].items()), glob, code["assess"], params)
    all_assess = sorted(out["assess"].items())
    for tg in world.targets:
        out["zones"][tg] = _h(tg, all_assess, code["zones"], params)
    out["context"]["global"] = _h([sorted(item.get(s, {}).items()) for s in world.context_sources], code["context"], params)
    out["validate"]["global"] = _h(sorted(out["zones"].items()), code["validate"], params)
    for tg in world.targets:
        out["export"][tg] = _h(out["zones"][tg], out["context"]["global"], code["export"], params)
    return out, withdrawn


def plan(world: World, signals: dict, code: dict, params: dict, previous: dict | None) -> dict:
    """Units to rerun, per step, against the keys of the current release (`previous`; None reruns everything)."""
    new, withdrawn = keys(world, signals, code, params)
    rerun = {}
    for s in STEPS:
        old = (previous or {}).get(s, {})
        units = sorted(u for u, k in new[s].items() if old.get(u) != k)
        if units:
            rerun[s] = units
    return {"keys": new, "rerun": rerun, "withdrawn_tiles": withdrawn}


def describe(p: dict, seconds_per_unit: dict) -> str:
    """Dry-run text: units per step and the estimated time, from measured step times."""
    lines, total = [], 0.0
    for s in STEPS:
        n = len(p["rerun"].get(s, []))
        if n:
            sec = n * seconds_per_unit.get(s, 0)
            total += sec
            lines.append(f"{s}: {n} unit{'s' if n > 1 else ''}, {sec / 60:.0f} min")
    if p["withdrawn_tiles"]:
        lines.append(f"withdrawn tiles (cells become not evaluated): {len(p['withdrawn_tiles'])}")
    lines.append(f"total: about {total / 3600:.1f} h" if lines else "nothing to rerun")
    return "\n".join(lines)
