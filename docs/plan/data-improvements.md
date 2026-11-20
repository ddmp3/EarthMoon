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
| D10 | An independent list of expected analogs and negative controls (E10) | Positive validation of scenarios A and B: none exists today | Needs analog researchers outside the project | David or the jury names reviewers | blocked |

## Moon

| # | Source | What it would improve | Blocked by | Unblock | Status |
|---|---|---|---|---|---|
| M1 | LOLA 5 m south pole mosaic, compared at 5 m | The persistently lit target is "not comparable": no Earth cube at 5 m | No global Earth DEM at 5 m | Regional lidar DEMs for candidate zones only | blocked |
| M2 | Diviner polar temperature maps (Williams et al. 2019) | Lunar thermal context of each environment (T47) | Not verified in the catalogue | Verify the PDS product | ready |
| M3 | NAC DTMs of lunar pits | Slopes at the pits themselves instead of a context window | Public DTMs preliminary, post spacing not stated (T41) | Wait for final DTMs, or verify the existing ones | blocked |

## Mars (T48)
To be filled when T48 starts.
