"""Earth window slopes at the R29 control cells (463 m scale) against the Martian volcanic plains profile."""
import json
import sys

import numpy as np
import pyarrow.parquet as pq

sys.path.insert(0, "/repo/tools")
from discovery.discover import global_cell  # noqa: E402
from discovery.copernicus import tile_name  # noqa: E402

ctl = [("Big Craters", 43.44379, -113.56113), ("Mauna Ulu", 19.36733, -155.20157),
       ("Kilauea Iki", 19.41374, -155.24662), ("Kilauea caldera", 19.39591, -155.28608)]
prof = pq.read_table("/data/profiles/mars/mars-volcanic-plains.windows.parquet", columns=["slope_mean"]).column(0).to_numpy()
print("mars volcanic slope p25/p50/p75", np.percentile(prof, [25, 50, 75]).round(3).tolist())
names = pq.read_schema("/data/run-mars-002/cells.parquet").names
print([n for n in names if "volcanic" in n])
out = []
for name, la, lo in ctl:
    f = f"/data/cube/glo90-463m-w25/{tile_name(int(np.floor(la)), int(np.floor(lo)), 'glo90')}.windows.parquet"
    t = pq.read_table(f).to_pydict()
    lat, lon, s = np.array(t["lat"]), np.array(t["lon"]), np.array(t["slope_mean"], float)
    d = np.hypot((lat - la) * 111.2, (lon - lo) * 111.2 * np.cos(np.radians(la)))
    near = d < 12
    out.append({"control": name, "windows_within_12km": int(near.sum()),
                "earth_slope": np.round(s[near], 2).tolist(),
                "earth_slope_percentile_in_mars_profile": [round(float(np.mean(prof < x) * 100), 1) for x in s[near]]})
print(json.dumps(out, indent=1))
