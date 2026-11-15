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

| Mode | Sites ranked | Expected analogs in the top half | Negative control | Mean criteria coverage |
|---|---|---|---|---|
| Robotics validation | 32 | 5/6 | excluded or last | 100% |
| Instrument calibration | 32 | 2/3 | excluded or last | 100% |
| Self-sufficient colony | 32 | 2/2 | excluded or last | 100% |

### Robotics validation

| Rank | Site | Role | Score |
|---|---|---|---|
| 1 | craters-of-the-moon | candidate | 99 |
| 2 | atacama | validation | 90 |
| 3 | changtang | candidate | 88 |
| 4 | meteor-crater | validation | 87 |
| 5 | hoggar-atakor | candidate | 84 |
| 6 | black-point | validation | 83 |
| 7 | mauna-kea | validation | 80 |
| 8 | peary-land | candidate | 80 |
| 9 | tenoumer | candidate | 79 |
| 10 | erta-ale | candidate | 78 |

Expected in the top half (rank ≤ 16) and present: atacama, black-point, haughton, mauna-kea, meteor-crater.
Expected but lower: iceland-holuhraun (#19).
All known analogs: atacama (#2, 90), meteor-crater (#4, 87), black-point (#6, 83), mauna-kea (#7, 80), svalbard-bockfjorden (#13, 72), haughton (#16, 68), dry-valleys (#18, 66), iceland-holuhraun (#19, 63), death-valley (#30, 42).
Best understudied sites: Craters of the Moon (Idaho) (99), Changtang Plateau (Tibet) (88), Atakor volcanic field, Hoggar (Algeria) (84).
Excluded by the bare-soil filter (NDVI > 0.2): amazon, manicouagan, popigai, wolfe-creek, gosses-bluff.

### Instrument calibration

| Rank | Site | Role | Score |
|---|---|---|---|
| 1 | hoggar-atakor | candidate | 77 |
| 2 | namib-gobabeb | candidate | 70 |
| 3 | erebus | candidate | 68 |
| 4 | harrat-khaybar | candidate | 65 |
| 5 | axel-heiberg | candidate | 62 |
| 6 | changtang | candidate | 62 |
| 7 | qaidam-lenghu | candidate | 61 |
| 8 | tunnunik | candidate | 60 |
| 9 | dry-valleys | validation | 58 |
| 10 | licancabur | candidate | 57 |

Expected in the top half (rank ≤ 16) and present: atacama, dry-valleys.
Expected but lower: svalbard-bockfjorden (#30).
All known analogs: dry-valleys (#9, 58), atacama (#12, 56), black-point (#14, 55), meteor-crater (#16, 52), haughton (#22, 47), death-valley (#28, 39), svalbard-bockfjorden (#30, 34), mauna-kea (#31, 32), iceland-holuhraun (#32, 32).
Best understudied sites: Atakor volcanic field, Hoggar (Algeria) (77), Namib gravel plains, Gobabeb (Namibia) (70), Mount Erebus, Ross Island (Antarctica) (68).
Excluded by the bare-soil filter (NDVI > 0.2): amazon, manicouagan, popigai, wolfe-creek, gosses-bluff.

### Self-sufficient colony

| Rank | Site | Role | Score |
|---|---|---|---|
| 1 | dry-valleys | validation | 100 |
| 2 | tunnunik | candidate | 92 |
| 3 | haughton | validation | 88 |
| 4 | mistastin | candidate | 83 |
| 5 | pingualuit | candidate | 79 |
| 6 | iceland-holuhraun | validation | 77 |
| 7 | erebus | candidate | 77 |
| 8 | axel-heiberg | candidate | 69 |
| 9 | elgygytgyn | candidate | 69 |
| 10 | peary-land | candidate | 63 |

Expected in the top half (rank ≤ 16) and present: dry-valleys, haughton.
All known analogs: dry-valleys (#1, 100), haughton (#3, 88), iceland-holuhraun (#6, 77), svalbard-bockfjorden (#11, 55), black-point (#17, 41), death-valley (#21, 38), atacama (#28, 25), meteor-crater (#29, 20), mauna-kea (#31, 15).
Best understudied sites: Tunnunik Crater (Victoria Island, NWT) (92), Mistastin impact structure, east shore (Labrador) (83), Pingualuit Crater, west rim (Nunavik, Quebec) (79).
Excluded by the bare-soil filter (NDVI > 0.2): amazon, manicouagan, popigai, wolfe-creek, gosses-bluff.
<!-- rankings:end -->

## Reading the misses

- **Holuhraun in robotics.** The lava flow is recent and rough at meter scale but flat at 1 km scale (mean slope 2.4°). The engine measures relief over 1 km, like the lunar DEM, and does not see the fine roughness that matters for navigation. A smaller scale would need a finer DEM on both sides.
- **Svalbard in calibration.** Arctic air is humid (the mode asks for at most 40% humidity, a proxy for no atmosphere). The AMASE tests target Mars instruments, not a dry Moon-like environment.
- **What it shows.** The engine does not only rediscover famous analogs: it says what each one is a good analog for, and what not.

## Limits of this validation

- The expectations (`known_for`) were defined by the team, and one parameter was adjusted after measurement (the NDVI threshold, see [scenarios.md](scenarios.md)); this is a consistency check, not an independent benchmark.
- Weights and tolerances are not calibrated; scores rank sites, they are not probabilities.

## Highlighted understudied sites

1. **Tunnunik Crater (Victoria Island, NWT).** 2nd in the colony mode (92/100), right behind the McMurdo Dry Valleys. Arctic impact crater with frozen ground (mean air temperature −14 °C) and no M ≥ 2.5 earthquake within 300 km since 2000. Little studied as a lunar analog; research partly funded by the CSA SOAR program.
2. **Mistastin impact structure (Labrador).** Among the top of the colony mode (83/100). Above all the best rock twin of the south pole: anorthosite, the rock of the lunar highlands, which our volcanic criteria cannot measure. The CSA has run analog missions there since 2010.
3. **Atakor volcanic field, Hoggar (Algeria).** Among the top of robotics and calibration: rugged terrain comparable to the lunar south pole (mean slope 12°, roughness 58 m over 1 km, inside the LOLA range), dry air (23% humidity), bare soil (NDVI 0.08), a single M ≥ 2.5 earthquake within 300 km since 2000 (the USGS catalog is less complete in remote regions). Almost absent from the planetary-analog literature.

Exact scores are in the report above and change if data or intervals change. Coordinates of these sites are to be confirmed (issue #23).
