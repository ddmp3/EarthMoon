"""Pre-analysis of a detected update (T52b, decided by David on 24/11/2026).

The refresher checks and identifies; it never starts a recompute. For each detected change it estimates, from the
served releases and without any heavy step:
- what the update would recompute (Earth tiles and their neighbours, targets, cells);
- how long it would take (CPU time, from the measured calibration of 23/11/2026).
The recompute is decided later from these figures; on Azure each one has a cost, which can be added from machine prices.
"""
from __future__ import annotations

import json
from pathlib import Path

from discovery.refresh_plan import tiles_of_item

# Measured on 10 Mars tiles (data/runs/t52-calibration.json): 18 s for 10 tiles at 2 scales, 5 s for 89 tiles
# reassessed, 2.3 s for the local zones of 3 targets.
SECONDS = {"features_per_tile_scale": 0.9, "assess_per_tile_target": 5.0 / 89 / 3, "zones_per_target": 0.8}
BASIS = "estimated from the calibration of 23/11/2026 (10 Mars tiles, data/runs/t52-calibration.json)"
TILED = ("copernicus-dem-glo30", "copernicus-dem-glo90", "esa-worldcover")
CONTEXT = ("obu-permafrost-2018", "global-aridity-index-v3", "macrostrat")
# profile input prefix -> catalogue id (release.MOON_CUBE_FILES and mars_run.INPUT_SOURCES)
PREFIX = {"SLDEM2015_": "sldem2015", "GeoUnits.": "usgs-unified-geologic-map", "ironhd": "lp-grs-ns-special-products",
          "mola": "mgs-mola-megdr", "swim": "swim-ice-consistency", "tanaka2014": "usgs-mars-geologic-map-2014"}
SCALES = {"moon": 3, "mars": 2}                         # Earth cube scales per body (90 m and two 30 m; 115 m and 463 m)


def _sources_of_inputs(inputs: dict) -> set[str]:
    out = set()
    for key, val in (inputs or {}).items():
        head = key.split("/")[0]
        names = list(val) if key == "moon-cube/inputs" and isinstance(val, dict) else [head]
        for n in names:
            out.add(next((cat for p, cat in PREFIX.items() if n.startswith(p)), n))
    return out


def releases(root: Path, entries: list[dict]) -> list[dict]:
    """What the pre-analysis needs from each served release."""
    out = []
    for e in entries:
        d = Path(root) / e["id"]
        rel = json.loads((d / "release.json").read_text(encoding="utf-8"))
        cells = next((p for p in rel.get("processing", []) if p.get("step") == "cells"), {})
        scen = json.loads((d / "scenarios.json").read_text(encoding="utf-8"))["scenarios"]
        targets = sorted({t for s in scen for t in s.get("assessed_targets", [])})
        profs = {p["id"]: p for p in json.loads((d / "profiles.json").read_text(encoding="utf-8"))["profiles"]}
        method = json.loads((d / "method.json").read_text(encoding="utf-8"))
        out.append({"id": e["id"], "body": e.get("body", "moon"), "tiles": cells.get("assessed_tiles", 0),
                    "cells": cells.get("cells", 0), "earth_sources": {s["id"] for s in method.get("sources", [])},
                    "target_sources": {t: _sources_of_inputs((profs.get(t) or {}).get("inputs")) for t in targets}})
    return out


def impact(source: str, change: dict, rels: list[dict]) -> dict:
    items = sorted(set(change.get("changed", [])) | set(change.get("withdrawn", [])) | set(change.get("added", [])))
    planetary = [r for r in rels if any(source in s for s in r["target_sources"].values())]
    if planetary:
        kind = "planetary"
    elif source in TILED:
        kind = "earth_tiles"
    elif source in CONTEXT:
        kind = "earth_context"
    else:
        kind = "earth_global"
    tiles = sorted({t for i in items for t in tiles_of_item(source, i)}) if kind == "earth_tiles" else []
    ring = {f"{int(t.split(',')[0]) + a},{int(t.split(',')[1]) + b}" for t in tiles for a in (-1, 0, 1) for b in (-1, 0, 1)}
    out_rels, seconds, unmeasured = [], 0.0, False
    for r in rels:
        per_cell = r["cells"] / r["tiles"] if r["tiles"] else 0
        if kind == "planetary":
            tg = sorted(t for t, s in r["target_sources"].items() if source in s)
            if not tg:
                continue
            n_tiles, feats, ctx = r["tiles"], False, False
        elif source not in r["earth_sources"]:
            continue
        elif kind == "earth_context":
            tg, n_tiles, feats, ctx = [], r["tiles"], False, True
        else:
            tg = sorted(r["target_sources"])
            n_tiles = len(ring) if kind == "earth_tiles" else r["tiles"]
            feats, ctx = kind == "earth_tiles", False
        s = (len(tiles) * SCALES.get(r["body"], 2) * SECONDS["features_per_tile_scale"] if feats else 0.0) \
            + n_tiles * len(tg) * SECONDS["assess_per_tile_target"] + len(tg) * SECONDS["zones_per_target"]
        est: float | None = s
        if ctx:                                               # the context step was never calibrated: no figure
            est, unmeasured = None, True
        else:
            seconds += s
        out_rels.append({"release": r["id"], "body": r["body"], "targets": tg, "tiles_reassessed": n_tiles,
                         "cells_estimate": round(n_tiles * per_cell), "earth_features": feats, "context": ctx,
                         "cpu_seconds_estimate": None if est is None else round(est, 1)})
    return {"source": source, "kind": kind, "items": len(items), "tiles_changed": tiles, "tiles_reassessed": len(ring),
            "releases": out_rels, "cpu_hours_estimate": None if unmeasured else round(seconds / 3600, 4),
            "basis": "not measured: the Earth context step was not calibrated" if unmeasured else BASIS,
            "recompute_started": False}
