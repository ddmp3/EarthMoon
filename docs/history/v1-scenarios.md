# Modes and parameters (methodology v1, superseded)

> **Superseded on 17 November 2026.** This page describes methodology v1. The API now applies methodology v2: see [SCIENTIFIC_METHODOLOGY.md](../METHOD.md) for the criteria, formulas and data, and [SCIENTIFIC_AUDIT.md](../wiki/v2/SCIENTIFIC_AUDIT.md) for why v1 was changed (volcano distance, earthquake catalog, temperature elevation, roughness, relative humidity, insolation). The v1 criteria are kept in `tools/scoring/score_sites.py` (`MODES_V1`) to reproduce the baseline.

Intervals, tolerances and weights are orders of magnitude, each tied to a source. These were the v1 values.

**All temperature criteria are proxies.** No Earth site approaches the cold of permanently shadowed lunar regions (29 to 50 K) or the lunar day-night swing (about 300 K at low latitude). The lunar south pole is highland crust (anorthosite), not mare basalt (Moriarty and Petro, EPSC2022-295); Earth basalt is only a stand-in for regolith and rock mechanics.

## Parameter catalog

Only parameters our sources provide exist in the app. Modes 1 to 3 preselect some; mode 4 offers all.

| ID | Parameter | Unit | Earth source | Lunar equivalent |
|---|---|---|---|---|
| `slope_mean`, `slope_max` | mean / max slope (1 km window) | ° | Copernicus DEM | LRO LOLA |
| `roughness` | std. deviation of elevation (1 km window) | m | Copernicus DEM | LRO LOLA |
| `elevation` | elevation | m | Copernicus DEM | — |
| `ndvi` | vegetation index | — | MODIS MOD13A1 | none |
| `lst_day`, `lst_night`, `lst_amplitude` | surface temperature day / night / swing | °C | MODIS MOD11A2 | Diviner |
| `t2m_mean`, `t2m_min`, `t2m_max` | air temperature (climatology) | °C | NASA POWER | — (cold proxy) |
| `wind`, `humidity`, `precipitation` | wind at 2 m, relative humidity, precipitation | m/s, %, mm/day | NASA POWER | 0 (no atmosphere) |
| `solar` | solar irradiance | kWh/m²/day | NASA POWER | near-continuous light on some polar ridges |
| `latitude_abs` | absolute latitude | ° | coordinates | polar illumination regime |
| `quake_count` | M ≥ 2.5 earthquakes within 300 km since 2000 | count | USGS ComCat | weak moonquakes |
| `volcano_distance` | distance to nearest Holocene volcano | km | Smithsonian GVP | none (basalt as a stand-in) |

## Scoring

- Each criterion has a target interval `[min, max]`, a tolerance `t` and a weight `w`.
- Criterion score: 1 inside the interval, linear decrease to 0 at distance `t`.
- Site score: `Σ(w × score) / Σ(w)`, out of 100. Criteria with no value are excluded from the total.
- Verdicts: score ≥ 0.7 matches, 0.4 to 0.7 partly matches, below 0.4 does not match.
- **Common vegetation filter:** the total is multiplied by a factor that is 1 up to `ndvi` 0.2, decreases linearly to 0 at `ndvi` 0.6 (dense vegetation by the usual remote-sensing convention), and excludes the site (score 0, ranked last) at 0.6 and above. It used to be a hard cut at 0.2; a single-point NDVI can misjudge a large site (Manicouagan is a ring lake in a forest), so the filter now degrades the score instead of dropping the site. The 0.2 threshold was raised from 0.1 to 0.2 after measuring 2024 MODIS NDVI on all 37 sites: at 0.1 it excluded bare deserts (Namib 0.116, Harrat Khaybar 0.109) and two NASA test sites (Black Point 0.151, Meteor Crater 0.157). At 0.2 it would still have excluded the Amazon (0.867), Manicouagan (0.551), Wolfe Creek (0.325), Popigai (0.241) and Gosses Bluff (0.240); with the graded filter their factors are 0 (Amazon), 0.12, 0.69, 0.90 and 0.90. Reference: NASA Earth Observatory, *Measuring Vegetation (NDVI & EVI)*.

## Mode 1 — Robotics validation (mobility)

Where to test a rover's mobility on Earth before sending it to a lunar site.

| Parameter | Target | Tolerance | Weight | Justification |
|---|---|---|---|---|
| `slope_mean` | 5 to 13° | 10° | 3 | Interquartile range measured at the lunar south pole (LRO LOLA LDEM_85S_40M, 71,731 windows of 1 km south of 85°S, same computation as on Earth: `tools/precompute/lunar_reference.py`). A 3 to 10° proposal based on the Apollo 15 and 16 traverses (mean 4.5 to 5.6°) was not kept for the south pole |
| `slope_max` | 15 to 30° | 10° | 1 | Rover limits: VIPER 15° (25 to 30° if needed), Apollo LRV 25°, NASA LTV requirement 20° |
| `roughness` | 22 to 65 m | 30 m | 2 | Interquartile range of 1 km elevation std. deviation at the lunar south pole (LOLA) |
| `precipitation` | ≤ 1 mm/day | 1 | 1 | Dry, loose ground, close to regolith (logic only) |
| `t2m_min` | ≤ −20 °C | 20 °C | 1 | Cold-soak proxy for hardware |
| `lst_amplitude` | ≥ 20 °C | 15 °C | 1 | Thermal cycling proxy (the real lunar swing is about 300 K) |
| `volcano_distance` | ≤ 50 km | 100 km | 1 | Basalt as an Earth stand-in for regolith and rock mechanics |

## Mode 2 — Instrument calibration

Where to calibrate instruments (drill, wind, gas, seismometer, thermal) in near-lunar conditions. Users can filter by instrument.

| Instrument | Parameter | Target | Tolerance | Weight | Justification |
|---|---|---|---|---|---|
| Drill | `t2m_mean` | ≤ 0 °C | 10 °C | 2 | Frozen ground, proxy for icy regolith |
| Drill | `volcano_distance` | ≤ 50 km | 100 km | 1 | Basalt stand-in |
| Wind | `wind` | ≤ 3 m/s | 3 m/s | 2 | Calm baseline (no wind on the Moon) |
| Gas | `humidity` | ≤ 40 % | 30 % | 2 | Dry-atmosphere proxy |
| Gas | `precipitation` | ≤ 0.5 mm/day | 1 | 1 | Dry environment |
| Seismometer | `quake_count` | ≤ 5 | 20 | 3 | Low seismic noise, like the Moon. A low USGS count can also mean few stations, not quiet ground |
| Thermal | `lst_amplitude` | ≥ 25 °C | 15 °C | 2 | Large day-night swing |
| Thermal | `t2m_min` | ≤ −30 °C | 20 °C | 1 | Extreme cold proxy |

## Mode 3 — Self-sufficient colony

Earth sites that reproduce the conditions that make a lunar site favorable to a self-sufficient base.

| Need | Parameter | Target | Tolerance | Weight | Justification |
|---|---|---|---|---|---|
| Water | `t2m_mean` | ≤ −5 °C | 10 °C | 3 | Permafrost, proxy for ice in shadowed regions (LEND) |
| Energy | `latitude_abs` | ≥ 65° | 15° | 2 | Polar illumination regime |
| Energy | `solar` | ≥ 2 kWh/m²/day | 2 | 1 | Minimum solar potential |
| Construction | `slope_mean` | ≤ 5° | 5° | 3 | Flat, buildable ground |
| Shelter | `volcano_distance` | ≤ 100 km | 200 km | 1 | Possible lava tubes |
| Stability | `quake_count` | ≤ 10 | 30 | 2 | Stable ground for structures |
| Survival | `t2m_min` | ≤ −30 °C | 20 °C | 1 | Life-support stress test |

## Mode 4 — Free criteria

The user picks parameters from the catalog and sets the interval, tolerance and weight of each. The vegetation filter stays on by default and can be turned off.

## Candidate sites

37 sites in `data/candidates.json`: 9 known analogs (Atacama, McMurdo Dry Valleys, Haughton, Mauna Kea, Svalbard, Holuhraun, Meteor Crater, Black Point, Death Valley), 1 negative control (Amazon) and 27 candidate sites (hypotheses to validate) in cold, arid or volcanic regions (Canadian Arctic, Greenland, Tibetan plateau, Altiplano, Gobi, Namib, volcanic fields…).

## Evidence

- **Rover limits:** NASA SP-4214 ch. 13 (Apollo LRV); NASA NTRS 20240013903 and 20250004148 (VIPER); NASA LTV solicitation (secondary summary). Apollo 15/16 as-traversed slopes: NTRS 20250011301.
- **Lunar temperatures:** Paige et al. 2010, Science 330:479 (cold traps as low as 29 K); Diviner overview, EPSC2013-386 (about 400 K at the equator at noon, under 100 K at night).
- **Seismicity:** Nakamura, NTRS 19930008250 (28 shallow moonquakes in 8 years); Latham et al., NTRS 19780005006.
- **South pole geology:** Moriarty and Petro, EPSC2022-295.
- **Open points:** no Pragyan slope specification found; PRIME-1 demonstrated drill motion but no ice drilling result; the NASA LTV figures come from a secondary summary of the original solicitation.
