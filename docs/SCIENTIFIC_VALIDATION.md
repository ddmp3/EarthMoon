# Scientific validation: protocol and before / after results

This document defines the evaluation grid, applies it to methodology v1 (before any change) and to methodology v2 (after the corrections), with the same criteria and the same methods. It also reports what changed in the rankings and what got worse.

Reproduce every number:

```bash
python tools/validation/science_grid.py     # counted indicators of the grid, v1 and v2
python tools/validation/ablation.py         # corrections applied one at a time, effect on the rankings
python tools/scoring/score_sites.py         # v2 rankings (Python reference scorer)
python tools/scoring/score_sites.py --v1 data/reference/baseline-v1-values.json   # v1 rankings
python tools/validation/rankings.py --api http://localhost:3001                    # check against the running API
```

## 1. The grid

Each criterion is scored from 0 to 3 with the rubric below. Where a number can be counted from the repository, it is counted by `tools/validation/science_grid.py` and the score follows from it; where a judgement is needed, the rubric says what each level requires so that another reviewer can redo it.

| Level | Meaning |
|---|---|
| 0 | Absent |
| 1 | Present but with errors that change results |
| 2 | Correct for what it covers, with known gaps |
| 3 | Meets the target stated for the criterion |

| # | Criterion | Method of evaluation | Reference level (target, 3) |
|---|---|---|---|
| 1 | Quality and traceability of sources | Share of scenario criteria whose values are frozen in the repository; presence of data and method versions in every result; hashes of inputs | 100% frozen, versions in every result, input hashes stored |
| 2 | Relevance of parameters | Share of scenario criteria that use an indicator the audit found invalid for its use | 0%, and every proxy states what it does not measure |
| 3 | Quality of processing | Number of sites whose values were taken from a source that does not describe them (reanalysis cell more than 300 m off in elevation, used without correction); Earth and Moon terrain computed identically; artefacts flagged | 0 sites; identical processing; artefacts flagged |
| 4 | Validity of calculations | Automated tests; agreement of two independent implementations on the real data set | Every rule tested; exact agreement on every site and mode |
| 5 | Relevance of comparison criteria | Share of each scenario's weight resting on a lunar measurement or a documented mission requirement | ≥ 50% in every scenario |
| 6 | Handling of missing data | Is a missing value distinguished from a zero, excluded rather than scored, reported per site (coverage, bounds), and is a non-representative value treated as missing? | All four |
| 7 | Handling of uncertainty | Share of criteria whose values carry a quantified uncertainty; is data uncertainty propagated to the result? | 100% quantified, propagated, correlations handled |
| 8 | Adaptation to mission scenarios | Hard requirements exist; criteria irrelevant to a mission are absent from its scenario; criteria derive from documented mission requirements | All three |
| 9 | Quality of interpretation | Can a user see why a site ranks where it does, how sure the result is, and what it does not cover? | Explanation, confidence and limits for every site, shown to the user |
| 10 | Reproducibility | Same request, same result on any day; seed fixed; data set rebuildable from versioned inputs | All three |
| 11 | Methodological transparency | Share of scenario criteria that state their role, basis and rationale through the API; methodology document | 100%, and a document describing every formula |
| 12 | External validation | Expectations fixed in advance by people who did not build the model; number of negative controls | Independent expectation list, ≥ 10 negative controls |
| 13 | Coverage of ground material (geology, mineralogy, regolith) | Number of material properties measured on both sides | At least lithology and composition |

Criteria 12 and 13 were added to the eleven requested because the audit found them decisive and neither is addressed by v2: they show what the corrections did not reach.

## 2. Counted indicators

Output of `tools/validation/science_grid.py` (v1: criteria of `MODES_V1`; v2: criteria of `data/reference/scenarios-v2.json`):

| Indicator (number = grid criterion) | Methodology v1 | Methodology v2 |
|---|---|---|
| 1 Criteria whose values are frozen and versioned | 7/22 (32%) | 15/15 (100%) |
| 2 Criteria using an indicator the audit found invalid | 9/22 (41%) | 0/15 (0%) |
| 3 Sites scored with an air temperature taken more than 300 m off their elevation | 12/37 | 0/37 |
| 5 Weight resting on a lunar measurement or a documented mission requirement (mean of the modes) | 28% (robotics 60%, calibration 0%, colony 23%) | 25% (robotics 75%, calibration 0%, colony 0%) |
| 7 Criteria whose values carry a quantified uncertainty | 0/22 (0%) | 10/15 (67%) |
| 8 Hard requirements (criteria that cannot be averaged away) | 0 | 2 |
| 11 Criteria stating their role, basis and rationale in the API | 0/22 (0%) | 15/15 (100%) |

Reading indicator 5 correctly: in v1, 60% of the robotics weight was counted as "lunar measurement" because `roughness` and `slope_max` were compared with LOLA values, but the audit found both misused. The colony share fell from 23% to 0% because v2 labels the slope limit for building as expert judgement (it is not taken from a documented requirement), while v1 counted the slope criterion as measured. On this indicator v2 is not better, it is more honest; the target (≥ 50% in every scenario) is not met.

Tests: v1 had 124 TypeScript and 30 Python tests. v2 has 154 TypeScript and 55 Python tests, including a test that the TypeScript engine and the independent Python scorer give identical totals, requirement outcomes and coverage for all 37 sites in all three modes on the repository data set.

## 3. Grid results

| # | Criterion | v1 (initial) | Evidence for v1 | Target | v2 (final) | Evidence for v2 |
|---|---|---|---|---|---|---|
| 1 | Sources and traceability | 1 | 7/22 criteria frozen; climate, seismicity and volcanoes read live; no version in results | 3 | **3** | All values frozen in `data/dataset-v2.json` with input hashes; LOLA file hash stored; method and data versions in every response |
| 2 | Relevance of parameters | 1 | 9/22 criteria use an invalid indicator (volcano distance, M 2.5 count, relative humidity, tilt "roughness", max slope, insolation) | 3 | **2** | 0/15 invalid; but calibration and colony still rest only on climate proxies |
| 3 | Processing | 1 | 12/37 sites scored with off-elevation temperatures; Earth 30 m geographic grid vs Moon 40 m; DEM artefacts not flagged | 3 | **2** | 0/37; identical 40 m grid on both bodies; flat artefact and seasonal gaps flagged. Remaining: one point per site, one year of MODIS |
| 4 | Validity of calculations | 2 | Rules tested; Python scorer compared on sample data only | 3 | **3** | Every rule tested; exact TypeScript / Python agreement on the real data set |
| 5 | Relevance of comparison criteria | 1 | Weighted mean of cold, dry, calm, volcano proxies; no similarity measure beyond slope | 3 | **2** | Robotics: 75% of weight on lunar distributions and a documented limit. Calibration and colony: 0% (target not met) |
| 6 | Missing data | 1 | Missing excluded and shown per criterion, but no coverage, no bounds, non-representative values used as measurements | 3 | **3** | Coverage, bounds, `unknown` requirements, non-representative values set to missing, never-assessed attributes kept null |
| 7 | Uncertainty | 1 | Expert choices perturbed; data uncertainty ignored | 3 | **2** | 10/15 criteria carry a sigma; data uncertainty propagated by Monte Carlo; total interval and requirement share per site. Remaining: wind, humidity, precipitation, MODIS have no sigma; correlations ignored |
| 8 | Mission adaptation | 1 | Same proxies in every mode with different weights; no hard requirement | 3 | **2** | Hard requirements (traversable share, buildable slope); irrelevant criteria removed per scenario; roles explicit. Remaining: only one requirement comes from a mission document |
| 9 | Interpretation | 2 | Site cards show limits and sources; rank range shown | 3 | **2** | API returns explanation, confidence, coverage, expert share. Not yet shown in the interface (out of scope of this phase) |
| 10 | Reproducibility | 1 | Live sources: totals change from day to day | 3 | **3** | Frozen data, fixed seed, rebuild scripts, cross-implementation test |
| 11 | Transparency | 2 | Good documentation; no per-criterion basis in the API | 3 | **3** | Role, basis and rationale for 15/15 criteria in the API; formulas in `SCIENTIFIC_METHODOLOGY.md` |
| 12 | External validation | 1 | Team-written expectations, one negative control | 3 | **1** | Unchanged |
| 13 | Ground material | 0 | None | 2 | **0** | Unchanged (lithology and composition sources identified, not integrated) |
| | **Total** | **15 / 39** | | | **28 / 39** | |

The scores of the judged criteria were given by the same reviewer who made the corrections, which is a conflict of interest. The counted indicators of section 2 do not depend on that judgement.

## 4. Effect of each correction on the rankings

Output of `tools/validation/ablation.py`. Each step adds one correction to the previous one. "Expectations met" uses the team's `known_for` list (data/candidates.json), which is not independent (criterion 12).

| Step | Robotics: rank correlation with v1 / v1 top 10 kept / expectations | Calibration | Colony |
|---|---|---|---|
| S0 v1 | 1.00 / 10 / 5 of 6 | 1.00 / 10 / 2 of 3 | 1.00 / 10 / 2 of 2 |
| S1 corrected data (temperature at site elevation, 40 m grid, non-representative climate values missing) | 0.98 / 9 / 4 of 6 | 0.94 / 9 / 2 of 3 | 0.96 / 10 / 2 of 2 |
| S2 earthquakes M ≥ 4.5 | 0.98 / 9 / 4 of 6 | 0.78 / 5 / 1 of 3 | 0.94 / 10 / 2 of 2 |
| S3 volcano distance removed | 0.95 / 9 / 5 of 6 | 0.78 / 6 / 0 of 3 | 0.93 / 9 / 2 of 2 |
| S4 specific humidity | 0.95 / 9 / 5 of 6 | 0.63 / 5 / 1 of 3 | 0.93 / 9 / 2 of 2 |
| S5 detrended roughness, lunar percentiles, traversable share as requirement | 0.87 / 8 / 5 of 6 | 0.63 / 5 / 1 of 3 | 0.93 / 9 / 2 of 2 |
| S6 methodology v2 | 0.80 / 6 / 5 of 6 | 0.61 / 5 / 1 of 3 | 0.92 / 7 / 2 of 2 |

What it shows:

- **Calibration changes most.** The earthquake correction alone moves half of its top 10: sites in the western United States (Meteor Crater, Black Point, Craters of the Moon) lose their artificial penalty, sites in poorly instrumented active regions lose their artificial advantage. Specific humidity then promotes cold dry polar sites that relative humidity had ranked as humid.
- **Robotics changes least in its expectations, but its top changes.** Fresh lava fields and impact structures in arid regions (Erta Ale, Aorounga, Tenoumer) reach the top because their 1 km slope and detrended relief fall in the lunar range; Craters of the Moon falls from 1st to 5th. Tolbachik and Licancabur fail the traversable-ground requirement.
- **Colony is stable** (correlation 0.92): it was and remains a ranking of cold, high-latitude, flat, quiet places. Ten sites now fail the buildable-slope requirement instead of scoring up to 77.

## 5. Validation against known analogs

Report of `tools/validation/rankings.py` on v2 (full report in [validation.md](validation.md)):

| | v1 | v2 |
|---|---|---|
| Expectations met (top half of the mode) | 9 of 11 (82%) | 8 of 11 (73%) |
| Pass threshold of 75% | met | **not met** |
| Negative control excluded in every mode | yes | yes |
| Probability that a random ranking does as well | 2.6% | 10.0% |
| Mean share of Monte Carlo scenarios in which an expectation holds | 82% | 73% |

The v2 misses:

- **Holuhraun in robotics (#32, was #19).** At 1 km the lava field is flatter (mean slope 1.9°) and smoother (detrended relief 2.8 m) than 95% of south polar windows. v1 also missed it. NASA used it for rover navigation on a lava surface whose difficulty lies below the DEM scale. The data say it is not a 1 km terrain analog of the south pole; they say nothing of its metre-scale roughness.
- **Atacama in calibration (#24, was #12).** The air is dry and calm, but the site lies on a subduction margin (1,452 earthquakes M ≥ 4.5 within 300 km) and its mean temperature at the site elevation is 12.7 °C, so the seismometer, drill (frozen ground) and cold-soak criteria score 0. v1 had hidden the seismicity because the M ≥ 2.5 count is incomplete in South America. Atacama's real calibration use (ARADS) is for Mars-like dry soils, not lunar conditions.
- **Svalbard in calibration (#20, was #31: better, still missed).** Specific humidity is low (2.3 g/kg) but the region has 106 earthquakes M ≥ 4.5 and moderate wind.

The fall from 9 to 8 is not a reason to retune: the expectations were written by the team that built v1 and are not an independent benchmark (criterion 12). Tuning v2 to them would repeat the circularity. Each miss above is explained by a measurement, not by a threshold choice.

## 6. Confidence of the v2 assessments

| Scenario | High | Medium | Low | Median rank range (10th to 90th percentile) | Median width of the total's interval |
|---|---|---|---|---|---|
| Robotics | 1 | 18 | 17 | 12 places | 30 points |
| Calibration | 25 | 8 | 3 | 7 places | 14 points |
| Colony | 5 | 28 | 3 | 5 places | 19 points |

In robotics, half of the sites have low confidence: moving the site point by 1 km changes the 1 km terrain statistics a lot. The top of the robotics ranking (Erta Ale, Aorounga, Peary Land at 100, 100 and 91) has rank ranges of 1 to 14, 1 to 11 and 1 to 12: these sites are candidates worth a closer look, not a reliable order. v1 hid this by ignoring data uncertainty.

## 7. Summary of the change

**Corrected**: findings V1 (volcano distance), S1 (earthquake catalog), C1 (temperature elevation), C2 (relative humidity), T1 (slope baseline), T2 (roughness), T3 (max slope), C4 (insolation), M3 (missing data), M4 (data uncertainty), R1 (reproducibility), D1 (flat DEM artefacts flagged). Partly: M1 (equal weights and hard requirements; weights still not elicited), M2 (roles and requirements; only one requirement from a mission document).

**New scientific functions**: identical Earth and Moon terrain processing on a 40 m grid with a full lunar distribution; detrended roughness and traversable share; lava tube evidence levels separating demonstration from predisposition; frozen versioned data set with per-value uncertainty and quality flags; hard requirements; coverage and score bounds; Monte Carlo on data and expert choices; confidence label; per-criterion explanation; method and data versions in results; independent scorer checked on every site.

**Regressions and losses** (stated, not hidden):

1. Expectations met fall from 9 to 8 of 11; the validation threshold is no longer met.
2. Six sites lose their wind, humidity and precipitation values (reanalysis cell more than 1 km off); their calibration coverage drops to 0.6 to 0.9.
3. The data no longer refresh by themselves; they must be rebuilt explicitly.
4. The interface shows the new parameter identifiers (`roughness_detrended`, `traversable_15`, `specific_humidity`, `quake_m45_count`) without labels or help text, because the interface was out of scope. It still works.
5. Requests built by hand for v1 that rely on removed criteria still work (deprecated parameters are still served), but the three predefined modes give different rankings.

**Remaining limits**: criteria 12 and 13 unchanged; calibration and colony rest on judgement only; terrain at 40 m says nothing of rover-scale ground. Details in [SCIENTIFIC_LIMITATIONS.md](SCIENTIFIC_LIMITATIONS.md).
