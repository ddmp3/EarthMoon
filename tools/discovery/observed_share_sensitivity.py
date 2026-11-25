"""Sensitivity of the volcanic plains profile to the E19 observed-share rule: slope and latitude by observed share."""
import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, "/repo/tools")
from discovery.mars import GLOBAL_TILES, global_windows  # noqa: E402
from discovery.mars_geology import UnitMap, volcanic_units  # noqa: E402

mola = Path("/data/mola")
geo = Path("/data/mars-geology/extracted/SIM3292_MarsGlobalGeologicGIS_20M/SIM3292_Shapefiles/SIM3292_Global_Geology")
tiles = [(mola / f"megt{la}{lo}hb.img", mola / f"megc{la}{lo}hb.img", top, float(lo))
         for la, top in GLOBAL_TILES for lo in ("000", "090", "180", "270")]
w = global_windows(tiles, 128, -90.0, 90.0)
m = UnitMap.read(geo)
u = m.unit_at(w["lat"], w["lon"])
vol = volcanic_units(m.descriptions)
inv = np.array([x in vol for x in u], bool) & np.isfinite(w["slope_mean"])
obs = np.asarray(w["observed_frac"], float)
s = np.asarray(w["slope_mean"], float)
lat = np.asarray(w["lat"], float)
out = {"volcanic_windows": int(inv.sum()), "observed_share_quantiles": {}, "by_observed_bin": [], "by_lat_band": []}
for q in (10, 25, 50, 75, 90):
    out["observed_share_quantiles"][str(q)] = round(float(np.percentile(obs[inv], q)), 3)
for lo, hi in ((0, 0.1), (0.1, 0.2), (0.2, 0.3), (0.3, 0.4), (0.4, 0.5), (0.5, 1.01)):
    k = inv & (obs >= lo) & (obs < hi)
    if k.sum():
        out["by_observed_bin"].append({"bin": [lo, min(hi, 1.0)], "windows": int(k.sum()),
                                       "slope_p25": round(float(np.percentile(s[k], 25)), 3),
                                       "slope_p50": round(float(np.percentile(s[k], 50)), 3),
                                       "slope_p75": round(float(np.percentile(s[k], 75)), 3),
                                       "lat_median": round(float(np.median(lat[k])), 1)})
for a in range(-90, 90, 20):
    k = inv & (lat >= a) & (lat < a + 20)
    if k.sum():
        kk = k & (obs >= 0.5)
        out["by_lat_band"].append({"band": [a, a + 20], "volcanic_windows": int(k.sum()), "kept": int(kk.sum()),
                                   "slope_p50_all": round(float(np.median(s[k])), 3),
                                   "slope_p50_kept": round(float(np.median(s[kk])), 3) if kk.sum() else None})
print(json.dumps(out, indent=1))
