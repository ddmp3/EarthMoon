"""T43: write the run-001 zone dossiers into docs/wiki/runs/run-001/ (run in Docker with the repo at /repo).

Outcomes come from tools/discovery/dossier.outcome (rule committed before any dossier was written).
Images: DEM hillshades at 80 m (one per place) and world maps at 0.25°, to keep the repository light."""
import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, "/repo/tools")
from discovery.discover import load_cells  # noqa: E402
from discovery.dossier import outcome, world_map, write_png_rgb, zone_hillshade  # noqa: E402

RUN = Path("/data/run001")
OUT = Path("/repo/docs/wiki/runs/run-001")
(OUT / "zones").mkdir(parents=True, exist_ok=True)
facts = json.loads((RUN / "report/zones/facts.json").read_text(encoding="utf-8"))
evidence = json.loads((RUN / "dossier-evidence.json").read_text())
lit = json.loads((RUN / "literature.json").read_text(encoding="utf-8"))["searches"]


def lit_for(lat, lon):
    for s in lit:
        for part in s["place"].split(" (")[0].split(" / "):
            la, lo = (float(x) for x in part.split(","))
            if abs(la - lat) < 0.02 and abs(lo - lon) < 0.02:
                return s
    return None


images, rows = {}, []
for zid in sorted(facts):
    f, e = facts[zid], evidence[zid]
    key = f"{f['lat']:.2f},{f['lon']:.2f}"
    if key not in images:
        images[key] = f"{zid}.png"
        zone_hillshade(f, Path("/glo30"), OUT / "zones" / images[key], pixel_m=80.0)
    s = lit_for(f["lat"], f["lon"])
    res, why = outcome(e["windows"], e["cells"], e["mean_masked_share"], None if s is None else s["match"])
    rows.append((zid, f, e, res, why, s))
    med = np.array(f["cell_medians"], float)
    lines = [
        f"# Zone {zid}: {f['place']}",
        "",
        f"run-001, scenario {zid[0]}, target `{f['target']}`" + (f", also found for {', '.join('`' + x + '`' for x in f['also_for'])}" if f["also_for"] else "") + ".",
        "",
        f"**Outcome: {res}.** {why[0].upper() + why[1:]}.",
        "",
        "| Value | |",
        "|---|---|",
        f"| Centre | {f['lat']:.4f}, {f['lon']:.4f} |",
        f"| Cells, area | {f['cells']} cells, {f['area_km2']:.0f} km² |",
        f"| Median typicality (median of cell medians) | {f['median']:.3f} (cells: p25 {np.percentile(med, 25):.3f}, p75 {np.percentile(med, 75):.3f}) |",
        f"| Windows: all, compared (unmasked) | {e['windows']}, {e['windows'] - round(e['mean_masked_share'] * e['windows'])} (mean masked share {e['mean_masked_share']:.2f}) |",
        f"| Windows per cell | {e['windows'] / e['cells']:.1f} (a full 5 km cell has about 25) |",
        f"| High-confidence cells | {f['high_confidence_share']:.0%} |",
        f"| Monte Carlo: runs in the sample's top decile | {f['mc_top_decile_share']:.0%} |" if f.get("mc_top_decile_share") is not None else "| Monte Carlo | not available |",
        "",
        f"![DEM hillshade, 30 x 30 km, Copernicus GLO-30 at 80 m]({images[key]})",
        "",
        "Relief only (hillshade of the Copernicus DEM): no optical imagery is used.",
        "",
        "## Literature",
        "",
    ]
    if s:
        lines += [f"- Query: `{s['query']}`", f"- Finding: {s['finding']}", "- Sources: " + ", ".join(f"<{u}>" for u in s["sources"])]
    else:
        lines += ["- No search: the outcome follows from the data alone (rule above)."]
    (OUT / "zones" / f"{zid}.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(zid, res, key)

# world maps at 0.25°
cells = load_cells(str(RUN / "cells.parquet"))
lat = np.asarray(cells["lat"], float)
lon = np.asarray(cells["lon"], float)
ms = np.nan_to_num(np.asarray(cells["masked_share"], float), nan=1.0)
ok = np.isfinite(lat) & np.isfinite(lon)
zs = json.loads((RUN / "zones.json").read_text())["scenarios"]
pos = {c: i for i, c in enumerate(cells["cell"])}
for sc, v in zs.items():
    for t in v["targets"]:
        med = np.asarray(cells[f"{t}:median"], float)
        cls = np.where(ms >= 0.5, 1, np.where(np.isfinite(med), 2, 1))
        inz = np.zeros(lat.size, bool)
        inz[[pos[c] for z in json.loads((RUN / f"zones-{sc}-{t}.json").read_text()) for c in z["cell_ids"] if c in pos]] = True
        cls = np.where(inz, 3, cls)
        write_png_rgb(OUT / f"map-{sc}-{t}.png", world_map(lat[ok], lon[ok], cls[ok], deg=0.25))
        print("map", sc, t)
json.dump([{"zone": r[0], "outcome": r[3], "why": r[4]} for r in rows], open(OUT / "outcomes.json", "w"), indent=1)
