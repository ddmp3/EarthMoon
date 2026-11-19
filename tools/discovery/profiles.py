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


def window_fraction(pixels: np.ndarray, window_px: int, margin: int = 0) -> np.ndarray:
    """Mean of a 0..1 pixel layer per window, over known pixels; NaN when the window has none."""
    core = pixels[margin:pixels.shape[0] - margin, margin:pixels.shape[1] - margin].astype("float64")
    h, w = (core.shape[0] // window_px) * window_px, (core.shape[1] // window_px) * window_px
    b = core[:h, :w].reshape(h // window_px, window_px, w // window_px, window_px)
    with np.errstate(invalid="ignore"):
        n = np.isfinite(b).sum(axis=(1, 3))
        s = np.nansum(b, axis=(1, 3))
    return np.where(n > 0, s / np.maximum(n, 1), np.nan)


def threshold(frac: np.ndarray, at_most: float | None = None, at_least: float | None = None) -> np.ndarray:
    """Windows whose fraction is <= at_most or >= at_least. Unknown (NaN) is never selected."""
    ok = np.isfinite(frac)
    f = np.where(ok, frac, 0.0)
    if at_most is not None:
        return ok & (f <= at_most)
    return ok & (f >= at_least)


def lit_areas(illumination: np.ndarray, q: float, min_pixels: int) -> np.ndarray:
    """Pixels of connected areas (8-connected) with average illumination >= q and at least min_pixels pixels."""
    from rasterio.features import sieve
    above = np.isfinite(illumination) & (np.nan_to_num(illumination) >= q)
    kept = sieve(above.astype("uint8"), size=min_pixels, connectivity=8).astype(bool)
    return kept & above              # sieving never adds a pixel below q


def parse_pits(html: str) -> list[dict]:
    """Rows of the LROC Lunar Pits Atlas list page. Values as printed; '>' marks a lower bound, N/A is None.
    The 'Sorting' columns repeat the value beside them and are dropped."""
    import re
    from html import unescape

    def num(cell: str) -> tuple[float | None, bool]:
        c = unescape(cell).strip()
        if c in ("", "N/A"):
            return None, False
        return float(c.lstrip(">")), c.startswith(">")

    out = []
    for row in re.findall(r"<tr>(.*?)</tr>", html, flags=re.S):
        cells = re.findall(r"<td>(.*?)</td>", row, flags=re.S)
        if len(cells) != 13:
            continue                                               # header row
        link = re.search(r'href="/atlases/pits/(\d+)">(.*?)</a>', cells[1])
        depth, lower = num(cells[11])
        out.append({"id": int(link.group(1)), "name": unescape(link.group(2)).strip(), "host": unescape(cells[0]).strip(),
                    "lat": float(cells[2]), "lon": float(cells[3]) % 360, "funnel_max_m": num(cells[4])[0],
                    "funnel_min_m": num(cells[5])[0], "inner_max_m": num(cells[6])[0], "inner_min_m": num(cells[8])[0],
                    "azimuth": num(cells[10])[0], "depth_m": depth, "depth_is_lower_bound": lower})
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


def read_polar(path: Path, size: int, pixel_m: float, psr: bool = False) -> np.ndarray:
    """A PGDA polar stereographic product (int16 with scale and offset) on the LDEM grid, nearest neighbour.
    Nodata and, for the PSR map, any value other than 0 or 1 are unknown (NaN)."""
    import rasterio
    from rasterio.transform import from_origin
    from rasterio.warp import Resampling, reproject
    half = size * pixel_m / 2
    out = np.full((size, size), np.nan, "float32")
    with rasterio.open(path) as src:
        a = src.read(1).astype("float64")
        a = np.where(a == src.nodata, np.nan, a * src.scales[0] + src.offsets[0]) if src.nodata is not None \
            else a * src.scales[0] + src.offsets[0]
        if psr:
            a = np.where(np.isin(a, (0.0, 1.0)), a, np.nan)
        reproject(a.astype("float32"), out, src_transform=src.transform, src_crs=src.crs, src_nodata=np.nan,
                  dst_transform=from_origin(-half, half, pixel_m, pixel_m), dst_crs=src.crs, dst_nodata=np.nan,
                  resampling=Resampling.nearest)
    return out


def polar_windows(ldem: Path, psr_path: Path, ill_path: Path, window_px: int = 25, max_lat: float = -85.0):
    """Metrics, permanent-shadow fraction and mean illumination of every window of LDEM_85S_40M south of max_lat."""
    from lunar_reference import latitude_grid, read_ldem
    g = LDEM_85S
    z = read_ldem(str(ldem), g["size"])
    lat = latitude_grid(g["size"], g["pixel_m"])
    w = window_metrics_grid(z, g["pixel_m"], window_px, margin=0, metrics=ALL_METRICS)
    w["psr_fraction"] = window_fraction(read_polar(psr_path, g["size"], g["pixel_m"], psr=True), window_px)
    w["mean_illumination"] = window_fraction(read_polar(ill_path, g["size"], g["pixel_m"]), window_px)
    return w, select_windows(lat <= max_lat, window_px)


def record(spec_id: str, summary: dict, inputs: dict, params: dict) -> dict:
    return {"id": spec_id, "body": "moon", "spec": f"data/profiles/spec/{spec_id}.yaml", "inputs": inputs,
            "code": code_version(), "commit": os.environ.get("EARTHMOON_COMMIT", "unknown"), "params": params,
            "percentiles": list(PERCENTILES), **summary}


def write_windows(path: Path, w: dict, sel: np.ndarray, cols: tuple[str, ...], pixel_m: float, window_px: int,
                  size: int) -> str:
    """Parquet of the selected windows (row, col, polar stereographic centre x and y, metrics); returns sha256."""
    import pyarrow as pa
    import pyarrow.parquet as pq
    r, c = np.nonzero(sel)
    half = size * pixel_m / 2
    t = {"row": r.astype("int32"), "col": c.astype("int32"),
         "x_m": (-half + (c + 0.5) * window_px * pixel_m).astype("float64"),
         "y_m": (half - (r + 0.5) * window_px * pixel_m).astype("float64")}
    for k in cols:
        t[k] = np.asarray(w[k])[sel].astype("float32")
    path.parent.mkdir(parents=True, exist_ok=True)
    pq.write_table(pa.table(t), path, compression="zstd")
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write(path: Path, rec: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(rec, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("what", choices=["south-polar-cap", "polar", "cube", "pits", "lit"])
    ap.add_argument("--dem5", type=Path)
    ap.add_argument("--pits-html", type=Path)
    ap.add_argument("--cube", type=Path, help="moon cube folder (moon_cube.py --out)")
    ap.add_argument("--psr", type=Path)
    ap.add_argument("--illumination", type=Path)
    ap.add_argument("--windows-out", type=Path, default=Path("/data/profiles/moon"))
    ap.add_argument("--iron", type=Path)
    ap.add_argument("--ldem", type=Path)
    ap.add_argument("--out", type=Path, default=Path("data/profiles/moon"))
    a = ap.parse_args(argv)
    if a.what == "south-polar-cap":
        s = south_polar_cap(a.ldem)
        rec = record("moon-south-polar-cap-v2", s, {"lro-lola-ldem-85s-40m": file_input(a.ldem)},
                     {"max_lat": -85.0, "pixel_m": 40.0, "window_px": 25, "margin_px": 0, "min_valid": 0.9})
        write(a.out / "moon-south-polar-cap-v2.json", rec)
        print(json.dumps(rec["windows"]), json.dumps(rec["metrics"]["slope_mean"]))
    elif a.what == "polar":
        polar(a)
    elif a.what == "cube":
        cube_profiles(a)
    elif a.what == "pits":
        pits_profile(a)
    elif a.what == "lit":
        lit_profile(a)
    return 0


LIT_Q, LIT_WINDOWS_M = (0.5, 0.6, 0.7), (100.0, 200.0, 500.0)


LIT_MIN_WINDOWS = 100


def lit_nominal(runs: list[dict]) -> dict:
    """The (0.6, 200 m) run if it has enough windows, else the strictest q, then the largest window, with enough."""
    middle = next(r for r in runs if r["q"] == 0.6 and r["window_m"] == 200.0)
    if middle["windows"]["selected"] >= LIT_MIN_WINDOWS:
        return middle
    ok = [r for r in runs if r["windows"]["selected"] >= LIT_MIN_WINDOWS]
    if not ok:
        return middle
    return sorted(ok, key=lambda r: (-r["q"], -r["window_m"]))[0]


def _frame(a: np.ndarray, fill) -> np.ndarray:
    """One column of `fill` on each side (the margin of central differences)."""
    side = np.full((a.shape[0], 1), fill, dtype=a.dtype)
    return np.hstack([side, a, side])


def _read_rows(dz, lo: int, hi: int, n: int) -> np.ndarray:
    """Rows [lo, hi) of the 5 m mosaic as float64; rows outside the file are NaN, nodata is NaN."""
    from rasterio.windows import Window
    out = np.full((hi - lo, n), np.nan)
    a, b = max(lo, 0), min(hi, dz.height)
    z = dz.read(1, window=Window(0, a, n, b - a)).astype("float64")
    if dz.nodata is not None:
        z[z == dz.nodata] = np.nan
    out[a - lo:b - lo] = z
    return out


def lit_profile(a) -> None:
    """moon-persistently-lit: windows of the 5 m mosaic (87°S to 90°S) lying entirely inside connected areas whose
    average illumination is >= q (60 m map, south of 85°S). Every q and window size of the spec is computed; the
    nominal is the middle of each list (expert choice, T41). The 40 m LDEM outside the mosaic is not used: the
    mosaic covers the area where 200 m windows can be measured at 5 m, and mixing pixel scales is avoided."""
    import rasterio
    from rasterio.transform import from_origin
    from rasterio.warp import Resampling, reproject
    ill = read_polar(a.illumination, 5058, 60.0)                       # native 60 m grid, no resampling
    with rasterio.open(a.illumination) as src:
        ill_crs, ill_tf = src.crs, src.transform
    masks = {q: {} for q in LIT_Q}
    for q in LIT_Q:
        for wm in LIT_WINDOWS_M:
            masks[q][wm] = lit_areas(ill, q, min_pixels=int(np.ceil((wm / 60.0) ** 2)))
    runs = []
    with rasterio.open(a.dem5) as dz:
        n, px, half = dz.width, 5.0, dz.width * 5.0 / 2
        for wm in LIT_WINDOWS_M:
            wpx = int(wm / px)
            strip = 1000
            acc = {q: {k: [] for k in POLAR_METRICS} for q in LIT_Q}
            for r0 in range(0, n, strip):
                tf = from_origin(-half, half - (r0 - 1) * px, px, px)    # grid of the framed strip, row r0 - 1 first
                shape = (strip + 2, n)
                lit = {}
                for q in LIT_Q:
                    m = np.zeros(shape, "uint8")
                    reproject(masks[q][wm].astype("uint8"), m, src_transform=ill_tf, src_crs=ill_crs, dst_transform=tf,
                              dst_crs=ill_crs, resampling=Resampling.nearest)
                    lit[q] = _frame(m.astype(bool), False)
                if not any(v.any() for v in lit.values()):
                    continue
                zz = _frame(_read_rows(dz, r0 - 1, r0 + strip + 1, n), np.nan)
                w = window_metrics_grid(zz, px, wpx, margin=1, metrics=ALL_METRICS)
                il = np.full(shape, np.nan, "float32")
                reproject(ill.astype("float32"), il, src_transform=ill_tf, src_crs=ill_crs, src_nodata=np.nan,
                          dst_transform=tf, dst_crs=ill_crs, dst_nodata=np.nan, resampling=Resampling.nearest)
                w["mean_illumination"] = window_fraction(_frame(il, np.nan), wpx, margin=1)
                for q in LIT_Q:
                    sel = select_windows(lit[q], wpx, margin=1)
                    for k in POLAR_METRICS:
                        acc[q][k].append(np.asarray(w[k])[sel])
            for q in LIT_Q:
                vals = {k: np.concatenate(acc[q][k]) if acc[q][k] else np.zeros(0) for k in POLAR_METRICS}
                s = summarise(vals, np.ones(vals["slope_mean"].size, bool), POLAR_METRICS)
                runs.append({"q": q, "window_m": wm, "pixel_m": px, **s})
    nominal = lit_nominal(runs)
    rec = record("moon-persistently-lit", {"windows": nominal["windows"], "metrics": nominal["metrics"]},
                 {"lola-south-pole-5m-mosaic/elevation": file_input(a.dem5),
                  "lola-polar-illumination/average": file_input(a.illumination)},
                 {"q": nominal["q"], "window_m": nominal["window_m"], "pixel_m": 5.0,
                  "window_px": int(nominal["window_m"] / 5.0), "min_valid": 0.9,
                  "domain": "87°S to 90°S (5 m mosaic)", "min_area": "connected lit area of at least one window",
                  "nominal_rule": f"middle of the spec lists (q 0.6, 200 m) unless it has fewer than {LIT_MIN_WINDOWS} windows; "
                                  "then the strictest q, then the largest window, that has at least that many (T41)"})
    rec["sensitivity"] = [{"q": r["q"], "window_m": r["window_m"], **r["windows"], "metrics": r["metrics"]} for r in runs]
    rec["not_computed"] = {"ldem_40m_outside_87s": "85°S to 87°S is not covered at 5 m; 200 m windows at 40 m (5 pixels) are not comparable, so left out",
                           "earth_scale": "windows below 1 km need an Earth cube at the same window size (T42)"}
    write(a.out / "moon-persistently-lit.json", rec)
    print("moon-persistently-lit", json.dumps(rec["windows"]), json.dumps(rec["metrics"]["slope_mean"]))
    for r in rec["sensitivity"]:
        print(r["q"], r["window_m"], r["selected"], r["metrics"]["slope_mean"]["p50"])


def pits_profile(a) -> None:
    """moon-pits (site-set): each atlas pit with its geologic unit and the 1 km SLDEM window that contains it."""
    import pyarrow.parquet as pq
    from discovery.moon_cube import grid_lookup
    codes = json.loads((a.cube / "units_codes.json").read_text())
    units = np.load(a.cube / "units_64ppd.npy", mmap_mode="r")
    pits = parse_pits(a.pits_html.read_text(encoding="utf-8"))
    sites, tiles = [], {}
    for pit in pits:
        u = int(grid_lookup(units, np.array([pit["lat"]]), np.array([pit["lon"]]), 90, -180)[0])
        site = {**pit, "map_unit": codes[u - 1] if u else None}
        la, lo = int(np.floor(pit["lat"])), int(np.floor(pit["lon"])) % 360
        name = f"moon_{'N' if la >= 0 else 'S'}{abs(la):02d}_E{lo:03d}.windows.parquet"
        f = a.cube / "sldem2015-59m" / name
        if -60 <= pit["lat"] < 60 and f.exists():
            if name not in tiles:
                tiles[name] = pq.read_table(f, columns=["lat", "lon", "slope_mean", "roughness_detrended"]).to_pydict()
            t = tiles[name]
            dlat = np.radians(np.asarray(t["lat"]) - pit["lat"])
            dlon = np.radians((np.asarray(t["lon"]) - pit["lon"] + 180) % 360 - 180) * np.cos(np.radians(pit["lat"]))
            i = int(np.argmin(np.hypot(dlat, dlon)))
            dist_m = float(np.hypot(dlat[i], dlon[i]) * 1737400.0)
            site.update({"window_distance_m": round(dist_m, 1),
                         "context_slope_mean": None if dist_m > 720 else round(float(t["slope_mean"][i]), 3),
                         "context_roughness_detrended": None if dist_m > 720 else round(float(t["roughness_detrended"][i]), 3)})
        else:
            site.update({"window_distance_m": None, "context_slope_mean": None, "context_roughness_detrended": None,
                         "outside": "SLDEM2015 covers 60°S to 60°N"})
        sites.append(site)
    ctx = np.array([s["context_slope_mean"] for s in sites if s["context_slope_mean"] is not None])
    by_unit: dict = {}
    for s in sites:
        by_unit[s["map_unit"] or "none"] = by_unit.get(s["map_unit"] or "none", 0) + 1
    rec = record("moon-pits", {"windows": {"selected": len(sites), "valid": int(ctx.size)},
                               "metrics": {"context_slope_mean": {"n": int(ctx.size), **{f"p{q}": round(float(np.percentile(ctx, q)), 3) for q in PERCENTILES}}}},
                 {"lroc-pits-atlas/list": file_input(a.pits_html),
                  "moon-cube/manifest": {"sha256": hashlib.sha256((a.cube / "sldem2015-59m" / "manifest.jsonl").read_bytes()).hexdigest()}},
                 {"window": "the 1 km SLDEM window whose centre is nearest (at most 720 m, half a window diagonal)",
                  "unit": "Unified Geologic Map unit at the pit centre (64 ppd raster)"})
    rec["kind"] = "site-set"
    rec["pits_by_map_unit"] = dict(sorted(by_unit.items(), key=lambda kv: -kv[1]))
    rec["sites"] = sites
    rec["not_computed"] = {
        "nac_dtm_slopes": "public NAC DTMs are preliminary and their post spacing is not stated (lroc-nac-dtm-pipeline): not used",
        "bouguer_anomaly": "GRAIL cannot resolve a single tube (spec): exploratory, left out",
        "setting": "the atlas gives the host feature, not mare / impact melt / highland; the map unit at the pit is given instead"}
    write(a.out / "moon-pits.json", rec)
    print("moon-pits", len(sites), "sites,", ctx.size, "with context;", rec["pits_by_map_unit"])


CUBE_SPECS = ("moon-mare-plains", "moon-fresh-craters", "moon-degraded-highlands")


def _spec_param(spec: dict, name: str) -> dict:
    return next(p for p in spec["selection"]["parameters"] if p["name"] == name)


def cube_profiles(a) -> None:
    """moon-mare-plains, moon-fresh-craters, moon-degraded-highlands from the lunar window cube (SLDEM2015)."""
    import pyarrow.dataset as ds
    import yaml
    from discovery.moon_cube import otsu_split, read_iron
    root = Path(__file__).resolve().parents[2]
    folder = a.cube / "sldem2015-59m"
    codes = json.loads((a.cube / "units_codes.json").read_text())
    cols = ["lat", "lon", "unit", "unit_share", "fe", *ALL_METRICS]
    t = ds.dataset(sorted(folder.glob("*.windows.parquet")), format="parquet").to_table(columns=cols)
    w = {k: t.column(k).to_numpy() for k in cols}          # numpy columns: Python lists of 32 M rows exhaust memory
    del t
    manifest = folder / "manifest.jsonl"
    inputs = {"moon-cube/manifest": {"file": manifest.name, "sha256": hashlib.sha256(manifest.read_bytes()).hexdigest()},
              "moon-cube/inputs": json.loads((a.cube / "inputs.json").read_text())}
    code_of = {c: i + 1 for i, c in enumerate(codes)}
    in_units = lambda units, share: np.isin(w["unit"], [code_of[u] for u in units if u in code_of]) & (w["unit_share"] >= share)
    domain = {"windows": int(w["unit"].size), "valid": int(np.isfinite(w["slope_mean"]).sum())}
    for sid in CUBE_SPECS:
        spec = yaml.safe_load((root / f"data/profiles/spec/{sid}.yaml").read_text(encoding="utf-8"))
        up, sp = _spec_param(spec, "units"), _spec_param(spec, "min_unit_share")
        sel = in_units(up["value"], sp["value"])
        sens = []
        for share in sp["sensitivity"]:
            s = summarise(w, in_units(up["value"], share), ("slope_mean",))
            sens.append({"min_unit_share": share, "units": up["value"], **s["windows"], "slope_mean": s["metrics"]["slope_mean"]})
        for units in up["sensitivity"]:
            s = summarise(w, in_units(units, sp["value"]), ("slope_mean",))
            sens.append({"min_unit_share": sp["value"], "units": units, **s["windows"], "slope_mean": s["metrics"]["slope_mean"]})
        params = {"units": up["value"], "min_unit_share": sp["value"], "pixel_m": 59.225293836, "window_px": 17,
                  "window_m": round(17 * 59.225293836, 1), "min_valid": 0.9, "domain": "60°S to 60°N"}
        if sid == "moon-mare-plains":
            iron = read_iron(Path(a.iron))
            lat = 89.75 - np.arange(360) * 0.5
            band = np.abs(lat) < 60
            vals = iron[band].ravel()
            wts = np.repeat(np.cos(np.radians(lat[band])), 720)
            split = otsu_split(vals, wts)
            params["fe_split_wt_pct"] = round(split, 3)
            for f in (0.9, 1.0, 1.1):
                fe_sel = np.nan_to_num(w["fe"], nan=-1) >= split * f
                s = summarise(w, fe_sel, ("slope_mean",))
                both = int((fe_sel & sel).sum())
                sens.append({"fe_split_wt_pct": round(split * f, 3), **s["windows"], "slope_mean": s["metrics"]["slope_mean"],
                             "agreement_with_map": {"both": both, "map_only": int((sel & ~fe_sel).sum()),
                                                    "iron_only": int((fe_sel & ~sel).sum())}})
            inputs["lp-grs-ns-special-products/ironhd"] = file_input(Path(a.iron))
        rec = record(sid, summarise(w, sel, ALL_METRICS), inputs, params)
        rec["domain"] = domain
        rec["sensitivity"] = sens
        rec["outputs"] = {"windows_parquet": _write_cube_windows(a.windows_out / f"{sid}.windows.parquet", w, sel)}
        rec["not_computed"] = {"reason": "composition (Lunar Prospector Th) is compared in T46 (geology)"} if sid == "moon-mare-plains" else {}
        write(a.out / f"{sid}.json", rec)
        print(sid, json.dumps(rec["windows"]), json.dumps(rec["metrics"]["slope_mean"]))


def _write_cube_windows(path: Path, w: dict, sel: np.ndarray) -> str:
    import pyarrow as pa
    import pyarrow.parquet as pq
    path.parent.mkdir(parents=True, exist_ok=True)
    pq.write_table(pa.table({k: np.asarray(v)[sel] for k, v in w.items()}), path, compression="zstd")
    return hashlib.sha256(path.read_bytes()).hexdigest()


POLAR_METRICS = ALL_METRICS + ("mean_illumination",)


def polar(a) -> None:
    """moon-polar-lit-highlands and moon-psr. Nominal thresholds are the middle of the spec sensitivity lists
    (expert choice, T41); every listed value is computed and reported."""
    inputs = {"lro-lola-ldem-85s-40m": file_input(a.ldem), "lola-polar-illumination/psr": file_input(a.psr),
              "lola-polar-illumination/average": file_input(a.illumination)}
    g = LDEM_85S
    runs = {}
    for px in (25, 12, 5):
        runs[px] = polar_windows(a.ldem, a.psr, a.illumination, window_px=px)
    w, base = runs[25]
    specs = {"moon-polar-lit-highlands": ("f_lit", "at_most", 0.05, (0.0, 0.05, 0.10), (25,)),
             "moon-psr": ("f_psr", "at_least", 0.75, (0.5, 0.75, 0.9), (25, 12, 5))}
    for sid, (name, side, nominal, values, sizes) in specs.items():
        sens = []
        for px in sizes:
            wp, bp = runs[px]
            for v in values:
                sel = bp & threshold(wp["psr_fraction"], **{side: v})
                s = summarise(wp, sel, ("slope_mean",))
                sens.append({name: v, "window_m": px * g["pixel_m"], **s["windows"], "slope_mean": s["metrics"]["slope_mean"]})
        sel = base & threshold(w["psr_fraction"], **{side: nominal})
        rec = record(sid, summarise(w, sel, POLAR_METRICS), inputs,
                     {name: nominal, "nominal_rule": "middle of the spec sensitivity list (expert choice, T41)",
                      "max_lat": -85.0, "pixel_m": g["pixel_m"], "window_px": 25, "window_m": 1000.0, "min_valid": 0.9})
        rec["sensitivity"] = sens
        rec["outputs"] = {"windows_parquet": write_windows(a.windows_out / f"{sid}.windows.parquet", w, sel,
                                                           POLAR_METRICS + ("psr_fraction",), g["pixel_m"], 25, g["size"])}
        rec["not_computed"] = {"reason": "thermal, volatile and radar layers (Diviner, LAMP, Mini-RF) belong to T47"}
        write(a.out / f"{sid}.json", rec)
        print(sid, json.dumps(rec["windows"]), json.dumps(rec["metrics"]["slope_mean"]))


if __name__ == "__main__":
    sys.exit(main())
