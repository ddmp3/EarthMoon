# Data improvement backlog

The data and making them available are the core of EarthMoon (David, 20/11/2026). Each entry below is a better source than the one in use, or a gap only data can close: what it would improve, what blocks it, and who can unblock it. This list is reviewed at every gate. When a task meets a better source it cannot use yet, it adds a row here; it never settles silently for the lesser one.

Status: **blocked** (waiting on an action), **ready** (can be done), **done** (with the release that uses it).

## Earth

| # | Source | What it would improve | Blocked by | Unblock | Status |
|---|---|---|---|---|---|
| D1 | MODIS land surface temperature, multi-year (MOD11A2/MOD11C3, LP DAAC) | Thermal cycling layer (T47): day-night swing with its interannual sigma | NASA Earthdata account | David creates a free Earthdata account; credentials in an uncommitted local file (ADR-009) | blocked |
| D2 | ERA5-Land hourly, 1950 onwards (Copernicus CDS) | Air and soil temperature, snow, soil moisture, multi-year with sigma; would replace the v2 NASA POWER values | CDS account and licence acceptance | David creates a CDS account | blocked |
| D3 | EMIT L2B minerals, 60 m, 52°N to 52°S | Mineralogy beside lithology (T46): plagioclase, pyroxene, olivine bands | Earthdata account (as D1) | as D1 | blocked |
| D4 | ASTER GED emissivity, 100 m | Silica content indicator for the geology dimension | Earthdata account (as D1) | as D1 | blocked |
| D5 | Macrostrat world map 1:35M (source 154) where `carto` has no unit | 29.2% of samples have no map unit (Deccan, Tibet, Gobi, Kamchatka) | Not in the `carto` tiles; only the point API serves it | Query the point API once per no-map 1° tile, politely; or use D6 | ready |
| D6 | GLiM polygons (1.2 M polygons, 1:3.75M) | A global lithology layer with no hole | Licence not stated on the download pages | Write to the authors (Hartmann, Moosdorf) for the licence | blocked |
| D7 | Finer national geological maps (for example Newfoundland and Labrador 1:1M; OneGeology services) | Mistastin's anorthosite is below the 1:5M map; anorthosite bodies of impact structures | OneGeology portal certificate error; national licences to check | Check each map's licence and access | ready |
| D8 | A bare-earth DEM (forest and buildings removed, for example FABDEM) | 38% of the evaluated land is masked as hidden ground; slope under forest could be measured instead | Licence (FABDEM is non-commercial; to verify) and its own error model | Verify licence and accuracy; compare on the pilot tiles | ready |
| D9 | ESA Permafrost_cci v5 | Frozen ground in both hemispheres (Obu 2018 covers only the north) | Licence not stated on page (partly verified) | Verify licence | ready |
| D11 | Aridity index v3.1 with a stated nodata value, or a land mask | 0 marks both the sea and an index below 0.0001; treated as no data, so the driest cores (Atacama) may show no data | The README (figshare, MD5 ad026eba…) states no nodata value | Ask the authors (Zomer, Trabucco), or mask the sea with our own land cells | ready |
| D10 | An independent list of expected analogs and negative controls (E10) | Positive validation of scenarios A and B: none exists today | Needs analog researchers outside the project | David or the jury names reviewers | blocked |

## Moon

| # | Source | What it would improve | Blocked by | Unblock | Status |
|---|---|---|---|---|---|
| M1 | LOLA 5 m south pole mosaic, compared at 5 m | The persistently lit target is "not comparable": no Earth cube at 5 m | No global Earth DEM at 5 m | Regional lidar DEMs for candidate zones only | blocked |
| M2 | Diviner polar temperature maps (Williams et al. 2019) | Lunar thermal context of each environment (T47) | Not verified in the catalogue | Verify the PDS product | ready |
| M3 | NAC DTMs of lunar pits | Slopes at the pits themselves instead of a context window | Public DTMs preliminary, post spacing not stated (T41) | Wait for final DTMs, or verify the existing ones | blocked |

## Mars (T48)

| # | Source | What it would improve | Blocked by | Unblock | Status |
|---|---|---|---|---|---|
| R1 | MOLA-HRSC blended global DEM, 200 m (`mola-hrsc-blended-dem`) | Mid-latitude windows of 5 km instead of 11.6 km (MOLA 463 m) | Not verified: effective resolution between HRSC strips, licence | Verify the USGS product and its effective resolution | ready |
| R2 | HRSC DTMs, 50 m (`mex-hrsc-dtm`) | Terrain at 1.25 km windows where strips exist | Strips, not global: a site-set profile, not a global one | A sampling rule for strips decided before computing (E19 follow-up) | ready |
| R3 | HiRISE DTMs, 1 to 2 m (`mro-hirise-dtm`) | The rover-scale target (now "not comparable") and the MSL mobility limits (R43, E14) | 1,377 DTMs, large; no global Earth DEM at that scale | Regional Earth lidar for candidate zones only (as M1) | blocked |
| R4 | A shot-count grid for the 512 ppd polar MOLA grids | The observed share of polar windows (now "not available") | Not published (404 on the PDS node) | Rebuild it from PEDR shots (`mgs-mola-pedr`), or ask the PDS node | ready |
| R5 | Mars geologic map, Tanaka et al. 2014 (`usgs-mars-geologic-map-2014`) | Volcanic plains target and the only positive controls of scenario D (R29) | The USGS publications site blocks automated download | David downloads the ZIP in a browser into `earthmoon-data/mars-geology/` | blocked |
| R6 | THEMIS thermal inertia (`ody-themis-mosaics-ti`) | Grain size and induration (scenario D similarity) | Not verified | Verify the product and its units | ready |
| R7 | Mars Climate Database (`lmd-mars-climate-database`) | Wind, dust and humidity of scenario D | Free registration by email | David registers | blocked |
| R8 | SWIM ice consistency licence (`swim-ice-consistency`) | Use of the ice-rich target is stated as allowed | Licence not stated on the download page | Ask the SWIM team, or verify on the project page | ready |
| R9 | SWIM 2.0 products (`swim.psi.edu/SWIM2Products.php`) | The ice-rich target is built on the 2019 Northern Hemisphere SWIM products, which the page calls "superseded by the SWIM 2.0 products" (read 23/11, T52) | Not verified: coverage, format, licence and changes from 2019 | Verify the SWIM 2.0 page and products, then a protocol mars-v3 decided before any rerun | ready |

