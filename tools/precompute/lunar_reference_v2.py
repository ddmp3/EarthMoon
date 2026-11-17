"""Lunar south pole terrain reference, methodology v2: same metrics, pixel and window as Earth.

Source: LRO LOLA LDEM_85S_40M (NASA PDS Geosciences Node), 40 m/pixel polar stereographic, 85S to the pole.
Every non-overlapping 1 km window (25 x 25 pixels) entirely south of 85S is measured with
`terrain_metrics.window_metrics`, the function used for Earth sites (site_terrain.py). The reference is the
distribution of each metric over those windows (percentiles 5, 10, 25, 50, 75, 90, 95).

Scope and limits: the distribution covers the whole polar cap, permanently shadowed crater floors and walls
included; it is not the terrain of a specific landing region. LDEM_85S_40M is interpolated between LOLA
ground tracks, so its effective resolution is coarser than 40 m away from the pole.

    python lunar_reference_v2.py ~/data/lola/ldem_85s_40m.img --write ../../data/reference/moon-south-pole.json
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys

import numpy as np

from lunar_reference import latitude_grid, read_ldem
from terrain_metrics import METRIC_KEYS, PIXEL_M, WINDOW_PX, grid_metrics

PERCENTILES = (5, 10, 25, 50, 75, 90, 95)
UNITS = {"slope_mean": "°", "slope_p95": "°", "slope_max": "°", "roughness": "m", "roughness_detrended": "m",
         "traversable_15": "", "traversable_20": "", "traversable_25": ""}
SOURCE = ("LRO LOLA LDEM_85S_40M (NASA PDS Geosciences Node, lro-l-lola-3-rdr-v1), 40 m/pixel, 85°S-90°S; "
          "1 km windows (25 x 25 px), same function as Earth (tools/precompute/terrain_metrics.py)")


def distributions(windows: list[dict]) -> dict:
    out = {}
    for key in METRIC_KEYS:
        values = np.array([w[key] for w in windows if w[key] is not None], dtype="float64")
        out[key] = {f"p{p}": round(float(np.percentile(values, p)), 3) for p in PERCENTILES}
    return out


def lunar_reference_v2(path: str, size: int = 7584, max_lat: float = -85.0) -> dict:
    z = read_ldem(path, size)
    mask = latitude_grid(size, PIXEL_M) <= max_lat
    windows = grid_metrics(z, PIXEL_M, WINDOW_PX, mask)
    with open(path, "rb") as fh:
        digest = hashlib.sha256(fh.read()).hexdigest()
    return {"windows": len(windows), "window_m": PIXEL_M * WINDOW_PX, "pixel_m": PIXEL_M,
            "file_sha256": digest, "distributions": distributions(windows)}


def apply_to_profile(profile: dict, summary: dict) -> dict:
    """Writes the v2 terrain block; the v1 `params` entries are left untouched for continuity."""
    profile["terrain_v2"] = {
        "source": SOURCE, "windows": summary["windows"], "window_m": summary["window_m"],
        "pixel_m": summary["pixel_m"], "file_sha256": summary["file_sha256"],
        "params": {k: {"unit": UNITS[k], "distribution": d} for k, d in summary["distributions"].items()},
    }
    # Interquartile range of the metrics introduced in v2, shown next to the Earth value by the API.
    params = profile.setdefault("params", {})
    for key in ("slope_p95", "roughness_detrended", "traversable_15", "traversable_20", "traversable_25"):
        d = summary["distributions"][key]
        params[key] = {"min": d["p25"], "max": d["p75"], "unit": UNITS[key], "distribution": d,
                       "source": f"{SOURCE}; interquartile range (p25-p75) of {summary['windows']} windows"}
    return profile


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("ldem")
    ap.add_argument("--write")
    a = ap.parse_args(argv)
    summary = lunar_reference_v2(a.ldem)
    print(json.dumps(summary, indent=1))
    if a.write:
        with open(a.write, encoding="utf-8") as fh:
            profile = json.load(fh)
        with open(a.write, "w", encoding="utf-8") as fh:
            json.dump(apply_to_profile(profile, summary), fh, ensure_ascii=False, indent=2)
            fh.write("\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
