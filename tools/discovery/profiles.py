"""Planetary environment profiles (T41, ADR-001 stage `profiles`).

A profile is the distribution of each terrain metric over the windows of one environment, selected by the rule of
its spec (`data/profiles/spec/<id>.yaml`). The window metrics are the Earth ones (`windows.window_metrics_grid`),
so a lunar window and an Earth window are measured by the same code.

    python tools/discovery/profiles.py south-polar-cap --ldem /data/lola/ldem_85s_40m.img --out data/profiles/moon
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "precompute"))
from discovery.windows import ALL_METRICS, window_metrics_grid  # noqa: E402

PERCENTILES = (5, 10, 25, 50, 75, 90, 95)
PROFILE_FILES = ("discovery/profiles.py", "discovery/windows.py", "precompute/terrain_metrics.py",
                 "precompute/lunar_reference.py")
LDEM_85S = {"size": 7584, "pixel_m": 40.0, "window_px": 25}


# --- pure part (tested) ------------------------------------------------------------------------------------

def select_windows(mask: np.ndarray, window_px: int, margin: int = 0) -> np.ndarray:
    """(rows, cols) grid of non-overlapping windows: True when every pixel of the window is inside `mask`."""
    core = mask[margin:mask.shape[0] - margin, margin:mask.shape[1] - margin]
    h, w = (core.shape[0] // window_px) * window_px, (core.shape[1] // window_px) * window_px
    return core[:h, :w].reshape(h // window_px, window_px, w // window_px, window_px).all(axis=(1, 3))


def summarise(values: dict[str, np.ndarray], selected: np.ndarray, metrics: tuple[str, ...]) -> dict:
    """Counts and percentiles of each metric over the selected windows. NaN windows (below 90% valid pixels)
    count as selected but not valid; they never enter a percentile."""
    sel = selected.ravel()
    first = np.asarray(values[metrics[0]]).ravel()[sel]
    out = {"windows": {"selected": int(sel.sum()), "valid": int(np.isfinite(first).sum())}, "metrics": {}}
    for k in metrics:
        v = np.asarray(values[k], dtype="float64").ravel()[sel]
        v = v[np.isfinite(v)]
        row = {"n": int(v.size)}
        for p in PERCENTILES:
            row[f"p{p}"] = round(float(np.percentile(v, p)), 3) if v.size else None
        out["metrics"][k] = row
    return out


def code_version(root: Path = Path(__file__).resolve().parents[1]) -> str:
    """sha256 of the profile sources, line endings normalised (as the Earth cube, ADR-009)."""
    h = hashlib.sha256()
    for name in PROFILE_FILES:
        h.update(name.encode() + b"\0" + (root / name).read_bytes().replace(b"\r\n", b"\n") + b"\0")
    return h.hexdigest()


def file_input(path: Path) -> dict:
    return {"file": path.name, "size": path.stat().st_size, "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}


# --- environments ------------------------------------------------------------------------------------------

def south_polar_cap(ldem: Path, max_lat: float = -85.0) -> dict:
    """moon-south-polar-cap-v2: every 1 km window of LDEM_85S_40M entirely south of max_lat (v2 anchor)."""
    from lunar_reference import latitude_grid, read_ldem
    g = LDEM_85S
    z = read_ldem(str(ldem), g["size"])
    lat = latitude_grid(g["size"], g["pixel_m"])
    w = window_metrics_grid(z, g["pixel_m"], g["window_px"], margin=0, metrics=ALL_METRICS)
    sel = select_windows(lat <= max_lat, g["window_px"])
    return summarise(w, sel, ALL_METRICS)


def record(spec_id: str, summary: dict, inputs: dict, params: dict) -> dict:
    return {"id": spec_id, "body": "moon", "spec": f"data/profiles/spec/{spec_id}.yaml", "inputs": inputs,
            "code": code_version(), "commit": os.environ.get("EARTHMOON_COMMIT", "unknown"), "params": params,
            "percentiles": list(PERCENTILES), **summary}


def write(path: Path, rec: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(rec, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("what", choices=["south-polar-cap"])
    ap.add_argument("--ldem", type=Path)
    ap.add_argument("--out", type=Path, default=Path("data/profiles/moon"))
    a = ap.parse_args(argv)
    if a.what == "south-polar-cap":
        s = south_polar_cap(a.ldem)
        rec = record("moon-south-polar-cap-v2", s, {"lro-lola-ldem-85s-40m": file_input(a.ldem)},
                     {"max_lat": -85.0, "pixel_m": 40.0, "window_px": 25, "margin_px": 0, "min_valid": 0.9})
        write(a.out / "moon-south-polar-cap-v2.json", rec)
        print(json.dumps(rec["windows"]), json.dumps(rec["metrics"]["slope_mean"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
