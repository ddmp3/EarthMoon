# Scenarios (v3)

Machine-readable versions: `data/scenarios/*.yaml`, checked by `python tools/profiles/profiles.py`. They replace `data/reference/scenarios-v2.json` in T42.

**Rules for all scenarios:**
- Similarity, operational requirements, eliminating constraints and confidence are separate outputs. A good similarity never offsets an operational failure.
- Similarity uses only the parameters kept in T21, each scored with the T23 percentile. Dimensions are shown separately; a global value is their minimum.
- Every number has a checked source or an expert decision label (E1 to E16 in [LIMITS.md](LIMITS.md)).
- "Waiting" means that the layer is computed in a later task. Until then, the dimension is shown as missing, never as zero.

## A. Permanent lunar base

| | |
|---|---|
| Targets | Lit polar highlands; persistently lit areas; permanently shadowed regions; pits (E16) |
| Similarity | Slope (available); lithology (T46); day-night temperature amplitude (T47) |
| Requirements | Base slope at most 5°, unsuitable above 10° (E2). Bearing capacity, boulders and landing hazards are not set (E13) |
| Eliminating | None yet: no requirement has a checked source |
| Proxy | Natural shelter → curated lava tube evidence (E7); never proximity to a volcano |
| Cannot assess | Gravity, vacuum, radiation; grazing sunlight and cryogenic shadow; regolith mechanics; volatile resources |

v2's colony scenario ("cold, polar, flat, quiet") is gone (finding K2, E3).

## B. Robotic lunar exploration

| | |
|---|---|
| Targets | Lit polar highlands; shadowed regions; mare plains; whole polar cap (v2 anchor) |
| Similarity | Slope (available); lithology (T46). Detrended roughness is context only, until T41 |
| Requirements | **Apollo LRV: 20 to 23°, maximum 25° (NTRS 20250011301, verified), eliminating.** VIPER 15° and "half the window" (E1) |
| Cannot assess | Obstacles below the pixel; traction under lunar gravity; lunar night; navigation without GNSS |

The only verified limit is for a crewed rover. A robotic limit needs E1.

## C. Instrument calibration and validation

One row per instrument; site requirements are all open (E15).

| Instrument | Targets | Similarity | Cannot assess |
|---|---|---|---|
| C1 Geology | Mare plains; Martian volcanic plains | Lithology (T46) | Weathering at instrument scale |
| C2 Navigation | Lit highlands; shadowed regions | Slope | Low Sun angle; no GNSS |
| C3 Thermal sensors | Mare plains; Martian HiRISE terrain | Temperature amplitude; thermal inertia (T47) | Absolute lunar temperatures |
| C4 Radar | Pits; Martian ice-rich mid-latitudes | Ground ice (T47) | Dry regolith dielectrics; voids |
| C5 Mineralogy | Martian aqueous mineral sites | Mineral groups (T46) | Abundances; lunar mineralogy |
| C6 Sampling | Mare plains; Martian ice-rich ground | Lithology, ground ice | Regolith grain size (E9). Frozen ground at most -6 °C (E4, a permafrost proxy) |
| C7 Mobility | As B | Slope | Traction |

## D. Mars exploration and settlement

| | |
|---|---|
| Targets | Ice-rich mid-latitudes; north and south polar terrain; aqueous mineral sites; HiRISE rover-scale terrain |
| Similarity | Slope (T48); mineral groups (T46); ground ice, thermal inertia, aerosols, wind, specific humidity, precipitation (T47) |
| Requirements | MSL test vehicles (R43): up to 22° on smooth bedrock, 28° on some cohesive soils, embedding at 17° in loose sand. Which applies depends on terrain type (E14), so none eliminates |
| Proxy | Martian ground ice → Earth permafrost models, compared as classes |
| Cannot assess | CO₂ atmosphere at about 1% of Earth's pressure; gravity; radiation; ice content and depth |

Mars is profiled from Martian data only; no lunar criterion is reused with new weights.
