# Validation of the rankings

Known analogs should rank well, not in every mode, but in the modes they are actually used for. The expectations are in `data/candidates.json` (`known_for` field); the report below is produced by [`tools/validation/rankings.py`](../tools/validation/rankings.py) against the running API (real sources):

```bash
docker compose up --build -d
python tools/validation/rankings.py --markdown docs/validation.md
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

Other expectations: the negative control (Amazon) is excluded or last in every mode; hot deserts rank low in the colony mode (polar cold) and humid polar sites rank low in the calibration mode (dry air). Pass threshold: at least 75% of expectations met, and the negative control always excluded or last.

## Result (15 November 2026)

<!-- rankings:start -->
**Verdict: met.** Expectations met: 9/11 (82%, threshold 75%). Negative control excluded or last in every mode: yes.


Chance baseline: a random ranking would meet at least 9/11 expectations 2.6% of the time (modes treated as independent: indicative).
Robustness: on average each expectation is still met in 82% of the sensitivity scenarios (weights ±50%, tolerances ±25%, bounds ±10%).
Fragile expectations (met in fewer than half of the scenarios): iceland-holuhraun in robotics, svalbard-bockfjorden in calibration.

| Mode | Sites ranked | Expected analogs in the top half | Negative control | Mean criteria coverage |
|---|---|---|---|---|
| Robotics validation | 36 | 5/6 | excluded or last | 100% |
| Instrument calibration | 36 | 2/3 | excluded or last | 100% |
| Self-sufficient colony | 36 | 2/2 | excluded or last | 100% |

### Robotics validation

| Rank | Site | Role | Score | Rank range (80% of scenarios) |
|---|---|---|---|---|
| 1 | craters-of-the-moon | candidate | 99 | 1-1 |
| 2 | atacama | validation | 90 | 2-4 |
| 3 | changtang | candidate | 88 | 2-6 |
| 4 | meteor-crater | validation | 87 | 2-7 |
| 5 | hoggar-atakor | candidate | 84 | 4-8 |
| 6 | black-point | validation | 83 | 3-10 |
| 7 | mauna-kea | validation | 80 | 5-12 |
| 8 | peary-land | candidate | 80 | 5-11 |
| 9 | tenoumer | candidate | 79 | 6-11 |
| 10 | erta-ale | candidate | 78 | 7-13 |

Expected in the top half (rank ≤ 18) and present: atacama, black-point, haughton, mauna-kea, meteor-crater.
Expected but lower: iceland-holuhraun (#19).
All known analogs: atacama (#2, 90), meteor-crater (#4, 87), black-point (#6, 83), mauna-kea (#7, 80), svalbard-bockfjorden (#13, 72), haughton (#16, 68), dry-valleys (#18, 66), iceland-holuhraun (#19, 63), death-valley (#31, 42).
Best candidate sites (hypotheses to validate): Craters of the Moon (Idaho) (99), Changtang Plateau (Tibet) (88), Atakor volcanic field, Hoggar (Algeria) (84).
Score lowered by vegetation (NDVI 0.2 to 0.6, factor in brackets): gosses-bluff (×0.9), popigai (×0.9), wolfe-creek (×0.69), manicouagan (×0.12).
Excluded for dense vegetation (NDVI ≥ 0.6): amazon.

### Instrument calibration

| Rank | Site | Role | Score | Rank range (80% of scenarios) |
|---|---|---|---|---|
| 1 | hoggar-atakor | candidate | 77 | 1-2 |
| 2 | namib-gobabeb | candidate | 70 | 2-6 |
| 3 | erebus | candidate | 68 | 1-7 |
| 4 | harrat-khaybar | candidate | 65 | 3-9 |
| 5 | axel-heiberg | candidate | 62 | 4-14 |
| 6 | changtang | candidate | 62 | 3-12 |
| 7 | qaidam-lenghu | candidate | 61 | 4-13 |
| 8 | tunnunik | candidate | 60 | 5-16 |
| 9 | dry-valleys | validation | 58 | 5-19 |
| 10 | licancabur | candidate | 57 | 5-16 |

Expected in the top half (rank ≤ 18) and present: atacama, dry-valleys.
Expected but lower: svalbard-bockfjorden (#31).
All known analogs: dry-valleys (#9, 58), atacama (#12, 56), black-point (#14, 55), meteor-crater (#16, 52), haughton (#23, 47), death-valley (#29, 39), svalbard-bockfjorden (#31, 34), mauna-kea (#33, 32), iceland-holuhraun (#34, 32).
Best candidate sites (hypotheses to validate): Atakor volcanic field, Hoggar (Algeria) (77), Namib gravel plains, Gobabeb (Namibia) (70), Mount Erebus, Ross Island (Antarctica) (68).
Score lowered by vegetation (NDVI 0.2 to 0.6, factor in brackets): popigai (×0.9), gosses-bluff (×0.9), wolfe-creek (×0.69), manicouagan (×0.12).
Excluded for dense vegetation (NDVI ≥ 0.6): amazon.

### Self-sufficient colony

| Rank | Site | Role | Score | Rank range (80% of scenarios) |
|---|---|---|---|---|
| 1 | dry-valleys | validation | 100 | 1-1 |
| 2 | tunnunik | candidate | 92 | 2-2 |
| 3 | haughton | validation | 88 | 3-3 |
| 4 | mistastin | candidate | 83 | 4-7 |
| 5 | popigai | candidate | 83 | 4-6 |
| 6 | pingualuit | candidate | 79 | 6-8 |
| 7 | iceland-holuhraun | validation | 77 | 5-10 |
| 8 | erebus | candidate | 77 | 4-8 |
| 9 | axel-heiberg | candidate | 69 | 8-9 |
| 10 | elgygytgyn | candidate | 69 | 9-10 |

Expected in the top half (rank ≤ 18) and present: dry-valleys, haughton.
All known analogs: dry-valleys (#1, 100), haughton (#3, 88), iceland-holuhraun (#7, 77), svalbard-bockfjorden (#12, 55), black-point (#18, 41), death-valley (#22, 38), atacama (#31, 25), meteor-crater (#32, 20), mauna-kea (#34, 15).
Best candidate sites (hypotheses to validate): Tunnunik Crater (Victoria Island, NWT) (92), Mistastin impact structure, east shore (Labrador) (83), Popigai Crater (Siberia) (83).
Score lowered by vegetation (NDVI 0.2 to 0.6, factor in brackets): popigai (×0.9), gosses-bluff (×0.9), wolfe-creek (×0.69), manicouagan (×0.12).
Excluded for dense vegetation (NDVI ≥ 0.6): amazon.
<!-- rankings:end -->

## Reading the misses

- **Holuhraun in robotics.** The lava flow is recent and rough at meter scale but flat at 1 km scale (mean slope 2.4°). The engine measures relief over 1 km, like the lunar DEM, and does not see the fine roughness that matters for navigation. A smaller scale would need a finer DEM on both sides.
- **Svalbard in calibration.** Arctic air is humid (the mode asks for at most 40% humidity, a proxy for no atmosphere). The AMASE tests target Mars instruments, not a dry Moon-like environment.
- **What it shows.** The engine does not only rediscover famous analogs: it says what each one is a good analog for, and what not.

## What the statistics add

- **Chance baseline.** If each mode ranked its sites at random, at least 9 of 11 expectations would be met about 3% of the time (exact calculation, modes treated as independent, so indicative). The ranking is not random with respect to our expectations.
- **Robustness.** The sensitivity analysis perturbs weights, tolerances and interval bounds 500 times (fixed seed). The two misses (Holuhraun in robotics, Svalbard in calibration) are also the two expectations met in fewer than half of the scenarios: they are not borderline, the data say so. The nine hits hold in most scenarios.
- **Rank ranges.** Next to each rank, the 10th to 90th percentile range shows how far it can move. A 1 to 1 range means the rank does not depend on the exact weights; 4 to 14 means it does.

## Limits of this validation

- **Not independent.** The expectations (`known_for`) were defined by the team, and one parameter was adjusted after measurement (the NDVI threshold, see [scenarios.md](scenarios.md)). This is a consistency check, not an independent benchmark.
- **One negative control.** With a single negative site, a ROC curve or AUC would be meaningless, so none is reported. A fair benchmark needs an expectation list fixed in advance from the literature and a dozen negative controls (humid, forested or low-latitude sites).
- **Weights and tolerances are not calibrated.** Scores rank sites, they are not probabilities. The sensitivity analysis covers these choices only; it does not cover the choice of criteria, errors in the data or the 1 km scale.
- **Missing criteria.** Lighting at the pole, lithology, regolith mechanics, communications and logistics are not modelled, so a high score does not certify a test site.
- **Vegetation.** NDVI is a one-point annual mean; the graded filter reduces, but does not remove, the risk of misjudging a large heterogeneous site.
- **Rank stability labels.** "Stable" (the 10th to 90th percentile rank range spans 6% of the ranked sites or less, about 2 places out of 36), "moderate" (up to 25%, about 9 places) and "fragile" (more) are presentation choices, shown next to the numbers.

## Candidate sites to validate

These are hypotheses produced by the model, not discoveries: none has been checked against field data, and some are already known to specialists (for example, Mistastin impact rocks have been used in lunar-highland simulant research).

1. **Tunnunik Crater (Victoria Island, NWT).** 2nd in the colony mode (92/100), right behind the McMurdo Dry Valleys. Arctic impact crater with frozen ground (mean air temperature −14 °C) and no M ≥ 2.5 earthquake within 300 km since 2000. Presented by the team as little studied as a lunar analog (to be verified); research partly funded by the CSA SOAR program.
2. **Mistastin impact structure (Labrador).** Among the top of the colony mode (83/100). Above all the best rock twin of the south pole: anorthosite, the rock of the lunar highlands, which our volcanic criteria cannot measure. The CSA has run analog missions there since 2010.
3. **Atakor volcanic field, Hoggar (Algeria).** Among the top of robotics and calibration: rugged terrain comparable to the lunar south pole (mean slope 12°, roughness 58 m over 1 km, inside the LOLA range), dry air (23% humidity), bare soil (NDVI 0.08), a single M ≥ 2.5 earthquake within 300 km since 2000 (the USGS catalog is less complete in remote regions). We did not find it among established analog sites in the sources checked (not an exhaustive review).

Exact scores are in the report above and change if data or intervals change. Coordinates of these sites are to be confirmed (issue #23).
