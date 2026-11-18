# Spatial and statistical sampling (T22)

Experiment: `tools/research/sampling.py` (8 tests); output: `data/research/sampling-t22.json`. Run on 18 November 2026 in Docker, 86 s (10 tiles cached, 3 downloaded). Pilot tiles are for engineering only: no similarity threshold is tuned on them.

## Pilot tiles

- **10 random tiles:** Copernicus GLO-30 land tiles drawn with seed 20261117, area-weighted.
- **3 contrasting tiles:** the tiles holding the T21 random windows nearest the 10th, 50th and 95th percentiles of `slope_mean`.
- Each tile is reprojected to a local Lambert equal-area grid at 30, 40 and 90 m. Sea pixels (exactly 0 m) are missing, not flat land.

## Decisions

**1. Compare at the same pixel scale, never across scales.**
- The same 1 km windows at 90 m instead of 30 m keep their rank order: Spearman 0.87 to 0.99.
- Their values do not: the median slope ratio ranges from **0.47 to 0.96** with the terrain. No single correction factor exists.
- So Earth is resampled to the pixel scale of the planetary product it is compared with: 40 m for LDEM_85S_40M, about 60 m for SLDEM2015, about 115 m or 460 m for MOLA grids, and 1 to 2 m for HiRISE (only where national lidar exists on Earth).

**2. Spatial index.**
- **Processing unit:** the Copernicus 1° tile in a local Lambert azimuthal equal-area projection. The bucket listing gives **26,450 tiles**.
- **Statistics cell:** 5 km squares of that projection. They are equal-area, so cell counts can be compared across latitudes.
- **H3 (v4.1.2, Apache 2.0) is for display and aggregation only.** Its cells are not equal-area: at resolution 7 they range from 3.19 to 6.23 km² (a ratio of 1.95, measured on 5,000 random cells). Any count over H3 cells is area-weighted.

**3. Statistics per cell.**
- 1 km windows, kept when at least 90% of their pixels are valid. This is the v2 rule.
- Per cell: n valid windows, valid fraction, median, interquartile range, p5 and p95.
- A cell is **partial** (hatched in pastel) below 50% valid windows, and **missing** with none.
- A cell is never one value without its spread.

**4. Two-stage search.**
- **Stage 1 (screening):** 90 m, 990 m windows. A 5 km cell passes if one of its windows is inside the target interval widened by 2°.
- **Stage 2 (refinement):** 40 m, 1 km windows, only in the cells that passed.
- **Miss rate measured on the 13 pilot tiles**, with the lunar `slope_mean` interquartile range (5.2 to 12.9°) as the engineering target:

| Stage 1 rule | Fine matches missed | Cells passing |
|---|---|---|
| Exact interval | 1,118 of 20,490 (5.5%) | 37% |
| Widened by 1° | 311 (1.5%) | 42% |
| **Widened by 2° (chosen)** | **34 (0.17%)** | 48% |
| Lower bound × 0.75 | 152 (0.7%) | 43% |
| Lower bound × 0.5 | 17 (0.08%) | 52% |

  The ×0.5 rule misses fewer matches but keeps more cells. 2° is chosen as the simpler rule at a similar recall; the choice is re-measured for each new target in T43.
- Stage 1 used GLO-30 resampled to 90 m. The **GLO-90 product itself** must be checked against it in T40.

**5. Effective resolution, first look (finding L3).**
- **Method:** on 5 km blocks at 40 m, compare the power at 160 m wavelength with the power at 2 km.
- **Moon:** 40 random blocks of LDEM_85S_40M. **Earth:** 43 blocks from the pilot tiles.
- **At matched mean slope, the Moon has about 5 times less short-wave relief:**

| Mean slope of the block | Moon | Earth |
|---|---|---|
| 3 to 8° | 2.4e-5 (14 blocks) | 1.3e-4 (8 blocks) |
| above 8° | 4.0e-6 (26 blocks) | 2.1e-5 (11 blocks) |

- This is consistent with grid interpolation between laser tracks, and with the detrended roughness finding of T21. Real lunar smoothness at 160 m is not excluded.
- The T41 count-map test separates the two. Until then, Earth terrain is not sharpened or smoothed to match: the samples are small.

## Scale of each kept parameter

| Parameter | Native or effective resolution | Compared at | Why |
|---|---|---|---|
| `slope_mean` | LOLA 40 m (effective coarser, L3); SLDEM 60 m; MOLA 115 to 460 m; HiRISE 1 to 2 m | The planetary pixel, 1 km windows (rover scale for HiRISE) | Decision 1 |
| `lithology_class` | GLiM 0.5° grid; Macrostrat map scale | Map unit, reported per 5 km cell as a class fraction | Never finer than the map |
| `mineral_class` | EMIT 60 m (52°N to 52°S) | 60 m pixels, as presence per cell | Interpretation, presence only |
| `lst_amplitude`, `thermal_inertia` | MODIS 1 km | 1 km, multi-year statistics up to 1 December 2026 | Terra ends then |
| `ground_ice` | 1 km (Earth model), 3 km (SWIM) | Class per 5 km cell | Model and interpretation |
| `specific_humidity`, `precipitation` | ERA5-Land 9 km | 9 km, flagged as coarser than the cell | Model; cannot support site-scale discovery (L5) |
| `aerosol_optical_depth` | 1 km daily | 1 km, multi-year statistics | — |
| `wind_speed` | ERA5 0.25° | 0.25°, context for Mars only | Model |

## Compute budget (measured on the pilots, then extrapolated)

| Item | Measured | Whole Earth (26,450 tiles) |
|---|---|---|
| GLO-30 tile size | 36.4 MB on average (13 tiles) | about 0.96 TB, so **stream it, do not store it** |
| GLO-30 download | 2.9 to 7.7 s per tile (3 fresh downloads) | about 21 to 57 h |
| GLO-90 tile size | 4.6 to 5.7 MB (3 tiles) | about 0.14 TB, about 5 to 8 h of download |
| Reprojection and windows, 40 m | about 0.8 s per tile | about 6 h of CPU |
| Reprojection and windows, 90 m | about 0.4 s per tile | about 3 h of CPU |

- About half the cells pass stage 1, spread over most tiles, so stage 2 should read only those cells through COG range requests. Its time is **not measured yet** (T40).
- The GLO-90 tile count was not listed; it is assumed close to GLO-30 and is to be checked in T40.
- **Kept output:** cell statistics only, a few gigabytes at most. Raw tiles are not kept.
