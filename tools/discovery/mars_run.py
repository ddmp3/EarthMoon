"""Mars discovery run (T48, scenario D, protocol mars-v1): the lunar discovery engine with Martian settings.

    EARTHMOON_BODY=mars PYTHONPATH=tools python tools/discovery/mars_run.py lists --cube /data/cube --run /data/run-mars-001
    EARTHMOON_BODY=mars PYTHONPATH=tools python tools/discovery/discover.py refs --run /data/run-mars-001 --profiles-windows /data/profiles/mars
    (then assess and zones as for the Moon, with the tile lists written by `lists`)

What changes from the lunar runs, and why (docs/VALIDATION_PROTOCOL.md, protocol mars-v1):
- targets: the three Martian environments of phase 1, each compared at its own MOLA pixel (decision E19: windows of
  25 x 25 pixels), Earth resampled to the same pixel and window;
- every Earth tile is assessed: there is no screening stage at these scales;
- windows (2.9 and 11.6 km) are larger than the 5 km cells, so a window also belongs to every cell whose centre it
  holds, and confidence is the lunar share of valid and hidden windows rather than a count of 20;
- no requirement and no suitability: the lunar rover limits are never reused, and the MSL limits of scenario D
  (R43) apply at rover scale, far below these windows (E14);
- the Antarctic rock sample spreads over 0.4 window, as it does for the 1 km lunar windows (400 m).
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

PIXEL_M = {"glo90-115m-w25": 115.77, "glo90-463m-w25": 463.08}        # the cube pixels: MOLA 512 and 128 ppd
WINDOW_PX = 25
MC_SIGMA_DEG = {"glo90-115m-w25": 0.25, "glo90-463m-w25": 0.04}        # protocol mars-v2, measured (slope_noise.py)
TARGETS = {"mars-ice-rich-midlatitudes": "glo90-463m-w25", "mars-north-polar": "glo90-115m-w25",
           "mars-south-polar": "glo90-115m-w25",
           "mars-volcanic-plains": "glo90-463m-w25"}                  # protocol mars-v3 (24/11/2026), T48c


def share_confidence(valid: int, windows: int, masked: int, unknown_mask: int) -> str:
    """high: at least 80% of the cell's windows valid and unmasked, under 10% masked or of unknown cover (the lunar
    rule, 20 valid windows of about 25, as shares); medium: at least half valid; low otherwise."""
    if windows <= 0:
        return "low"
    if valid >= 0.8 * windows and (masked + unknown_mask) < 0.1 * windows:
        return "high"
    return "medium" if valid >= 0.5 * windows else "low"


def configure(d) -> None:
    """Replace the body-specific settings of the discovery engine module `d`. Dicts and lists are changed in place,
    so modules that imported them by name see the Martian values."""
    d.PRODUCT = "glo90"
    d.SCALES.clear()
    d.SCALES.update(PIXEL_M)
    d.COVERAGE_SCALES = tuple(sorted(PIXEL_M, key=PIXEL_M.get))      # finest first
    d.TARGET_SCALE.clear()
    d.TARGET_SCALE.update(TARGETS)
    d.SCENARIO_TARGETS.clear()
    d.SCENARIO_TARGETS.update({"D": sorted(TARGETS)})
    d.ELIMINATING.clear()
    d.ELIMINATING.update({"D": []})
    d.WINDOW_ASSIGN = "cover"
    d.WINDOW_M.clear()
    d.WINDOW_M.update({s: px * WINDOW_PX for s, px in PIXEL_M.items()})
    d.ROCK_RADIUS_M.clear()
    d.ROCK_RADIUS_M.update({s: 0.4 * px * WINDOW_PX for s, px in PIXEL_M.items()})
    d.CONFIDENCE = share_confidence
    d.RULES_IN_USE = {}
    d.SUITABILITY_IN_USE = {}
    d.CELL_SCHEMA = d._schema()
    keep = [c for c in d.LOAD_COLUMNS if not c.endswith(":median")]
    d.LOAD_COLUMNS[:] = keep + [f"{t}:median" for t in TARGETS]


def configure_validation(v) -> None:
    """Settings of the validation module `v` for the Mars run (protocol mars-v1)."""
    import math
    from discovery.mars import MARS_R_M
    fine = min(PIXEL_M, key=PIXEL_M.get)
    v.MASK_SCALE = fine                                                 # the masked unit: the finest Martian window
    v.MASK_REACH_KM = PIXEL_M[fine] * WINDOW_PX / 1000 / math.sqrt(2)   # half its diagonal
    v.PROFILE_KM_PER_DEG = 2 * math.pi * MARS_R_M / 1000 / 360
    v.BLOCK_KM.clear()
    v.BLOCK_KM.update({t: 5 * PIXEL_M[s] * WINDOW_PX / 1000 for t, s in TARGETS.items()})   # 5 windows, as on the Moon
    # protocol mars-v3: the verified controls of scenario D (R29) are volcanic plains; they validate that target only
    v.POSITIVES = {"D (polar and ice-rich targets)": "none: the R29 controls are volcanic plains",
                   "consequence": "no positive validation for the polar and ice-rich targets"}
    v.POSITIVE_TARGETS = {"D": ["mars-volcanic-plains"]}
    # protocol mars-v2 (23/11/2026): slope noise of the Monte Carlo measured from the DEM error at each scale
    # (tools/discovery/slope_noise.py, data/runs/run-mars-001/slope-noise.json), instead of the lunar 0.5 degree
    v.SIGMA_BY_SCALE.clear()
    v.SIGMA_BY_SCALE.update(MC_SIGMA_DEG)
    v.REPRO = {"scale": fine, "product": "glo90", "pixel": str(PIXEL_M[fine]), "window_px": WINDOW_PX,
               "cache": "/data/copernicus-glo90"}


def configure_release(r) -> None:
    """Settings of the release module `r` for the Mars release: scenario D, Martian profiles and sources."""
    r.BODY = "mars"
    r.PROTOCOL = "validation-protocol-mars-v3"
    r.SCENARIO_FILES = {"D": "D-mars.yaml"}
    r.PROFILE_DIR, r.PROFILE_GLOB = "data/profiles/mars", "mars-*.json"
    r.EARTH_SOURCES = ["copernicus-dem-glo90", "esa-worldcover", "add-rock-outcrop-v7-3", "natural-earth-admin0-110m"]
    r.INPUT_SOURCES = {"mola": "mgs-mola-megdr", "swim": "swim-ice-consistency"}
    r.NOT_COMPARABLE_TEXT = "later phase: site sets or rover-scale terrain (HiRISE), not in phase 1"
    r.SCREENING = False
    r.COVERAGE_AREA = "cells"
    r.COVERAGE_TEXT = {**r.COVERAGE_TEXT,
                       "screened_out": "no Earth window at this target's MOLA scale (sea or no DEM)",
                       "low_confidence": "not high confidence: under 80% of the cell's windows valid, or 10% or more "
                                         "masked or of unknown cover",
                       "evaluated": "high confidence: at least 80% of the cell's windows valid and under 10% masked or "
                                    "of unknown cover"}


def tile_lists(cube: Path, run: Path) -> list[Path]:
    """One list per scale of every tile the cube holds (all Earth land tiles: no screening at these scales)."""
    import re
    run.mkdir(parents=True, exist_ok=True)
    out = []
    pat = re.compile(r"_([NS])(\d+)_00_([EW])(\d+)_00_DEM\.windows\.parquet$")
    for sc in sorted(PIXEL_M, key=PIXEL_M.get):
        keys = []
        for f in sorted((Path(cube) / sc).glob("*.windows.parquet")):
            m = pat.search(f.name)
            if m:
                la = int(m.group(2)) * (1 if m.group(1) == "N" else -1)
                lo = int(m.group(4)) * (1 if m.group(3) == "E" else -1)
                keys.append(f"{la},{lo}")
        p = run / f"tiles-refine-{sc}.txt"
        p.write_text("\n".join(keys) + "\n")
        out.append(p)
    return out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("what", choices=["lists"])
    ap.add_argument("--cube", type=Path, default=Path("/data/cube"))
    ap.add_argument("--run", type=Path, default=Path("/data/run-mars-001"))
    a = ap.parse_args(argv)
    for p in tile_lists(a.cube, a.run):
        print(p, len(p.read_text().split()))
    return 0


if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    sys.exit(main())
