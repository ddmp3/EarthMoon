# Scientific audit of EarthMoon (methodology v1)

Audit date: 17 November 2026. Scope: data, processing, indicators, scoring and interpretation. The website, its infrastructure, deployment and security are out of scope.

This document describes methodology v1 as it was implemented on `main` (commit `5822942`) and judges it. The corrections are in [SCIENTIFIC_METHODOLOGY.md](SCIENTIFIC_METHODOLOGY.md) and [SCIENTIFIC_ROADMAP.md](SCIENTIFIC_ROADMAP.md); the measured before / after comparison is in [SCIENTIFIC_VALIDATION.md](SCIENTIFIC_VALIDATION.md). References `[Rn]` are listed in [SCIENTIFIC_REFERENCES.md](../../REFERENCES.md).

Every number in this audit was recomputed from the code and the data, not copied from the documentation. The scripts are in the repository: `tools/validation/ablation.py`, `tools/validation/science_grid.py`, `tools/precompute/`.

## 1. Summary

EarthMoon v1 ranks 37 hand-picked Earth sites for three missions (rover mobility, instrument calibration, self-sufficient base) against the lunar south pole. Its engineering is sound and its documentation is unusually honest about limits. Its science has six problems that change the results:

| # | Finding | Severity | Effect on v1 results |
|---|---|---|---|
| V1 | Distance to a Holocene volcano is used as a stand-in for basalt and for lava tubes | Critical | Used in all three modes. Mistastin, the only anorthosite site (the rock of the lunar highlands), is 2,333 km from a volcano and scores 0; Erebus (phonolite) and Licancabur (andesite) score 1 for "basalt" |
| S1 | Earthquakes are counted from magnitude 2.5, where the catalog is complete only near dense networks | Critical | The count measures the number of seismometers as much as seismicity: Meteor Crater 745 events, Tolbachik (Kamchatka subduction zone) 2,081, a ratio of 2.8 where real seismicity differs by a factor of about 400 |
| C1 | Air temperature comes from a 50 km reanalysis cell and is not corrected to the site elevation | Critical | 12 of 37 sites are more than 300 m off, 6 more than 1,000 m. Mauna Kea is scored at 20.9 °C (its cell is at 636 m, the site at 3,730 m) |
| T2 | "Roughness" is the standard deviation of elevation without removing the tilt | Major | It measures slope a second time (correlation 0.96 with mean slope). The two criteria carry half of the robotics weight |
| M1 | Weights, tolerances and most intervals have no measured basis; all criteria are averaged | Major | Only 28% of the weight rests on a lunar measurement or a documented requirement. Erebus (mean slope 21°, 70% of the ground steeper than 15°) gets 55/100 for rover mobility and 77/100 as a place to build a base |
| R1 | Scores depend on live APIs read at request time | Major | No result can be reproduced: the USGS count changes daily (Mauna Kea: 20,397 then 20,383 with a fixed end date) |

Twelve further findings are listed in section 5. What v1 does well is listed in section 6.

## 2. How v1 works, from source to score

```
data/candidates.json (37 points)
        |
        |-- live, at each request -----------------------------------------------
        |     NASA POWER climatology  -> t2m_mean, t2m_min, t2m_max, wind, humidity, precipitation, solar
        |     USGS ComCat count       -> quake_count
        |     Smithsonian GVP list    -> volcano_distance
        |-- precomputed offline (data/candidates-precomputed.json) ---------------
        |     Copernicus DEM GLO-30   -> elevation, slope_mean, slope_max, roughness
        |     MODIS MOD11A2 / MOD13A1 -> lst_day, lst_night, lst_amplitude, ndvi
        v
  merge values (a failing source gives null)
        v
  per criterion: score = 1 inside [min, max], linear to 0 at distance `tolerance`
        v
  site total = 100 x sum(weight x score) / sum(weight), criteria without a value left out
        v
  x vegetation factor (1 up to NDVI 0.2, linear to 0 at NDVI 0.6)
        v
  sort by total; 500 perturbations of weights (±50%), tolerances (±25%), bounds (±10%) give a rank range
```

Implementation: `apps/api/src/scoring/score.ts`, `modes.ts`, `sensitivity.ts`; connectors in `apps/api/src/sources/`; offline processing in `tools/precompute/`.

## 3. Data sources as used in v1

| Source | Producer | Parameters, units | Resolution | Coverage | Processing in v1 | Known limits |
|---|---|---|---|---|---|---|
| NASA POWER climatology API v2.10 | NASA Langley; meteorology from MERRA-2 [R30], solar from CERES SYN1deg | `t2m_mean`, `t2m_min`, `t2m_max` (°C), `wind` at 2 m (m/s), `humidity` relative (%), `precipitation` (mm/day), `solar` (kWh/m²/day) | 0.5° x 0.625° (about 50 km) for meteorology, 1° for solar; 25-year climatology (2001 to 2025), annual value `ANN` | Global | None: the `ANN` value of the cell containing the point | A cell is not a site. The API returns the cell elevation, which v1 ignored. `T2M_MIN` `ANN` is the lowest of the twelve monthly values, not a mean daily minimum |
| USGS ComCat (FDSN count) | U.S. Geological Survey | `quake_count`: events M ≥ 2.5 within 300 km since 2000-01-01 | Point events | Global, but complete at M 2.5 only where networks are dense | None; no end date | Completeness varies by region; the count grows every day |
| Smithsonian GVP, Volcanoes of the World | Smithsonian Institution | `volcano_distance` (km) to the nearest of 1,214 Holocene volcanoes | One point per volcano | Global, Holocene only | Great-circle distance to the nearest point | A volcano is a point, a volcanic field is tens of km wide; basalt fields older than the Holocene are absent (the Black Point flow is not in the list; it is 42 km from the nearest listed vent); rock type ignored |
| Copernicus DEM GLO-30 | ESA / EU, from TanDEM-X (DLR, Airbus) | `elevation` (m), `slope_mean`, `slope_max` (°), `roughness` (m) | 1 arc-second in latitude (about 30 m); coarser in longitude at high latitude | Global land | Central differences on the geographic grid, statistics over one 1 km window centred on the point | Surface model (includes vegetation and buildings); edited flat over water and salt flats; absolute vertical accuracy better than 4 m (90%) [R37] |
| MODIS MOD11A2 / MYD11A2 v6.1 | NASA LP DAAC, via Microsoft Planetary Computer | `lst_day`, `lst_night`, `lst_amplitude` (°C) | 1 km, 8-day composites | Global | 12 composites of 2024, one pixel; mean of valid values; null under 6 valid | Clear-sky only; two overpass times, not the daily extremes; one year; accuracy about 1 K in most conditions [R33] |
| MODIS MOD13A1 / MYD13A1 v6.1 | NASA LP DAAC | `ndvi` | 500 m, 16-day composites | Global | 12 composites of 2024, one pixel; median | One pixel for a site that can be tens of km wide |
| LRO LOLA LDEM_85S_40M | NASA GSFC, PDS Geosciences Node [R3] | Lunar `slope_mean`, `slope_max`, `roughness` | 40 m per pixel, 85°S to 90°S | South polar cap | Same slope function as Earth; statistics over 71,731 non-overlapping 1 km windows; interquartile range kept | Interpolated between ground tracks; whole cap, shadowed crater walls included; 40 m baseline versus about 30 m on Earth |
| Published values | Paige et al. 2010 [R1], NASA fact sheet, NASA Artemis III release | Coldest shadowed temperatures, gravity, pressure, latitude band | n/a | n/a | Copied into `data/reference/moon-south-pole.json` | Used for display, not for scoring |

Only three of the 18 parameters have a lunar value computed from lunar data: `slope_mean`, `slope_max` and `roughness`. For every other parameter the "lunar equivalent" is an absence (no wind, no humidity, no rain) or a quantity Earth cannot approach (cold of shadowed regions). The tool is therefore not measuring similarity to the Moon on most criteria; it is ranking Earth sites by how dry, cold, calm and bare they are.

Data not used although relevant: the POWER cell elevation, specific humidity (`QV2M`), the GVP rock type and landform of each volcano, the MODIS quality layers, the lunar composition, illumination and rock abundance products (section 5, finding X1).

## 4. Indicators one by one

For each indicator: what it really measures, whether its use in v1 is correct, and what it does and does not allow one to conclude.

| Indicator | What it measures | Use in v1 | Verdict |
|---|---|---|---|
| `slope_mean` | Mean slope at about 30 m baseline over one 1 km window around one point | Robotics: similarity to the lunar interquartile range (5 to 13°), tolerance 10°. Colony: ≤ 5° | Sound in principle: the only criterion computed the same way on both bodies. Limits: baseline differs (30 m vs 40 m), one window stands for a whole site, 30 to 40 m slopes say little about the 1 to 5 m slopes a rover meets [R4, R5]. The 10° tolerance is arbitrary |
| `slope_max` | Maximum pixel slope in the window | Robotics: target 15 to 30° "from rover limits" | Not defensible. A maximum is an extreme-value statistic driven by DEM noise and resolution. Rover limits are operational constraints, yet they are used here as a two-sided similarity target: a site whose steepest pixel is 10° is penalized for being too gentle |
| `roughness` | Standard deviation of elevation in the window, tilt included | Robotics: similarity to the lunar interquartile range (22 to 65 m) | Not what its name says. A perfectly smooth plane tilted at the lunar median slope (8.3°) has a "roughness" of 42 m, inside the target. Measured on the 37 sites: correlation with `slope_mean` 0.96 (Spearman 0.97). It counts slope twice |
| `elevation` | Elevation of the point | Free criteria only | No lunar meaning; harmless |
| `ndvi` | Greenness of one 500 m pixel, 2024 median | Multiplier on the total | Reasonable as a bare-ground filter. It is not a similarity criterion and should not be presented as one. Missing for three polar sites (no valid composite) |
| `lst_day`, `lst_night` | Clear-sky surface temperature at the two satellite overpass times, mean of up to 12 composites of 2024 | Free criteria only | Biased toward the sunlit season at high latitude (10 valid composites out of 12 for Haughton) |
| `lst_amplitude` | Mean day-minus-night difference between two overpass times | Robotics and calibration: "thermal cycling" | Weak proxy. It is driven by latitude (Spearman -0.64 with absolute latitude; mean 4 °C above 60°, 20 °C below 40°) because polar sites have little daily cycle. The lunar swing is about 300 K [R12]. Irrelevant to rover mobility, where it was used |
| `t2m_mean` | 25-year mean air temperature of a 50 km cell | Calibration: "frozen ground"; colony: "permafrost, proxy for ice" | The permafrost link is physically grounded [R32], but the value is wrong wherever the cell and the site differ in elevation (finding C1), and the tolerance (10 °C) gives a positive "frozen ground" score at +9 °C |
| `t2m_min` | Lowest monthly minimum of the climatology, same cell | "Cold soak" and "life-support stress" | Same elevation error. Used three times as a cold criterion alongside `t2m_mean` (correlation 0.94) and latitude (-0.91): in the colony mode 6 of 13 weight points ask the same question, "is it polar?" |
| `wind` | Mean wind at 2 m of a 50 km cell | Calibration: "wind instrument" baseline | There is no wind on the Moon and no lunar wind instrument. Low wind is a legitimate test-quality condition (wind is a leading noise source for surface seismometers) but it is not an analogy |
| `humidity` | Relative humidity at 2 m | Calibration: "dry atmosphere" | Wrong quantity. Relative humidity is relative to saturation, which depends on temperature: Haughton has 94% relative humidity and 1.8 g/kg of water vapour, the Atacama point 25% and 3.1 g/kg. v1 ranks the drier air as the wetter. Spearman correlation with temperature -0.71 |
| `precipitation` | Mean precipitation of a 50 km cell | Robotics: "dry, loose ground" | Acceptable as a coarse proxy for dry ground. It is not a soil property: nothing is known about grain size, cohesion or bearing strength |
| `solar` | Annual mean all-sky insolation on a horizontal surface | Colony: "minimum solar potential" | No lunar meaning. Lunar polar illumination is set by a 1.54° obliquity and by topography, with ridges lit most of the year at grazing incidence [R6, R7, R8]. On Earth it is anticorrelated with the latitude criterion of the same mode (-0.83): the two criteria partly cancel |
| `latitude_abs` | Absolute latitude | Colony: "polar illumination regime" | Earth's 23.4° obliquity gives a polar night and a polar day, not the permanent grazing light of the lunar pole. High latitude does give low Sun and long shadows part of the year, which is useful for perception tests |
| `quake_count` | Number of catalogued events M ≥ 2.5 within 300 km since 2000 | Calibration: "seismometer"; colony: "stability" | Invalid as used (finding S1). Even with a complete catalog, a count of regional earthquakes is not the ambient noise that matters to a seismometer [R36] |
| `volcano_distance` | Distance to the nearest Holocene vent point | Robotics and calibration: "basalt stand-in"; colony: "possible lava tubes" | Invalid (finding V1) |

## 5. Findings

### Critical: they invalidate a criterion

**V1. Distance to a volcano is neither a rock type nor a lava tube.** Three independent errors. (a) The target is wrong: the lunar south pole is feldspathic highland crust, not mare basalt [R15], and v1's own documentation says so. Rewarding basalt contradicts the stated target. (b) The proxy does not measure basalt: the nearest volcano of Erebus is phonolitic, of Licancabur andesitic, of Changtang trachytic (GVP `Major_Rock_Type`), and all get the same credit as a basalt shield. (c) Proximity to a vent says nothing about lava tubes, which form in specific conditions (long-lived, low-viscosity, tube-fed pahoehoe flows [R20]) and whose presence is established by survey, collapse features or geophysics [R24, R25, R26], not by distance. Known lunar tubes and pits are in the maria [R16, R17, R18, R19], not at the south pole, so the "shelter" criterion of the colony mode does not describe the targeted environment at all.

**S1. The earthquake count is a map of seismometers.** For a complete catalog the Gutenberg-Richter law predicts about 100 times more events above M 2.5 than above M 4.5. Measured on the candidate sites (300 km radius, 2000 to 2026):

| Site | M ≥ 2.5 | M ≥ 4.5 | Ratio |
|---|---|---|---|
| Meteor Crater (Arizona) | 745 | 2 | 372 |
| Craters of the Moon (Idaho) | 4,380 | 28 | 156 |
| Death Valley (California) | 14,082 | 122 | 115 |
| Atacama | 4,921 | 1,452 | 3.4 |
| Tolbachik (Kamchatka) | 2,081 | 829 | 2.5 |
| Holuhraun (Iceland) | 776 | 441 | 1.8 |

Ratios near 100 appear only in the United States, where the network detects small events; elsewhere the catalog misses about 97% of events between M 2.5 and M 4.5. v1 therefore penalized well-instrumented quiet regions and rewarded poorly instrumented active ones. The v1 documentation mentioned the risk in one line; the size of the effect had not been measured.

**C1. Air temperature is taken at the wrong elevation.** NASA POWER returns the value of a reanalysis cell about 50 km wide and its mean elevation. Compared with the Copernicus elevation of each site:

| Site | Site elevation | Cell elevation | v1 temperature | Corrected with 6.5 K/km |
|---|---|---|---|---|
| Erebus | 3,737 m | 229 m | -19.4 °C | -42.2 °C |
| Mauna Kea | 3,730 m | 636 m | 20.9 °C | 0.8 °C |
| Licancabur | 5,691 m | 2,881 m | 13.6 °C | -4.7 °C |
| Tolbachik | 3,454 m | 992 m | -5.5 °C | -21.5 °C |
| McMurdo Dry Valleys | 141 m | 1,139 m | -27.2 °C | -20.7 °C |
| Death Valley (Badwater) | -86 m | 846 m | 19.1 °C | 25.2 °C |

The corrected values are consistent with what is known of these places (a few degrees above freezing at the summit of Mauna Kea, about -20 °C on the floor of Wright Valley, about 25 °C at Badwater). Temperature criteria carry 2 to 4 weight points in every mode.

### Major: they bias the ranking or its interpretation

**T2. Roughness measures tilt.** See section 4. Slope and "roughness" together carry 5 of the 10 weight points of the robotics mode while measuring one thing.

**T3. Maximum slope is misused.** See section 4.

**C2. Relative humidity is the wrong measure of dryness.** See section 4.

**C3. Thermal amplitude is confounded with latitude and irrelevant to mobility.** See section 4.

**C4. Annual insolation and latitude do not describe lunar polar lighting.** See section 4.

**M1. Weights and tolerances are not justified, and everything is averaged.** Weights 3, 2 and 1 and tolerances such as 10° or 20 °C are stated without source; v1 called them "orders of magnitude". Because the total is a weighted mean, any failure can be bought back: Erebus (mean slope 21°, 70% of the 1 km window steeper than the 15° limit the project cites for VIPER) scores 55/100 in robotics, and the same 21° slope scores 77/100 as a place to build a base because the site is cold. A criterion that is essential to a mission is diluted, and a criterion that is irrelevant to it (cold for a mobility test) lowers the score of otherwise suitable sites.

**M2. Mission scenarios are not differentiated by what the mission needs.** The three modes share the same kind of criteria with different weights. There is no distinction between a property of the Moon to reproduce, an operational requirement of the vehicle or instrument, and an environmental proxy. The same parameter (`volcano_distance`, `t2m_min`) is reused across modes with a different story each time.

**M3. Missing data is hidden in the total.** A criterion without a value is dropped and the weights renormalized, which is the right default, but nothing tells the user that a total rests on 4 criteria out of 7. Worse, values that exist but do not describe the site (finding C1) are treated as measurements.

**M4. The uncertainty analysis covers the expert choices only.** The 500 perturbations vary weights, tolerances and bounds. Data errors, the choice of the point, the 1 km window and the single year of MODIS are not propagated, so the published rank ranges are too narrow. Example: the 1 km windows adjacent to the Svalbard point have mean slopes that differ by 7.5° (robust spread), yet its v1 rank range ignores it.

**R1. Results are not reproducible.** See the summary table. No data version or method version accompanies a result.

**P1. One point and one window stand for a site.** Sites are tens of km wide (Manicouagan is 70 km across); several coordinates are marked "approximate" or "fixture coordinate" in `data/candidates.json`. The score of a site is the score of one arbitrary kilometre of it.

### Moderate: they limit what can be concluded

**T1. Slope baselines differ** (about 30 m on Earth, 40 m on the Moon), and slope decreases as the baseline grows [R4].

**T4. The lunar reference is the whole polar cap**, including the walls and floors of permanently shadowed craters, not the terrain of candidate landing regions.

**D1. Edited DEM values are taken as measurements.** Salar de Uyuni has slope 0.00° and roughness 0.00 m: the DEM is flattened there. The site is truly very flat, but the zero is an editing artefact.

**D2. MODIS sampling is thin**: 12 composites of a single year, one pixel, valid values only (19 of 37 sites have gaps).

**X1. Whole classes of properties are absent.** Lithology and mineralogy, grain size and regolith mechanics, dust, rock abundance, lighting geometry, subsurface structure, accessibility and logistics. v1's documentation lists most of them as "not yet modelled", which is honest; the consequence is that no score can claim to say whether a site is a good analog of lunar *ground*.

**Va1. The validation is circular and has one negative control.** The expectations were written by the team that tuned the thresholds (the NDVI threshold was changed after looking at the results). v1 says so itself.

### Conceptual

**K1. "Analog" is used in one sense for three different things.** The literature separates analogs by function: a site can reproduce a process, a material, a landscape or an operational constraint, and almost never all of them [R27, R28]. v1 folds everything into one score out of 100, which invites the reading "this site is 92% like the Moon". No such statement is defensible.

**K2. The colony mode has no clear target.** "Conditions that make a lunar site favorable to a base" mixes resources (ice), power (light), construction (slope) and safety (seismicity) with proxies that are all, in practice, "cold and polar". It is closer to "where are existing polar field stations" than to a similarity measure.

## 6. What v1 does well

- The lunar slope reference is computed from primary data with the same code as Earth. This is the scientific core of the project and it is correct: the v2 recomputation reproduces the v1 percentiles exactly.
- Nothing is invented: a missing value stays null and is shown as missing.
- Limits are stated on every site card (gravity, vacuum, radiation, cold).
- A sensitivity analysis exists and is deterministic.
- The validation document reports its own misses and its own circularity.
- The scoring engine is separated from the sources and fully tested (124 tests).

## 7. Regolith and dust: what can and cannot be compared

The request singles out dust and regolith. v1 has no indicator for either. The table states what is known on the lunar side, what could be measured on Earth, and whether a comparison is defensible.

| Property | Moon (source) | Earth data available globally | Status for EarthMoon |
|---|---|---|---|
| Grain size distribution | Well-graded silty sand, median about 40 to 130 µm, roughly 10 to 20% finer than 20 µm (Apollo cores [R9, R10, R39]) | SoilGrids sand / silt / clay fractions at 250 m [R34]: model predictions, poorly constrained in unvegetated terrain | Estimable with large uncertainty; site sampling needed. Not integrated |
| Particle shape, abrasiveness | Angular, glass-welded agglutinates, no weathering rounding [R9, R11] | None from orbit | No data. Only crushed rock, fresh volcanic ash or simulants approach it [R40, R41]. Must not be transposed from terrestrial dust |
| Electrostatic charging | Driven by solar UV and plasma in vacuum [R11] | None | Not reproducible in open air on Earth; chamber tests only |
| Cohesion, friction angle, bearing strength | Cohesion about 0.1 to 1 kPa, friction angle about 30 to 50° [R10, R42] | None globally; needs in-situ geotechnical tests | No data. Under one sixth gravity the same soil behaves differently, so even a perfect material match is not a mobility match |
| Regolith thickness and layering | Metres on maria, about 10 m or more on highlands [R9] | Not comparable (soil and sediment have other origins) | Not applicable |
| Thermal inertia | Very low, highly insulating upper centimetres [R13, R14] | Derivable from day and night thermal imagery; not done | Possible future indicator; the atmosphere dominates on Earth |
| Rock abundance | Diviner rock abundance, LROC boulder counts at the pole [R44] | No global product; high-resolution imagery per site | Needs per-site work |
| Composition | Feldspathic at the south pole, FeO-poor [R15] | EMIT mineral maps between about 52°N and 52°S [R35], ASTER thermal emissivity, global lithological map [R31] | Measurable: highest-priority addition (see roadmap) |

The honest position for now: EarthMoon compares **terrain shape and climate proxies**, not ground material. Every result must say so.

## 8. Limits of this audit

The audit was done by one reviewer (an AI model working with the project owner) from the code, the data and the published literature, in one session. It did not include field data, a second independent reviewer, or domain experts in regolith mechanics, volcanology or mission operations. The points that need such experts are listed in [SCIENTIFIC_LIMITATIONS.md](SCIENTIFIC_LIMITATIONS.md).
