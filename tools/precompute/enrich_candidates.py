"""Option 1 (offline precompute): add Copernicus DEM geometry to every site of data/candidates.json.

    python enrich_candidates.py data/candidates.json            # rewrites the file in place
    python enrich_candidates.py data/candidates.json -o out.json
    python enrich_candidates.py data/candidates.json --force    # recompute sites that already have values

Input: a JSON list of sites, each with at least  id, name, lat, lon  (other keys are kept untouched).
Output: the same list, each site gaining a "precomputed" block with the catalogue IDs of docs/history/v1-scenarios.md:
    elevation, slope_mean, slope_max, roughness  (+ source, window_m, valid_frac, computed_at)
A site whose tile is missing keeps null values and an "error" message; the run never stops on one bad site.
"""
from __future__ import annotations
import argparse
import json
import sys
import time
from datetime import datetime, timezone

from point_geometry import TileNotFound, point_geometry

KEYS = ("elevation", "slope_mean", "slope_max", "roughness")


def enrich_site(site: dict, window_m: float = 1000.0, retries: int = 2, geometry_fn=point_geometry) -> dict:
    block = {k: None for k in KEYS}
    block.update({"source": "Copernicus DEM GLO-30", "window_m": window_m,
                  "computed_at": datetime.now(timezone.utc).isoformat(timespec="seconds")})
    for attempt in range(retries + 1):
        try:
            g = geometry_fn(float(site["lat"]), float(site["lon"]), window_m=window_m)
            block.update({k: g[k] for k in KEYS})
            block["valid_frac"] = g["valid_frac"]
            break
        except TileNotFound as e:                      # ocean / tile not published: no point retrying
            block["error"] = str(e)
            break
        except Exception as e:                         # network hiccup etc.
            block["error"] = f"{type(e).__name__}: {e}"
            if attempt < retries:
                time.sleep(1.5 * (attempt + 1))
    if all(block[k] is not None for k in KEYS):
        block.pop("error", None)
    # Keep values written by other tools (e.g. MODIS from modis_values.py); refresh only the geometry fields.
    previous = {k: v for k, v in (site.get("precomputed") or {}).items() if k != "error"}
    return {**site, "precomputed": {**previous, **block}}


def enrich(sites: list[dict], window_m: float = 1000.0, force: bool = False, geometry_fn=point_geometry) -> list[dict]:
    out, seen = [], set()
    for s in sites:
        for k in ("id", "name", "lat", "lon"):
            if k not in s:
                raise ValueError(f"site without '{k}': {s}")
        if s["id"] in seen:
            raise ValueError(f"duplicate id: {s['id']}")
        seen.add(s["id"])
        done = s.get("precomputed") and all(s["precomputed"].get(k) is not None for k in KEYS)
        if done and not force:
            out.append(s)
            print(f"  skip  {s['id']} (already computed)")
            continue
        r = enrich_site(s, window_m, geometry_fn=geometry_fn)
        p = r["precomputed"]
        print(f"  {'FAIL' if 'error' in p else 'ok  '}  {s['id']}: " +
              (p.get("error") or f"slope_mean={p['slope_mean']} slope_max={p['slope_max']} roughness={p['roughness']} elev={p['elevation']}"))
        out.append(r)
    return out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("candidates")
    ap.add_argument("-o", "--output", default=None, help="default: rewrite the input file")
    ap.add_argument("--window-m", type=float, default=1000.0)
    ap.add_argument("--force", action="store_true")
    a = ap.parse_args(argv)
    with open(a.candidates, encoding="utf-8") as fh:
        sites = json.load(fh)
    if not isinstance(sites, list):
        sys.exit("candidates.json must be a JSON list of sites")
    out = enrich(sites, a.window_m, a.force)
    with open(a.output or a.candidates, "w", encoding="utf-8") as fh:
        json.dump(out, fh, ensure_ascii=False, indent=2)
        fh.write("\n")
    failed = [s["id"] for s in out if "error" in s.get("precomputed", {})]
    print(f"{len(out) - len(failed)}/{len(out)} sites with geometry" + (f" | failed: {failed}" if failed else ""))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
