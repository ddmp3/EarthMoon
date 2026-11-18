# Validation of the rankings

Known analogs should rank well, not in every mode, but in the modes they are actually used for. The expectations are in `data/candidates.json` (`known_for` field); the report below is produced by [`tools/validation/rankings.py`](../../tools/validation/rankings.py) against the running API (methodology v2, frozen data set `data/dataset-v2.json`). The before / after comparison with methodology v1 is in [SCIENTIFIC_VALIDATION.md](v2/SCIENTIFIC_VALIDATION.md).

```bash
docker compose up --build -d
python tools/validation/rankings.py --markdown docs/wiki/rankings.md
```

## Expected ranking

| Known analog | Modes expected in the top half | Real use |
|---|---|---|
| Haughton Crater (Nunavut) | robotics, colony | Haughton-Mars Project: rover and spacewalk tests, inhabited station |
| Atacama Desert | robotics, calibration | NASA rover and drilling tests (ARADS) |
| McMurdo Dry Valleys | calibration, colony | Cold desert: instruments, permafrost and ice |
| Mauna Kea | robotics | PISCES: rover and ISRU tests |
| Svalbard, Bockfjorden | calibration | AMASE: instrument tests |
| Holuhraun (Iceland) | robotics | NASA SAND-E: rover navigation on a lava flow |
| Meteor Crater | robotics | Apollo astronaut field geology training |
| Black Point (Arizona) | robotics | NASA Desert RATS: rover and spacewalk tests |
| Death Valley | none | Mars analog named in the challenge statement |

Other expectations: the negative control (Amazon) is excluded or last in every mode; hot deserts rank low in the colony mode (polar cold). Pass threshold: at least 75% of expectations met, and the negative control always excluded or last.

## Result (17 November 2026, methodology v2)

<!-- rankings:start -->
**Verdict: not met.** Expectations met: 8/11 (73%, threshold 75%). Negative control excluded or last in every mode: yes.


Chance baseline: a random ranking would meet at least 8/11 expectations 10.0% of the time (modes treated as independent: indicative).
Robustness: on average each expectation is still met in 73% of the Monte Carlo scenarios (weights ±50%, tolerances ±25%, bounds ±10%, site values redrawn within their uncertainty).
Fragile expectations (met in fewer than half of the scenarios): atacama in calibration, iceland-holuhraun in robotics, svalbard-bockfjorden in calibration.

| Mode | Sites ranked | Expected analogs in the top half | Negative control | Mean criteria coverage |
|---|---|---|---|---|
| Robotics validation | 36 | 5/6 | excluded or last | 96% |
| Instrument calibration | 36 | 1/3 | excluded or last | 93% |
| Self-sufficient colony | 36 | 2/2 | excluded or last | 100% |

### Robotics validation

| Rank | Site | Role | Score | Rank range (80% of scenarios) | Confidence |
|---|---|---|---|---|---|
| 1 | erta-ale | candidate | 100 | 1-14 | low |
| 2 | aorounga | candidate | 100 | 1-11 | medium |
| 3 | peary-land | candidate | 91 | 1-12 | low |
| 4 | tenoumer | candidate | 88 | 2-16 | low |
| 5 | craters-of-the-moon | candidate | 84 | 3-15 | low |
| 6 | tunnunik | candidate | 83 | 3-18 | low |
| 7 | svalbard-bockfjorden | validation | 80 | 10-31 | low |
| 8 | haughton | validation | 79 | 3-15 | medium |
| 9 | changtang | candidate | 79 | 3-11 | medium |
| 10 | atacama | validation | 75 | 2-12 | low |

Expected in the top half (rank ≤ 18) and present: atacama, black-point, haughton, mauna-kea, meteor-crater.
Expected but lower: iceland-holuhraun (#32).
All known analogs: svalbard-bockfjorden (#7, 80), haughton (#8, 79), atacama (#10, 75), dry-valleys (#11, 75), black-point (#12, 75), meteor-crater (#15, 72), mauna-kea (#16, 71), death-valley (#20, 50), iceland-holuhraun (#32, 25).
Best candidate sites (hypotheses to validate): Erta Ale (Ethiopia) (100), Aorounga Crater (Chad) (100), Peary Land (North Greenland) (91).
Fail a hard requirement (ranked after the others, total kept): tolbachik (traversable_15), licancabur (traversable_15).
Confidence of the assessments: 1 high, 18 medium, 17 low.
Score lowered by vegetation (NDVI 0.2 to 0.6, factor in brackets): gosses-bluff (×0.9), wolfe-creek (×0.69), popigai (×0.9), manicouagan (×0.12).
Excluded for dense vegetation (NDVI ≥ 0.6): amazon.

### Instrument calibration

| Rank | Site | Role | Score | Rank range (80% of scenarios) | Confidence |
|---|---|---|---|---|---|
| 1 | axel-heiberg | candidate | 87 | 1-2 | high |
| 2 | haughton | validation | 85 | 2-5 | high |
| 3 | peary-land | candidate | 85 | 1-5 | high |
| 4 | tunnunik | candidate | 84 | 3-5 | high |
| 5 | erebus | candidate | 83 | 2-6 | medium |
| 6 | elgygytgyn | candidate | 79 | 6-8 | high |
| 7 | dry-valleys | validation | 74 | 6-13 | high |
| 8 | popigai | candidate | 73 | 7-12 | high |
| 9 | pingualuit | candidate | 72 | 8-15 | high |
| 10 | changtang | candidate | 71 | 6-18 | high |

Expected in the top half (rank ≤ 18) and present: dry-valleys.
Expected but lower: atacama (#24), svalbard-bockfjorden (#20).
All known analogs: haughton (#2, 85), dry-valleys (#7, 74), meteor-crater (#14, 65), black-point (#15, 65), svalbard-bockfjorden (#20, 57), atacama (#24, 50), death-valley (#28, 38), iceland-holuhraun (#31, 32), mauna-kea (#34, 17).
Best candidate sites (hypotheses to validate): McGill Arctic Research Station, Axel Heiberg Island (Nunavut) (87), Peary Land (North Greenland) (85), Tunnunik Crater (Victoria Island, NWT) (84).
Confidence of the assessments: 25 high, 8 medium, 3 low.
Score lowered by vegetation (NDVI 0.2 to 0.6, factor in brackets): popigai (×0.9), gosses-bluff (×0.9), wolfe-creek (×0.69), manicouagan (×0.12).
Excluded for dense vegetation (NDVI ≥ 0.6): amazon.

### Self-sufficient colony

| Rank | Site | Role | Score | Rank range (80% of scenarios) | Confidence |
|---|---|---|---|---|---|
| 1 | dry-valleys | validation | 100 | 1-6 | medium |
| 2 | tunnunik | candidate | 100 | 1-3 | high |
| 3 | haughton | validation | 99 | 2-4 | high |
| 4 | popigai | candidate | 90 | 4-6 | high |
| 5 | pingualuit | candidate | 84 | 4-30 | medium |
| 6 | mistastin | candidate | 82 | 5-8 | medium |
| 7 | iceland-holuhraun | validation | 60 | 7-13 | medium |
| 8 | svalbard-bockfjorden | validation | 52 | 6-31 | low |
| 9 | black-point | validation | 50 | 8-12 | medium |
| 10 | namib-gobabeb | candidate | 50 | 8-13 | medium |

Expected in the top half (rank ≤ 18) and present: dry-valleys, haughton.
All known analogs: dry-valleys (#1, 100), haughton (#3, 99), iceland-holuhraun (#7, 60), svalbard-bockfjorden (#8, 52), black-point (#9, 50), death-valley (#19, 25), atacama (#25, 11), meteor-crater (#32, 25), mauna-kea (#36, 0).
Best candidate sites (hypotheses to validate): Tunnunik Crater (Victoria Island, NWT) (100), Popigai Crater (Siberia) (90), Pingualuit Crater, west rim (Nunavik, Quebec) (84).
Fail a hard requirement (ranked after the others, total kept): axel-heiberg (slope_mean), elgygytgyn (slope_mean), erebus (slope_mean), peary-land (slope_mean), tolbachik (slope_mean), meteor-crater (slope_mean), hoggar-atakor (slope_mean), licancabur (slope_mean), payunia (slope_mean), mauna-kea (slope_mean).
Confidence of the assessments: 5 high, 28 medium, 3 low.
Score lowered by vegetation (NDVI 0.2 to 0.6, factor in brackets): popigai (×0.9), gosses-bluff (×0.9), wolfe-creek (×0.69), manicouagan (×0.12).
Excluded for dense vegetation (NDVI ≥ 0.6): amazon.
<!-- rankings:end -->

## Reading the misses

- **Holuhraun in robotics (#32).** At 1 km the lava field is flatter (mean slope 1.9°) and smoother (detrended relief 2.8 m) than 95% of south polar windows, so both similarity criteria score 0. Its difficulty for a rover lies below the DEM scale, which neither DEM resolves. v1 also missed it.
- **Atacama in calibration (#24).** Dry, calm air, but a subduction margin (1,452 earthquakes M ≥ 4.5 within 300 km) and a mean temperature of 12.7 °C: the seismometer, drill and cold-soak criteria score 0. v1 ranked it 12th because the M ≥ 2.5 catalog it used is incomplete in South America.
- **Svalbard in calibration (#20, was #31).** Low specific humidity, but 106 earthquakes M ≥ 4.5 within 300 km and little thermal cycling.
- **Why not retune.** The expectations were written by the team that built v1. Adjusting v2 until they are met would make the check circular. Each miss is explained by a measurement.

## What the statistics add

- **Chance baseline.** A random ranking would meet at least 8 of 11 expectations about 10% of the time (modes treated as independent, indicative). With v1 it was 2.6%: v2 agrees less with the team's expectations.
- **Robustness.** 500 Monte Carlo scenarios (fixed seed) perturb weights, tolerances and bounds and redraw every site value that has a quantified uncertainty. On average an expectation holds in 73% of them.
- **Rank ranges and confidence.** Next to each rank, the 10th to 90th percentile range and a confidence label (coverage, unknown requirements, width of the total's interval). In robotics, half of the sites have low confidence: 1 km terrain statistics change a lot from one kilometre to the next.
- **Hard requirements.** Sites that fail a requirement (too little ground under 15° for a rover, too steep to build) are ranked after the others with their total kept.

## Limits of this validation

- **Not independent.** The expectations (`known_for`) were defined by the team, and one parameter was adjusted after measurement (the NDVI threshold, see [scenarios.md](../history/v1-scenarios.md)). This is a consistency check, not an independent benchmark.
- **One negative control.** With a single negative site, a ROC curve or AUC would be meaningless, so none is reported. A fair benchmark needs an expectation list fixed in advance from the literature and a dozen negative controls (humid, forested or low-latitude sites).
- **Weights and thresholds are not calibrated.** Scores rank sites, they are not probabilities. The Monte Carlo analysis covers these choices and the data uncertainties that are quantified; it does not cover the choice of criteria, unquantified data errors or the 1 km scale.
- **Missing criteria.** Lighting at the pole, lithology, regolith mechanics, communications and logistics are not modelled, so a high score does not certify a test site. See [SCIENTIFIC_LIMITATIONS.md](v2/SCIENTIFIC_LIMITATIONS.md).
- **Vegetation.** NDVI is a one-point annual mean; the graded filter reduces, but does not remove, the risk of misjudging a large heterogeneous site.
- **Rank stability labels.** "Stable" (the 10th to 90th percentile rank range spans 6% of the ranked sites or less, about 2 places out of 36), "moderate" (up to 25%, about 9 places) and "fragile" (more) are presentation choices, shown next to the numbers.

## Candidate sites to validate

These are hypotheses produced by the model, not discoveries: none has been checked against field data, and several are already known to specialists. Their rank ranges are wide; read them as "worth a closer look".

1. **Erta Ale and Aorounga (robotics, both 100, rank ranges 1-14 and 1-11).** Their 1 km slope and detrended relief fall inside the lunar interquartile ranges and most of the ground is under 15°. Erta Ale is an active basaltic shield, Aorounga an eroded impact structure in the Sahara. Neither is highland rock.
2. **Tunnunik Crater (colony, 100, rank range 1-3, high confidence).** Arctic impact crater, mean temperature -13 °C at site elevation, no earthquake M ≥ 4.5 within 300 km since 2000, flat ground.
3. **Mistastin (colony, 82).** The best rock twin of the lunar highlands (anorthosite, references R54 and R55 in [SCIENTIFIC_REFERENCES.md](../REFERENCES.md)); no criterion measures rock type yet, so its score does not reflect it.

Coordinates of several sites are approximate (`data/candidates.json`).
