"""Stage 1 screening of the global run (T22 decision 4, T43).

A 1° tile is refined at the scale of a lunar target when at least one of its unmasked 90 m windows falls inside
that target's slope interquartile range widened by 2° (T22: 0.17% of fine matches missed on the pilot tiles).
Windows whose ground is hidden (WorldCover, `compare.masked_windows`) never make a tile pass. South of 60°S, where
WorldCover has no data, a tile is kept only if it contains SCAR rock outcrops (`add-rock-outcrop-v7-3`, T14):
elsewhere the surface is ice. Rules fixed before the run (T43).

    python tools/discovery/screen.py --cube /data/cube --profiles data/profiles/moon --outcrops outcrop_tiles.json \
        --out /data/cube/screen.json
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from discovery.compare import MASK_CLASSES, masked_windows  # noqa: E402

WIDEN_DEG = 2.0
SCENARIO_TARGETS = {"A": ["moon-polar-lit-highlands", "moon-psr", "moon-pits"],
                    "B": ["moon-polar-lit-highlands", "moon-psr", "moon-mare-plains", "moon-south-polar-cap-v2"]}
SCALE = {"moon-south-polar-cap-v2": "glo30-40m", "moon-polar-lit-highlands": "glo30-40m", "moon-psr": "glo30-40m",
         "moon-mare-plains": "glo30-59m", "moon-pits": "glo30-59m"}


def target_intervals(profiles: dict, targets: list[str], widen: float = WIDEN_DEG) -> dict:
    out = {}
    for t in targets:
        m = profiles[t]["metrics"]["slope_mean"] if "metrics" in profiles[t] else profiles[t]
        out[t] = (round(max(m["p25"] - widen, 0.0), 6), round(m["p75"] + widen, 6))
    return out


def tile_passes(slope: np.ndarray, masked: np.ndarray, intervals: dict) -> bool:
    ok = np.isfinite(slope) & ~masked
    s = slope[ok]
    return any(bool(((s >= lo) & (s <= hi)).any()) for lo, hi in intervals.values())


def pits_interval(profile: dict) -> dict:
    """The pits profile is a site set: its context slopes play the role of the distribution."""
    return profile["metrics"]["context_slope_mean"]


def main(argv=None) -> int:
    import pyarrow.parquet as pq
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--cube", type=Path, required=True)
    ap.add_argument("--profiles", type=Path, required=True)
    ap.add_argument("--outcrops", type=Path, required=True, help="JSON list of 'lat,lon' tiles holding rock outcrops")
    ap.add_argument("--out", type=Path, required=True)
    a = ap.parse_args(argv)
    profiles = {}
    for t in SCALE:
        p = json.loads((a.profiles / f"{t}.json").read_text(encoding="utf-8"))
        profiles[t] = pits_interval(p) if t == "moon-pits" else p
    targets = sorted({t for ts in SCENARIO_TARGETS.values() for t in ts})
    intervals = target_intervals(profiles, targets)
    by_scale = {s: {t: intervals[t] for t in targets if SCALE[t] == s} for s in sorted(set(SCALE.values()))}
    outcrops = set(json.loads(a.outcrops.read_text()))
    listing = json.loads((a.cube / "glo90-90m" / "listing.json").read_text())
    cols = ["slope_mean", *MASK_CLASSES, "wc_covered"]
    keep = {s: [] for s in by_scale}
    stats = {"tiles": 0, "south_of_60_without_outcrops": 0, "fully_masked_or_missing": 0}
    from discovery.copernicus import tile_name
    for key in sorted(listing):
        la, lo = (int(v) for v in key.split(","))
        stats["tiles"] += 1
        if la < -60 and key not in outcrops:
            stats["south_of_60_without_outcrops"] += 1
            continue
        t = pq.read_table(a.cube / "glo90-90m" / f"{tile_name(la, lo, 'glo90')}.windows.parquet", columns=cols)
        w = {k: t.column(k).to_numpy() for k in cols}
        masked, _ = masked_windows(w)
        any_pass = False
        for s, iv in by_scale.items():
            if tile_passes(w["slope_mean"], masked, iv):
                keep[s].append(key)
                any_pass = True
        if not any_pass:
            stats["fully_masked_or_missing"] += 1 if not (np.isfinite(w["slope_mean"]) & ~masked).any() else 0
    out = {"rule": __doc__.split("\n\n")[1].strip(), "widen_deg": WIDEN_DEG, "intervals": intervals, "stats": stats,
           "refine": {s: v for s, v in keep.items()}, "counts": {s: len(v) for s, v in keep.items()}}
    a.out.write_text(json.dumps(out, indent=1) + "\n", encoding="utf-8")
    for s, v in keep.items():
        (a.out.parent / f"tiles-refine-{s}.txt").write_text("\n".join(v) + "\n")
    print(json.dumps({k: out[k] for k in ("intervals", "stats", "counts")}, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
