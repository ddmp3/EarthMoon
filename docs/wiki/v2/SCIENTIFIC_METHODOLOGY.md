# Scientific methodology

Version 2.0.0 of the method, on version 2.0.0 of the data set. Both versions are returned with every API result (`methodology`), so any score can be traced to the code and data that produced it.

The question the method answers:

> On traceable data, with a reproducible method and criteria chosen for a stated exploration objective, how far is an Earth site a relevant analog of a lunar environment, and how much confidence does the assessment deserve?

What the method does not claim: that any Earth site is equivalent to the Moon, or that a score is a probability. Three words are kept apart throughout: **similarity** (a measured quantity falls in the measured lunar range), **representativeness** (the site can stand for a lunar condition in a test, through a proxy) and **equivalence** (never claimed).

Section 1 recalls methodology v1 in one page; the audit of it is in [SCIENTIFIC_AUDIT.md](SCIENTIFIC_AUDIT.md). Sections 2 to 8 describe v2 as implemented. Section 9 describes the target that v2 does not reach yet. References `[Rn]` are in [SCIENTIFIC_REFERENCES.md](../../REFERENCES.md).

## 1. Methodology v1 in brief

Eighteen parameters per site, read live (NASA POWER, USGS, Smithsonian GVP) or precomputed (Copernicus DEM, MODIS). Each mode lists criteria with a target interval, one tolerance and a weight; the criterion score is 1 inside the interval and falls linearly to 0 at the tolerance; the site total is the weighted mean out of 100, multiplied by a vegetation factor. Weights, tolerances and bounds are perturbed 500 times to give a rank range. Criteria of v1 are kept in `tools/scoring/score_sites.py` (`MODES_V1`) and the values it scored in `data/reference/baseline-v1-values.json`, so the v1 rankings can be reproduced.

## 2. Principles of v2

1. **A criterion states what it is.** Each criterion has a `role`: *similarity* to a measured lunar distribution, operational *requirement* of the vehicle, instrument or mission, or Earth *proxy* of a lunar condition that cannot be reproduced. It has a `basis`: *lunar measurement*, documented *mission requirement*, or *expert judgement*. It has a written `rationale`. All three are served by the API.
2. **No number is chosen by hand when a measurement exists.** Similarity intervals are the interquartile range of the lunar distribution and their tolerances reach its 5th and 95th percentiles.
3. **Where no measurement exists, the method says so.** Thresholds that rest on judgement are labelled as such, weights are equal, and the share of each result that rests on judgement is reported (`expertShare`).
4. **An essential criterion is not averaged away.** A hard requirement that fails makes the site fail the scenario.
5. **A criterion irrelevant to a mission is not in its scenario.**
6. **A missing value is not a value.** It counts neither for nor against the site, and the result shows how much is missing.
7. **Score and confidence are two different outputs.**
8. **Everything is reproducible.** Data are frozen and versioned; the random seed is fixed; an independent Python scorer must give the same totals as the API.

## 3. Data set

The API scores `data/dataset-v2.json`, built by `tools/precompute/build_dataset.py` from three versioned inputs whose SHA-256 hashes are stored in the file. Nothing is read from the network when a score is computed.

| Input | Built by | Content |
|---|---|---|
| `data/candidates-precomputed.json` | `site_terrain.py`, `modis_values.py` | Terrain on the lunar grid, MODIS values |
| `data/snapshots/live-sources.json` | `live_snapshot.py` | NASA POWER climatology with the cell elevation, USGS counts with a fixed end date (2026-11-01), nearest GVP volcano with its rock type |
| `data/evidence/lava-tubes.json` | Hand-curated, each entry with a reference | Demonstrated or probable lava tubes |

Each value is stored as `{ value, sigma, sigma_basis, flags }`. `value` is `null` when there is no measurement. `sigma` is the 1-sigma uncertainty when it has been quantified, otherwise `null`. Flags describe quality problems.

To refresh the data: rerun the three tools, rebuild the data set, bump its version, rerun `tools/scoring/score_sites.py --write-expected` and the tests.

## 4. Indicators

For each indicator used by a scenario: definition, source, unit, computation, normalization, relevance, uncertainty, limits.

### 4.1 Terrain (Earth and Moon computed identically)

Common processing (`tools/precompute/terrain_metrics.py`): elevation on a metric grid of 40 m pixels; slope by central differences; statistics over non-overlapping windows of 25 x 25 pixels (1 km). Earth: Copernicus DEM GLO-30 resampled bilinearly to a local azimuthal equidistant grid centred on the site (`site_terrain.py`). Moon: LRO LOLA LDEM_85S_40M, all 71,731 windows entirely south of 85°S (`lunar_reference_v2.py`). The Earth value is the window centred on the site; its uncertainty is the robust spread (1.4826 x median absolute deviation) of the 3 x 3 windows around it, that is, how much the value changes if the site coordinate is off by 1 km.

| Indicator | Definition | Unit | Lunar distribution (p5 / p25 / p50 / p75 / p95) | Why it matters | Limits |
|---|---|---|---|---|---|
| `slope_mean` | Mean slope of the window at 40 m baseline | ° | 2.95 / 5.23 / 8.31 / 12.89 / 20.89 | Bulk steepness of the terrain a traverse crosses [R4] | 40 m baseline underestimates the 1 to 5 m slopes a rover meets; whole polar cap, shadowed craters included |
| `roughness_detrended` | Standard deviation of elevation after removing the least-squares plane of the window | m | 3.33 / 5.12 / 7.22 / 10.52 / 18.57 | Relief that is not explained by the mean tilt: craters, ridges, blocks at 40 m to 1 km scale [R5] | Same scale limit; says nothing of rocks |
| `traversable_15` (also `_20`, `_25`) | Share of the window area with slope ≤ 15° (20°, 25°) | 0 to 1 | 0.01 / 0.76 / 0.98 / 1 / 1 | Share of the ground within a rover's documented climbing limit | Slope is not traversability: slip depends on soil and gravity [R43] |
| `slope_p95` | 95th percentile of slope in the window | ° | 6.05 / 9.42 / 13.18 / 17.89 / 25.61 | Robust replacement of the maximum slope | Available in free criteria; not used by a predefined scenario |

`roughness` (v1, tilt included) and `slope_max` are still computed and served for continuity, and are not used by any predefined scenario. Check of the processing: the v2 code reproduces the v1 lunar percentiles of `slope_mean`, `slope_max` and `roughness` to the second decimal.

Normalization of similarity criteria: score 1 between the lunar 25th and 75th percentiles, falling linearly to 0 at the 5th percentile below and at the 95th percentile above. Half of the lunar windows therefore score 1 and 90% score above 0. Evidence level: the lunar distributions are established measurements; reading them as "similar terrain" at 1 km scale is strongly documented; extending the conclusion to rover-scale terrain is not supported.

### 4.2 Climate (NASA POWER, corrected)

| Indicator | Definition | Unit | Computation | Uncertainty | Limits |
|---|---|---|---|---|---|
| `t2m_mean` | Mean annual air temperature at 2 m, 2001 to 2025, at the site elevation | °C | `T2M` of the reanalysis cell, minus 6.5 K per km of elevation difference between site and cell | 1 sigma = sqrt(1.5² + (2 K/km x elevation difference)²): assumed reanalysis error plus the spread of real lapse rates [R38] | The 6.5 K/km standard lapse rate is wrong under inversions, common in polar valleys; the 1.5 K reanalysis error is an assumption |
| `t2m_min` | Lowest monthly `T2M_MIN` of the climatology, same correction | °C | Same | Same | The exact statistic behind POWER's monthly `T2M_MIN` was not confirmed in its documentation |
| `specific_humidity` | Mass of water vapour per mass of air at 2 m (`QV2M`) | g/kg | Annual value of the cell | Not quantified | Left missing when the cell is more than 1 km above or below the site |
| `wind`, `precipitation` | Annual means of the cell | m/s, mm/day | None | Not quantified | Same rule; a 50 km mean is not a site value |

Why the correction: 12 of 37 sites are more than 300 m from their cell elevation (audit, finding C1). Why no correction for the other variables: there is no accepted simple correction for humidity, wind or precipitation across a relief, so a value that does not describe the site is declared missing instead of being adjusted by a guess. Six sites are affected (Erebus, Mauna Kea, Licancabur, Tolbachik, Payún Matrú, Dallol).

### 4.3 Seismicity

`quake_m45_count`: earthquakes of magnitude 4.5 or more within 300 km between 2000-01-01 and 2026-11-01 (USGS ComCat). Magnitude 4.5 is the level from which USGS reports events worldwide; the audit shows that the M 2.5 count used by v1 depends on network density (finding S1). Uncertainty: Poisson counting error, sqrt(N), at least 1. Limits: it describes regional tectonic activity, not the ambient noise that limits a seismometer [R36]; the 300 km radius and the period are conventions.

### 4.4 Surface temperature and vegetation (MODIS)

`lst_amplitude` and `ndvi` are unchanged from v1 (12 composites of 2024, one pixel). Their uncertainty is not quantified; sites with missing composites carry the flag `seasonal_gaps` (19 of 37 sites). NDVI stays a common filter, not a similarity criterion: no penalty up to 0.2, linear down to exclusion at 0.6.

### 4.5 Lava tube evidence

`lava_tube_evidence` separates three situations that v1 merged into "close to a volcano":

| Level | Meaning | How it is assigned |
|---|---|---|
| 3 | Demonstrated: a tube has been entered, surveyed or mapped | By hand, with a published reference (`data/evidence/lava-tubes.json`) |
| 2 | Probable: aligned collapse pits, skylights or collapsed channels are reported without a survey | By hand, with a published reference |
| 1 | Predisposition only: a Holocene volcano of basaltic composition lies within 30 km | Automatically from the Smithsonian GVP rock type and distance |
| empty | Not assessed, or no evidence either way | Default |

There is no level 0: the project has no data that could show the absence of a cave, and absence of evidence is not recorded as absence. Currently 2 sites are at level 3 (Craters of the Moon [R29], Harrat Khaybar [R53]), 6 at level 1, 29 not assessed. The indicator is available in free criteria. It is deliberately **not** used in the three predefined scenarios, which target the lunar south pole: known lunar pits and tubes are in the maria [R17, R18, R19]. The 30 km radius and the list of "basaltic" rock types are expert choices.

### 4.6 Deprecated indicators

Still served so that existing requests keep working, labelled deprecated in the parameter catalog, and used by no predefined scenario: `volcano_distance`, `quake_count` (M ≥ 2.5), `humidity` (relative), `roughness` (tilt included), `slope_max`, `solar`. Reasons: audit findings V1, S1, C2, T2, T3, C4.

## 5. Scenarios

A scenario is a set of criteria for one objective and one target environment. The three predefined scenarios target the lunar south polar region. Definitions: `apps/api/src/scoring/modes.ts`, mirrored in `data/reference/scenarios-v2.json` for the Python scorer (a test keeps them identical).

### 5.1 Rover mobility test ("robotics")

Objective: find ground whose shape at 40 m to 1 km scale resembles south polar terrain and where a rover with a documented climbing limit can drive.

| Criterion | Role | Basis | Interval (score 1) | Score 0 at | Weight |
|---|---|---|---|---|---|
| `slope_mean` | Similarity | Lunar measurement | 5.23 to 12.89° | 2.95° and 20.89° | 1 |
| `roughness_detrended` | Similarity | Lunar measurement | 5.12 to 10.52 m | 3.33 m and 18.57 m | 1 |
| `traversable_15` | Requirement (hard) | Mission requirement, thresholds by judgement | ≥ 0.5 | ≤ 0.25 | 1 |
| `precipitation` | Proxy (dry ground) | Expert judgement | ≤ 1 mm/day | 2 mm/day | 1 |

Removed from v1 and why: `slope_max` and `roughness` (findings T2, T3), `volcano_distance` (V1), `t2m_min` and `lst_amplitude` (cold and thermal cycling do not condition a mobility test; hardware thermal qualification is done in chambers). Not covered: soil mechanics, grain size, rock abundance, lighting.

### 5.2 Instrument tests ("calibration")

Each instrument counts for 1 in total; the interface can filter by instrument.

| Instrument | Criterion | Role | Basis | Interval | Score 0 at | Weight |
|---|---|---|---|---|---|---|
| Drill | `t2m_mean` | Proxy (frozen ground) | Expert judgement, grounded in permafrost climatology [R32] | ≤ -6 °C | 0 °C | 1 |
| Wind | `wind` | Requirement (low disturbance) | Expert judgement | ≤ 3 m/s | 6 m/s | 1 |
| Gas | `specific_humidity` | Proxy (dry air) | Expert judgement | ≤ 3 g/kg | 8 g/kg | 0.5 |
| Gas | `precipitation` | Proxy (dry environment) | Expert judgement | ≤ 0.5 mm/day | 1.5 mm/day | 0.5 |
| Seismometer | `quake_m45_count` | Proxy (tectonic quiescence) | Expert judgement | ≤ 5 | 50 | 1 |
| Thermal | `lst_amplitude` | Proxy (thermal cycling) | Expert judgement | ≥ 25 °C | 10 °C | 0.5 |
| Thermal | `t2m_min` | Proxy (cold soak) | Expert judgement | ≤ -30 °C | -10 °C | 0.5 |

Changed from v1: relative humidity replaced by specific humidity (C2); M 2.5 count replaced by M 4.5 (S1); `volcano_distance` removed (V1); frozen-ground threshold moved from "0 °C with a 10 °C tolerance" to the range where permafrost goes from absent to continuous; weights equalized per instrument. Every criterion of this scenario rests on judgement: its results are an ordering of dry, cold, calm, quiet places, not a similarity to the Moon.

### 5.3 Base analog ("colony")

| Need | Criterion | Role | Basis | Interval | Score 0 at | Weight |
|---|---|---|---|---|---|---|
| Water | `t2m_mean` | Proxy (ground ice) | Expert judgement | ≤ -6 °C | 0 °C | 1 |
| Lighting | `latitude_abs` | Proxy (low Sun, long shadows) | Expert judgement | ≥ 65° | 50° | 1 |
| Construction | `slope_mean` | Requirement (hard) | Expert judgement | ≤ 5° | 10° | 1 |
| Stability | `quake_m45_count` | Proxy | Expert judgement | ≤ 5 | 50 | 1 |

Removed from v1 and why: `solar` (C4), `volcano_distance` as "possible lava tubes" (V1: not a feature of the target), `t2m_min` (third criterion asking "is it cold", correlation 0.94 with `t2m_mean`). The scenario remains conceptually weak (audit, finding K2) and all of it rests on judgement.

### 5.4 Free criteria

Any catalog parameter, with `min`, `max`, `tolerance`, optional `toleranceBelow` / `toleranceAbove`, `weight`, and optional `required: true`.

## 6. Scoring

For a criterion with interval `[min, max]` and value `x`:

```
score = 1                                   if min ≤ x ≤ max
score = max(0, 1 - (min - x) / tolBelow)    if x < min
score = max(0, 1 - (x - max) / tolAbove)    if x > max
```

`tolBelow` and `tolAbove` default to `tolerance`. For a site, over the criteria `i` that have a value (set K) among all criteria (set A), with weights `w`:

```
total      = 100 x Σ_K w_i score_i / Σ_K w_i
coverage   = Σ_K w_i / Σ_A w_i
totalMin   = 100 x Σ_K w_i score_i / Σ_A w_i                   (missing criteria scored 0)
totalMax   = 100 x (Σ_K w_i score_i + Σ_{A\K} w_i) / Σ_A w_i   (missing criteria scored 1)
contribution_i = 100 x w_i score_i / Σ_K w_i                   (sums to the total)
```

The total is then multiplied by the vegetation factor. **Requirements**: `failed` if a required criterion scores 0, `unknown` if a required criterion has no value, otherwise `met`. **Order**: sites excluded by vegetation last; before them sites that fail a requirement; the others first; by descending total within each group. A failing site keeps its total and its criteria: nothing is hidden, it is ranked where a site that cannot do the mission belongs.

Why a weighted mean was kept: it is transparent and its weaknesses are known [R51]. Its main weakness, full compensation between criteria, is handled by the hard requirements. Non-compensatory aggregation (geometric mean, outranking) was considered and left for a later step: it changes every score and should be chosen with domain experts.

Why equal weights: no measurement and no documented requirement supports the 3 / 2 / 1 weights of v1. Equal weights are the neutral choice [R51], the Monte Carlo analysis varies them by ±50%, and the choice is listed for expert review.

## 7. Missing data

| Situation | Treatment |
|---|---|
| No measurement exists (no valid MODIS composite, no DEM tile) | `value: null`; criterion `missing`; excluded from the mean; lowers `coverage`; widens `totalRange` |
| A value exists but does not describe the site (reanalysis cell more than 1 km off in elevation) | Same, with the flag `not_representative_elevation` |
| A value was corrected by a model (temperature) | Kept, with the flag `elevation_corrected` and a larger sigma |
| A measured zero (no earthquake M ≥ 4.5) | A value like any other, with its uncertainty |
| A required criterion is missing | `requirements: "unknown"`, confidence `low` |
| An attribute was never assessed (`lava_tube_evidence`) | `null` with the flag `not_assessed`; never 0 |

Geographic bias: the sources that leave gaps do so in specific regions. MODIS NDVI is missing for three polar sites; the reanalysis rule affects high or deep sites. Because a missing criterion is left out rather than scored, such sites are not pushed down; because `coverage` is shown, they are not silently trusted either.

## 8. Uncertainty and confidence

A Monte Carlo simulation (500 runs, fixed seed) propagates two things together [R50, R52]:

1. the expert choices: every weight ±50%, every tolerance ±25%, interval bounds shifted by ±10% of the tolerance (uniform);
2. the data: every value with a quantified sigma is redrawn from a normal distribution, clipped to its physical range.

In each run all sites are scored and ranked. Per site the API returns the 10th and 90th percentiles of its rank and of its total, the share of runs in which it stays in the top half, and the share of runs in which it meets its requirements.

Confidence label, separate from the score:

| Label | Rule |
|---|---|
| low | coverage below 0.6, or a required criterion without data, or a 10th to 90th percentile interval of the total wider than 30 points |
| high | coverage of 0.9 or more and an interval of 15 points or less |
| medium | otherwise |

The four thresholds are presentation choices. What the simulation does not include: values without a quantified sigma (wind, precipitation, humidity, MODIS), correlations between errors, the choice of criteria, the 40 m scale, and the uncertainty of extrapolating from Earth to the Moon. The intervals are therefore lower bounds of the real uncertainty.

What it shows in practice: in the mobility scenario 17 of 36 ranked sites have low confidence and the median rank range is 12 places, because 1 km terrain statistics change a lot from one kilometre to the next. v1 reported much narrower ranges because it ignored the data.

## 9. Explanation of a result

`GET /api/sites/{id}?mode=...` returns an `explanation`: `strengths` (criteria scoring 0.7 or more, by contribution), `weaknesses` (the others, by points lost), `decisive` (failed requirements), `missing`, `flagged` (values with a quality flag) and `expertShare`. Each item carries the role, basis and rationale of its criterion. The explanation only reorders what the assessment contains; it adds no interpretation of its own.

## 10. Target methodology (not implemented)

v2 corrects what could be corrected with the data already in the project. A method that a committee of planetary scientists and mission engineers would accept needs more, in this order.

**Target environments.** One reference profile per lunar environment, each with measured distributions: south polar highlands (done for terrain), permanently shadowed regions, mare plains, mare pits and lava tubes, fresh impact craters. A scenario is the combination of a target environment and a mission.

**Mission profiles.** Criteria derived from documented requirements of the vehicle (climbing limit, ground pressure, obstacle clearance), the instrument (drill depth and material strength, thermal range) and the operation (communication line of sight, lighting, autonomy), with the requirement document cited. Distinct profiles for a science rover, a scouting rover, a cargo vehicle, a drill, a cave explorer and a crewed mission. For a cave explorer: demonstrated cave (level 3) as a hard requirement, skylight or entrance geometry, loss of line of sight, darkness.

**Material properties.** Lithology and mineralogy from imaging spectroscopy and lithological maps compared with lunar composition maps [R15, R31, R35]; grain size from site sampling; no transposition of lunar dust properties to terrestrial dust.

**Site as an area.** A polygon per site and the distribution of each indicator inside it, instead of one point.

**Finer terrain.** 2 to 5 m elevation models on both bodies where they exist (LOLA 5 m landing-site models [R48], LROC stereo models; ArcticDEM, REMA [R58], national lidar), so that slopes are compared at a rover-relevant baseline.

**Weights.** Elicited from mission experts with a documented method, or dropped in favour of requirement-based screening followed by similarity ranking.

**Validation.** An expectation list fixed in advance from the literature by people who did not build the model, with a dozen negative controls.

The steps are planned in [SCIENTIFIC_ROADMAP.md](SCIENTIFIC_ROADMAP.md).
