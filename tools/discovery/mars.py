"""Mars terrain windows (T48, decision E19): MOLA MEGDR grids.

E19 (David, 20/11/2026): windows of 25 x 25 pixels of the planetary grid, as on the Moon (25 x 25 pixels of 40 m):
- polar grids at 512 pixels per degree (about 115.8 m): windows of about 2.9 km;
- the global grid at 128 pixels per degree (about 463 m north-south): windows of about 11.6 km.
The global grid is equirectangular: east-west pixels shrink with the cosine of latitude, so each band of 25 rows is
resampled east-west to square metric pixels before its windows are measured.
MOLA bins are filled by interpolation where no shot fell (55% of bins hold a shot near the equator, per the label):
each window keeps the share of its pixels that hold at least one shot (count grids `megc`).
"""
from __future__ import annotations

import math
import re
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

MARS_R_M = 3396190.0                         # IAU sphere used by the MEGDR labels (a_axis_radius 3396.0 km)
WINDOW_PX = 25                               # E19
DTYPES = {"SignedMSB2": ">i2", "UnsignedMSB2": ">u2", "SignedLSB2": "<i2", "IEEE754MSBSingle": ">f4", "UnsignedByte": "u1", "SignedByte": "i1"}


def read_pds4(img: Path) -> np.ndarray:
    """2-D array of a PDS4 image, from the shape, type and offset in its .xml label."""
    label = Path(img).with_suffix(".xml").read_text(encoding="utf-8")
    dtype = DTYPES[re.search(r"<(?:\w+:)?data_type>([^<]+)<", label).group(1)]
    n = [int(x) for x in re.findall(r"<(?:\w+:)?elements>(\d+)<", label)[:2]]
    m = re.search(r'<(?:\w+:)?offset unit="byte">(\d+)<', label)
    offset = int(m.group(1)) if m else 0
    a = np.fromfile(img, dtype=dtype, count=n[0] * n[1], offset=offset).reshape(n[0], n[1])
    elem = label[label.find("<Element_Array>"):label.find("</Element_Array>")] if "<Element_Array>" in label else ""
    sc = re.search(r"<(?:\w+:)?scaling_factor>([^<]+)<", elem)
    off = re.search(r"<(?:\w+:)?value_offset>([^<]+)<", elem)
    if sc or off:                                          # polar grids: elevation = raw x 0.25 - 8000 m
        return a.astype("float64") * (float(sc.group(1)) if sc else 1.0) + (float(off.group(1)) if off else 0.0)
    return a.astype(dtype.replace(">", "").replace("<", "") if dtype[1] != "f" else "f4")


def observed_fraction(counts: np.ndarray) -> float:
    """Share of pixels holding at least one MOLA shot."""
    c = np.asarray(counts)
    return float((c > 0).mean()) if c.size else float("nan")


def band_windows(z: np.ndarray, lats: np.ndarray, ppd: int, window_px: int = WINDOW_PX, counts: np.ndarray | None = None) -> dict:
    """Windows of one band of `window_px` rows of an equirectangular grid: the band is resampled east-west to square
    metric pixels (north-south pixel size), then cut into windows of window_px x window_px pixels."""
    from discovery.windows import ALL_METRICS, window_metrics_grid
    py = 2 * math.pi * MARS_R_M / 360 / ppd
    lat_c = float(np.mean(lats))
    px = py * math.cos(math.radians(lat_c))
    ncol = z.shape[1]
    width = ncol * px
    nsq = int(width // py)
    x_src = (np.arange(ncol) + 0.5) * px
    x_dst = (np.arange(nsq) + 0.5) * py
    zs = np.vstack([np.interp(x_dst, x_src, row.astype(float)) for row in z])
    w = window_metrics_grid(zs, py, window_px, margin=0, metrics=ALL_METRICS)
    out = {k: v.ravel() for k, v in w.items()}
    n = out["slope_mean"].size
    out["col_m"] = (np.arange(n) + 0.5) * window_px * py
    out["lon_frac"] = out["col_m"] / width                                  # position along the band, 0..1
    out["lat"] = np.full(n, lat_c)
    out["width_m"] = window_px * py
    if counts is not None:
        cs = np.vstack([np.interp(x_dst, x_src, (row > 0).astype(float)) for row in counts]) > 0.5
        nw = cs.shape[1] // window_px
        out["observed_frac"] = cs[:window_px, :nw * window_px].reshape(window_px, nw, window_px).mean(axis=(0, 2))[:n]
    return out


POLAR_R_M = 3376200.0    # radius of the polar MEGDR projection (a_axis_radius 3376.2 km in their labels)
POLAR_PIXEL_M = 115.089465                  # pixel_resolution of the 512 ppd polar labels (km 0.115089465)


def polar_latlon(row: np.ndarray, col: np.ndarray, size: int, pixel_m: float, north: bool = True, radius_m: float = POLAR_R_M):
    """Latitude and longitude of pixel centres of a MEGDR polar grid (polar stereographic, pole at the centre; north:
    longitude 0 straight down, 90°E to the right; south: 0 straight up, 90°E to the right, per the MEGDR page)."""
    c = (size - 1) / 2
    x = (np.asarray(col, float) - c) * pixel_m
    y = (np.asarray(row, float) - c) * pixel_m
    rho = np.hypot(x, y)
    lat_abs = 90 - np.degrees(2 * np.arctan(rho / (2 * radius_m)))
    if north:
        lon = np.degrees(np.arctan2(x, y)) % 360
        return lat_abs, lon
    lon = np.degrees(np.arctan2(x, -y)) % 360
    return -lat_abs, lon


# --- profiles of the Martian environments (T48) ----------------------------------------------------------------

METRICS = ("slope_mean", "slope_p95", "roughness_detrended")
MIN_OBSERVED = 0.5        # E19: a window needs a MOLA shot in half its pixels; below, its terrain is mostly interpolated
SWIM_MIN = 0.0            # SWIM states no class boundary: Ci > 0 is "consistent with ice" (0 inconclusive); 0.25, 0.5 tested


def polar_windows(t_img: Path, c_img: Path | None, north: bool, pixel_m: float, window_px: int = WINDOW_PX) -> dict:
    """Every window of a MEGDR polar grid, in strips of window_px rows: metrics, observed share (NaN when no count
    grid is published, as for the 512 ppd polar grids), centre lat/lon."""
    from discovery.windows import ALL_METRICS, window_metrics_grid
    z = read_pds4(t_img)
    cnt = read_pds4(c_img) if c_img is not None and Path(c_img).exists() else None
    size = z.shape[0]
    cols = {k: [] for k in METRICS}
    cols.update(lat=[], lon=[], observed_frac=[])
    for r0 in range(0, size - window_px + 1, window_px):
        strip = z[r0:r0 + window_px].astype("float64")
        w = window_metrics_grid(strip, pixel_m, window_px, margin=0, metrics=ALL_METRICS)
        n = w["slope_mean"].shape[1]
        for k in METRICS:
            cols[k].append(w[k].ravel())
        if cnt is not None:
            cs = cnt[r0:r0 + window_px, :n * window_px] > 0
            cols["observed_frac"].append(cs.reshape(window_px, n, window_px).mean(axis=(0, 2)))
        else:
            cols["observed_frac"].append(np.full(n, np.nan))
        rc = np.full(n, r0 + (window_px - 1) / 2)
        cc = np.arange(n) * window_px + (window_px - 1) / 2
        la, lo = polar_latlon(rc, cc, size, pixel_m, north)
        cols["lat"].append(la)
        cols["lon"].append(lo)
    return {k: np.concatenate(v) for k, v in cols.items()}


def global_windows(tiles: list[tuple[Path, Path, float, float]], ppd: int = 128, lat_min: float = 0.0, lat_max: float = 60.0,
                   window_px: int = WINDOW_PX) -> dict:
    """Windows of the 128 ppd tiles (top latitude, west longitude) between lat_min and lat_max."""
    cols: dict = {k: [] for k in (*METRICS, "lat", "lon", "observed_frac")}
    for t_img, c_img, top, west in tiles:
        z = read_pds4(t_img)
        cnt = read_pds4(c_img)
        span = z.shape[1] / ppd
        for r0 in range(0, z.shape[0] - window_px + 1, window_px):
            lats = top - (np.arange(r0, r0 + window_px) + 0.5) / ppd
            if lats.mean() < lat_min or lats.mean() > lat_max:
                continue
            w = band_windows(z[r0:r0 + window_px], lats, ppd, window_px, counts=cnt[r0:r0 + window_px])
            for k in (*METRICS, "lat", "observed_frac"):
                cols[k].append(np.asarray(w[k]))
            cols["lon"].append(west + w["lon_frac"] * span)
    return {k: np.concatenate(v) if v else np.array([]) for k, v in cols.items()}


def swim_xy(lat, lon):
    """Metres of the SWIM grid: Mars equidistant cylindrical, sphere 3396190 m, central meridian 180°."""
    d = (np.mod(np.asarray(lon, float), 360) - 180 + 180) % 360 - 180
    return MARS_R_M * np.radians(d), MARS_R_M * np.radians(np.asarray(lat, float))


def sample_swim(path: Path, lat: np.ndarray, lon: np.ndarray) -> np.ndarray:
    """SWIM combined ice consistency at points (lon 0..360°E); NaN outside the map or at its nodata (-30)."""
    import rasterio
    x, y = swim_xy(lat, lon)
    with rasterio.open(path) as src:
        vals = np.array([v[0] for v in src.sample(list(zip(x.tolist(), y.tolist())))], float)
        nod = src.nodata if src.nodata is not None else -30
    vals[(vals == nod) | (vals <= -29)] = np.nan
    return vals


def volcanic_selection(units: np.ndarray, observed: np.ndarray, volcanic: set, edifices: set) -> tuple[np.ndarray, dict]:
    """Windows of the volcanic plains (T48c, E20): centre inside a volcanic unit of the Tanaka map and at least
    MIN_OBSERVED of the pixels hold a MOLA shot (E19, as for the ice-rich target). Sensitivity counts: without the
    volcanic edifices, and with any observed share."""
    u = np.asarray(units, dtype=object)
    obs = np.asarray(observed, float) >= MIN_OBSERVED
    in_v = np.array([x in volcanic for x in u], bool)
    in_e = np.array([x in edifices for x in u], bool)
    sel = in_v & obs
    return sel, {"all_volcanic_units": int(sel.sum()), "without_edifices": int((sel & ~in_e).sum()),
                 "any_observed_share": int(in_v.sum())}


GLOBAL_TILES = (("88n", 88.0), ("44n", 44.0), ("00n", 0.0), ("44s", -44.0))   # the 128 ppd MEGDR tiles, top latitude


def build_volcanic(mola: Path, geology: Path, out_dir: Path, json_dir: Path) -> dict:
    """The volcanic plains environment (T48c): MOLA 128 ppd windows of the whole planet inside the volcanic units of
    the Tanaka et al. 2014 map (`geology`: the SIM3292_Global_Geology shapefile, without extension)."""
    import json
    import pyarrow as pa
    import pyarrow.parquet as pq
    from discovery.mars_geology import UnitMap, edifice_units, volcanic_units
    from discovery.profiles import file_input, summarise
    name = "mars-volcanic-plains"
    tiles = [(mola / f"megt{la}{lo}hb.img", mola / f"megc{la}{lo}hb.img", top, float(lo))
             for la, top in GLOBAL_TILES for lo in ("000", "090", "180", "270")]
    w = global_windows(tiles, 128, -90.0, 90.0)
    gmap = UnitMap.read(geology)
    vol, edi = volcanic_units(gmap.descriptions), edifice_units(gmap.descriptions)
    units = gmap.unit_at(w["lat"], w["lon"])
    sel, sens = volcanic_selection(units, w["observed_frac"], vol, edi)
    params = {"units": sorted(vol), "edifices": sorted(edi), "unit_rule": "map description (UnitDesc) contains 'volcanic'",
              "window_rule": "window centre inside a unit (map at 1:20,000,000)", "min_observed": MIN_OBSERVED,
              "pixel_m": round(2 * math.pi * MARS_R_M / 360 / 128, 2), "window_px": WINDOW_PX, "windows_by_rule": sens,
              "windows_by_unit": {u: int(((units == u) & sel).sum()) for u in sorted(vol)}}
    shp = Path(str(geology) + ".shp")
    inputs = {"tanaka2014/SIM3292_Global_Geology.shp": file_input(shp),
              **{f"mola/{t[0].name}": file_input(t[0]) for t in tiles}}
    cols = {k: np.asarray(w[k])[sel].astype("float32") for k in (*METRICS, "observed_frac")}
    cols["lat"] = np.asarray(w["lat"])[sel].astype("float64")
    cols["lon"] = np.asarray(w["lon"])[sel].astype("float64")
    cols["unit"] = np.asarray(units)[sel].astype(str)
    out_dir.mkdir(parents=True, exist_ok=True)
    pq.write_table(pa.table(cols), out_dir / f"{name}.windows.parquet", compression="zstd")
    full = {k: np.asarray(w[k]) for k in METRICS}
    rec = {"id": name, "body": "mars", "spec": f"data/profiles/spec/{name}.yaml", "inputs": inputs, "params": params,
           "decision": "E19, E20", **summarise(full, sel, METRICS)}
    no_edifice = sel & ~np.array([x in edi for x in units], bool)
    rec["sensitivity"] = {"without_edifices": summarise(full, no_edifice, METRICS)}
    json_dir.mkdir(parents=True, exist_ok=True)
    (json_dir / f"{name}.json").write_text(json.dumps(rec, indent=1) + "\n", encoding="utf-8")
    return {name: {"windows": rec["windows"], "slope_mean": rec["metrics"]["slope_mean"], "params": params}}


def build_profiles(mola: Path, swim: Path, out_dir: Path, json_dir: Path) -> dict:
    """The three MOLA environments of phase 1 (polar terrain north and south, ice-rich mid-latitudes): windows
    parquet for the comparison engine, and a JSON summary per environment. Volcanic plains wait for the Tanaka map."""
    import json
    import pyarrow as pa
    import pyarrow.parquet as pq
    from discovery.profiles import file_input, summarise
    pole_px = POLAR_PIXEL_M
    out = {}
    envs = {}
    for name, north in (("mars-north-polar", True), ("mars-south-polar", False)):
        p = "n" if north else "s"
        w = polar_windows(mola / f"megt_{p}_512_1.img", None, north, pole_px)
        phi = 80.0                                                    # nominal; 75 and 85 reported as sensitivity
        valid = np.isfinite(w["slope_mean"])
        sel = (np.abs(w["lat"]) >= phi) & valid
        # the polar grids reach about 78°: 75° cannot be tested; no count grid is published at 512 ppd
        sens = {str(f): int(((np.abs(w["lat"]) >= f) & valid).sum()) for f in (80, 85)}
        envs[name] = (w, sel, {"phi_deg": phi, "pixel_m": round(pole_px, 3), "window_px": WINDOW_PX,
                               "observed_share": "not available: no count grid is published for the 512 ppd polar grids",
                               "grid_extent": "about 78° to the pole", "windows_by_phi": sens},
                      {f"mola/{p}": file_input(mola / f"megt_{p}_512_1.img")})
    tiles = []
    for la, top in (("88n", 88.0), ("44n", 44.0)):
        for lo in ("000", "090", "180", "270"):
            tiles.append((mola / f"megt{la}{lo}hb.img", mola / f"megc{la}{lo}hb.img", top, float(lo)))
    w = global_windows(tiles, 128, 0.0, 60.0)
    ci = sample_swim(swim, w["lat"], w["lon"])
    w["swim_ci"] = ci
    sel = (ci > SWIM_MIN) & (w["observed_frac"] >= MIN_OBSERVED)
    sens = {str(c): int(((ci > c) & (w["observed_frac"] >= MIN_OBSERVED)).sum()) for c in (0.0, 0.25, 0.5)}
    envs["mars-ice-rich-midlatitudes"] = (w, sel, {"swim_ci_above": SWIM_MIN, "pixel_m": round(2 * math.pi * MARS_R_M / 360 / 128, 2),
                                                   "window_px": WINDOW_PX, "min_observed": MIN_OBSERVED, "windows_by_ci": sens},
                                          {"swim/Northern_Ci": file_input(swim), **{f"mola/{t[0].name}": file_input(t[0]) for t in tiles}})
    for name, (w, sel, params, inputs) in envs.items():
        cols = {k: np.asarray(w[k])[sel].astype("float32") for k in (*METRICS, "observed_frac")}
        cols["lat"] = np.asarray(w["lat"])[sel].astype("float64")
        cols["lon"] = np.asarray(w["lon"])[sel].astype("float64")
        out_dir.mkdir(parents=True, exist_ok=True)
        pq.write_table(pa.table(cols), out_dir / f"{name}.windows.parquet", compression="zstd")
        rec = {"id": name, "body": "mars", "spec": f"data/profiles/spec/{name}.yaml", "inputs": inputs, "params": params,
               "decision": "E19", **summarise({k: np.asarray(w[k]) for k in METRICS}, sel, METRICS)}
        json_dir.mkdir(parents=True, exist_ok=True)
        (json_dir / f"{name}.json").write_text(json.dumps(rec, indent=1) + "\n", encoding="utf-8")
        out[name] = {"windows": rec["windows"], "slope_mean": rec["metrics"]["slope_mean"], "params": params}
    return out


def main(argv=None) -> int:
    import argparse
    import json
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--mola", type=Path, default=Path("/data/mola"))
    ap.add_argument("--swim", type=Path, default=Path("/data/swim/Northern_Ci.tif"))
    ap.add_argument("--out", type=Path, default=Path("/data/profiles/mars"))
    ap.add_argument("--json", type=Path, default=Path("data/profiles/mars"))
    ap.add_argument("--only", choices=["phase1", "volcanic"], default="phase1",
                    help="phase1: polar and ice-rich (T48); volcanic: the volcanic plains (T48c)")
    ap.add_argument("--geology", type=Path, default=Path(
        "/data/mars-geology/extracted/SIM3292_MarsGlobalGeologicGIS_20M/SIM3292_Shapefiles/SIM3292_Global_Geology"))
    a = ap.parse_args(argv)
    if a.only == "volcanic":
        print(json.dumps(build_volcanic(a.mola, a.geology, a.out, a.json), indent=1))
    else:
        print(json.dumps(build_profiles(a.mola, a.swim, a.out, a.json), indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
