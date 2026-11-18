"""Lunar south pole relief measured like on Earth: mean slope, max slope and roughness over 1 km windows.

Source: LRO LOLA polar elevation model LDEM_85S_40M (NASA PDS Geosciences Node), 40 m/pixel,
polar stereographic projection centered on -90°, from 85°S to the pole:
    https://pds-geosciences.wustl.edu/lro/lro-l-lola-3-rdr-v1/lrolol_1xxx/data/lola_gdr/polar/img/ldem_85s_40m.img
    (label: ldem_85s_40m.lbl; 16-bit little-endian integers, height = DN x 0.5 m)

Same method as point_geometry.py for Earth (Copernicus DEM, ~30 m): gradient by central differences,
then, per 1 km window, mean and maximum slope and standard deviation of elevation. The lunar DEM (40 m) is slightly
coarser, so lunar slope is a little smoother than Earth slope (see docs/history/v1-scenarios.md).

Usage:
    python lunar_reference.py ~/data/lola/ldem_85s_40m.img            # prints the JSON block
    python lunar_reference.py ~/data/lola/ldem_85s_40m.img --write ../../data/reference/moon-south-pole.json
"""
from __future__ import annotations
import argparse
import json
import math
import sys

import numpy as np

from point_geometry import slope_deg

MOON_RADIUS_M = 1_737_400.0
SOURCE = ("LRO LOLA LDEM_85S_40M (NASA PDS Geosciences Node, lro-l-lola-3-rdr-v1), 40 m/pixel, 85°S-90°S ; "
          "slope and roughness computed over 1 km windows like on Earth (tools/precompute/lunar_reference.py)")
PERCENTILES = (10, 25, 50, 75, 90)


def read_ldem(path: str, size: int = 7584, scale: float = 0.5) -> np.ndarray:
    """Hauteurs (m) d'un LDEM polaire LOLA (entiers 16 bits petit-boutistes, LINES = LINE_SAMPLES = size)."""
    dn = np.fromfile(path, dtype="<i2")
    if dn.size != size * size:
        raise ValueError(f"{path}: {dn.size} values, {size * size} expected (LINES x LINE_SAMPLES of the label)")
    return dn.reshape(size, size).astype("float32") * scale


def latitude_grid(size: int, pixel_m: float, radius_m: float = MOON_RADIUS_M) -> np.ndarray:
    """Latitude (°, negative) at the center of each pixel of a south polar stereographic grid centered on the pole.
    Stereographic: r = 2R tan(pi/4 + lat/2), so lat = 2 atan(r / 2R) - pi/2."""
    offset = (size - 1) / 2.0
    idx = (np.arange(size, dtype="float64") - offset) * pixel_m
    r = np.hypot(idx[None, :], idx[:, None])
    return np.degrees(2 * np.arctan(r / (2 * radius_m)) - math.pi / 2)


def window_stats(z: np.ndarray, pixel_m: float, window_m: float = 1000.0, mask: np.ndarray | None = None) -> dict:
    """slope_mean, slope_max, roughness for each square window of window_m, without overlap.
    A window is kept only if all its pixels are inside `mask` (e.g. south of 85°S)."""
    n = max(int(round(window_m / pixel_m)), 2)
    s = slope_deg(z.astype("float64"), pixel_m, pixel_m)
    rows, cols = (z.shape[0] // n) * n, (z.shape[1] // n) * n

    def blocks(a):
        return a[:rows, :cols].reshape(rows // n, n, cols // n, n).swapaxes(1, 2).reshape(rows // n, cols // n, n * n)

    zb, sb = blocks(z.astype("float64")), blocks(s)
    keep = np.ones(zb.shape[:2], dtype=bool) if mask is None else blocks(mask).all(axis=2)
    return {
        "slope_mean": sb.mean(axis=2)[keep],
        "slope_max": sb.max(axis=2)[keep],
        "roughness": zb.std(axis=2)[keep],
        "window_px": n,
    }


def summarize(stats: dict) -> dict:
    out = {"windows": int(stats["slope_mean"].size), "window_m": None}
    for key in ("slope_mean", "slope_max", "roughness"):
        values = stats[key]
        out[key] = {f"p{p}": round(float(np.percentile(values, p)), 2) for p in PERCENTILES}
    return out


def lunar_reference(path: str, pixel_m: float = 40.0, size: int = 7584, window_m: float = 1000.0,
                    max_lat: float = -85.0) -> dict:
    z = read_ldem(path, size)
    mask = latitude_grid(size, pixel_m) <= max_lat
    stats = window_stats(z, pixel_m, window_m, mask)
    summary = summarize(stats)
    summary["window_m"] = round(stats["window_px"] * pixel_m, 1)
    return summary


def apply_to_profile(profile: dict, summary: dict) -> dict:
    """Writes slope and roughness (interquartile range p25-p75) into the lunar reference profile."""
    params = profile.setdefault("params", {})
    units = {"slope_mean": "°", "slope_max": "°", "roughness": "m"}
    for key, unit in units.items():
        d = summary[key]
        params[key] = {
            "min": d["p25"], "max": d["p75"], "unit": unit,
            "distribution": d,
            "source": f"{SOURCE}; interquartile range (p25-p75) of {summary['windows']} windows of "
                      f"{summary['window_m']:.0f} m",
        }
    profile["todo"] = [t for t in profile.get("todo", []) if not t.startswith("slope_mean, slope_max, roughness")]
    return profile


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("ldem")
    ap.add_argument("--write", help="lunar profile JSON to update (data/reference/moon-south-pole.json)")
    args = ap.parse_args(argv)
    summary = lunar_reference(args.ldem)
    print(json.dumps(summary, indent=1))
    if args.write:
        with open(args.write, encoding="utf-8") as f:
            profile = json.load(f)
        with open(args.write, "w", encoding="utf-8") as f:
            json.dump(apply_to_profile(profile, summary), f, ensure_ascii=False, indent=2)
            f.write("\n")
        print(f"written: {args.write}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
