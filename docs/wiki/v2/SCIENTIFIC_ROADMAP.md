# Scientific roadmap

Plan of the scientific corrections, ordered by effect on the validity of the results, then by dependency. Findings are those of [SCIENTIFIC_AUDIT.md](SCIENTIFIC_AUDIT.md); the target method is section 10 of [SCIENTIFIC_METHODOLOGY.md](SCIENTIFIC_METHODOLOGY.md).

Status: **done** = implemented, tested and measured in [SCIENTIFIC_VALIDATION.md](SCIENTIFIC_VALIDATION.md) (phase 1, November 2026). **next** = needs only data or work. **expert** = needs a decision by a domain expert first ([SCIENTIFIC_LIMITATIONS.md](SCIENTIFIC_LIMITATIONS.md), section 3).

## 1. Corrections

| Step | Problem (finding) | Severity | Consequence on v1 results | Correction | Basis | Files | Validation and tests | Done when | Status |
|---|---|---|---|---|---|---|---|---|---|
| 1 | Results not reproducible (R1) | Major, prerequisite of every comparison | A score cannot be checked or compared | Freeze POWER, USGS (fixed end date) and GVP in a versioned snapshot; build a versioned data set with input hashes; return method and data versions | Reproducibility | `tools/precompute/live_snapshot.py`, `build_dataset.py`, `apps/api/src/sources/dataset.ts`, `analyze.ts` | No network call while scoring (test); same response twice | Versions in every response; data set rebuildable | done |
| 2 | Temperature at the wrong elevation (C1) | Critical | 12 sites mis-scored on every temperature criterion | Lapse-rate correction with an uncertainty; other climate values set to missing when the cell is more than 1 km off | [R30, R38] | `build_dataset.py` | Unit tests of the correction and of the missing rule; 0/37 sites off | Grid indicator 3 at 0 | done |
| 3 | Earthquake count measures networks (S1) | Critical | Calibration and colony rankings biased by country | M ≥ 4.5 count with a Poisson uncertainty; M ≥ 2.5 deprecated | Gutenberg-Richter ratios measured in the audit | `live_snapshot.py`, `build_dataset.py`, `modes.ts` | Ablation step S2 | No scenario uses `quake_count` | done |
| 4 | Volcano distance as basalt and lava tubes (V1) | Critical | Mistastin penalized, non-basaltic volcanoes rewarded | Remove from scenarios; add `lava_tube_evidence` with three referenced levels | [R16 to R26, R29, R53] | `data/evidence/lava-tubes.json`, `build_dataset.py`, `modes.ts` | Tests: predisposition never counted as presence; not assessed stays null | No scenario uses `volcano_distance` | done |
| 5 | Terrain metrics (T1, T2, T3) | Major | Slope counted twice; max slope misused; baselines differ | Same 40 m grid and same function on both bodies; detrended roughness; traversable share; lunar percentiles as interval and tolerances | [R4, R5] | `tools/precompute/terrain_metrics.py`, `site_terrain.py`, `lunar_reference_v2.py` | Analytic tests (tilted plane, noise); v1 lunar percentiles reproduced; interval = lunar quartiles (test) | Done | done |
| 6 | Wrong humidity measure (C2), insolation (C4) | Major | Dry polar air ranked humid; lighting misdescribed | Specific humidity; insolation removed from scenarios | Physics of saturation | `modes.ts` | Ablation step S4 | No scenario uses `humidity` or `solar` | done |
| 7 | Missing data hidden (M3) | Major | Poorly documented sites indistinguishable from documented ones | Coverage, bounds, `unknown` requirement, missing list | [R51] | `score.ts`, `analyze.ts` | Tests: zero vs missing, bounds, unknown | Done | done |
| 8 | Everything averaged; one story for all missions (M1, M2) | Major | Unsuitable sites rank well | Roles and bases per criterion; hard requirements; irrelevant criteria removed; equal weights | [R28, R51] | `types.ts`, `score.ts`, `modes.ts` | Tests: failed requirement ranks last; every criterion documented | Done for the three existing scenarios | done |
| 9 | Uncertainty ignores data (M4) | Major | Rank ranges too narrow | Per-value sigma; Monte Carlo on data and choices; total interval; confidence label | [R50, R52] | `sensitivity.ts`, `analyze.ts` | Tests: normal draws, clipping, wider interval with noisy data | Done | done |
| 10 | No explanation of a result | Moderate | Users cannot see why a site ranks | Contributions, strengths, weaknesses, decisive, missing, flagged, expert share | — | `explain.ts`, `app.ts` | Tests: contributions sum to the total | Done in the API | done |
| 11 | Uncertainty missing for wind, humidity, precipitation, MODIS | Moderate | Intervals are lower bounds | Interannual standard deviation from POWER monthly or daily series; MODIS spread over several years | — | `live_snapshot.py`, `modis_values.py`, `build_dataset.py` | Sigma present on 15/15 scenario criteria | Grid indicator 7 at 100% | next |
| 12 | One point stands for a site (P1) | Major | A site's score depends on an arbitrary kilometre | Site polygons; distribution of each indicator inside; score of the best or median window, stated | — | `data/candidates.json` (polygons), `site_terrain.py` | Rank change against point-based scores reported | Every site has a polygon from a cited source | next |
| 13 | No ground material (X1, criterion 13) | Major | No statement about the analog quality of the ground is possible | Lithology (GLiM, national geological maps); mineralogy where covered (EMIT, ASTER); compared with lunar polar composition | [R15, R31, R35] | new `tools/precompute/lithology.py` | Mistastin anorthosite recognised; known basalt fields recognised | Lithology for 37/37 sites with a source per value | next |
| 14 | Terrain scale too coarse for rovers (T1) | Major | Mobility conclusions limited to 40 m to 1 km | 2 to 5 m models on both bodies (LOLA landing-site models, LROC stereo; ArcticDEM, REMA, national lidar) | [R48, R58] | `terrain_metrics.py` reused at 5 m | Same tests at 5 m | Robotics scenario at rover scale for the sites where both exist | next |
| 15 | Weights and thresholds by judgement (M1) | Major | Calibration and colony rest on judgement only | Mission requirements from documents; expert elicitation for the rest | — | `modes.ts` | Grid indicator 5 ≥ 50% in every scenario | — | expert |
| 16 | Mission profiles (M2) | Major | One scenario per objective, no vehicle or instrument profile | Scientific rover, scouting rover, cargo, drill, cave explorer, crewed mission; each with cited requirements | [R44, R49] | `modes.ts`, new profile files | One profile per mission type with a requirement document | — | expert |
| 17 | Target environments (K1, K2) | Major | Only the south polar highlands have a reference | Reference profiles for mare plains, mare pits and tubes, shadowed regions, fresh craters | [R12, R17 to R19] | `data/reference/` | Each profile computed from primary data like `terrain_v2` | — | next |
| 18 | Validation circular (Va1, criterion 12) | Major | 9/11 or 8/11 says little | Expectation list fixed in advance from the analog literature by people outside the project; 10 or more negative controls | [R27, R28] | `data/candidates.json`, `tools/validation/rankings.py` | Report against the independent list | Independent list committed before rerunning | expert |
| 19 | Display the new results | Moderate (usability) | Explanation, confidence, coverage, failed requirements exist only in the API | Interface work: labels of new parameters, confidence badge, coverage, explanation panel | — | `apps/web/` | UI tests | Out of scope of phase 1 | next |

## 2. Dependencies

```
1 reproducibility ──┬── 2, 3, 4, 5, 6 (data corrections) ──┬── 7, 8, 9, 10 (scoring) ──── 19 (interface)
                    │                                       └── 11 (more uncertainties)
                    ├── 12 polygons ──── 14 finer terrain
                    ├── 13 lithology
                    └── 17 target environments ──── 16 mission profiles ──── 15 weights
18 independent validation: can start now; must be fixed before any further tuning
```

## 3. Interface needs created by phase 1 (documented, not implemented)

| Need | API field | Suggested display |
|---|---|---|
| Labels and help of new parameters | `GET /api/parameters` already returns labels | Add `roughness_detrended`, `traversable_15/20/25`, `slope_p95`, `specific_humidity`, `quake_m45_count`, `lava_tube_evidence` to `apps/web/src/api.ts` and `content-fr.ts`; regenerate `api-schema.ts` |
| Confidence | `sites[].confidence`, `stability.totalP10/P90` | Badge next to the score; interval as a whisker |
| Coverage and bounds | `coverage`, `totalRange`, `missing` | "Based on 3 of 4 criteria; between 53 and 78 if the missing one were measured" |
| Failed requirement | `requirements`, `failedRequirements` | Separate group "fails a hard requirement" at the end of the list |
| Explanation | `GET /api/sites/{id}` `explanation` | Strengths and weaknesses list with the rationale of each criterion; share resting on judgement |
| Quality flags | `criteria[].flags`, `criteria[].sigma` | Icon with the flag text; value ± sigma |
| Versions | `methodology` | Footer of the results |
| Deprecated parameters | labels say "deprecated" | Hide them from the free-criteria builder or mark them |
| "See the match" panel shows v1 terrain values | `apps/web/public/sites/manifest.json` (built by `tools/precompute/site_visuals.py` from the v1 30 m geometry) | Regenerate the manifest from `terrain_v2` so the panel and the scorecard agree (Atacama: 7.97° in the panel, 7.85° in the scorecard) |

## 4. Additional data sources

Each source answers a parameter the audit found missing. Priority: **indispensable** (a result cannot be interpreted without it), **strongly recommended**, **complementary**, **experimental**.

| Source | Parameter | Why it matters | Lunar relevance | Coverage | Resolution | Access and terms | Integration difficulty | Scientific limits | Priority |
|---|---|---|---|---|---|---|---|---|---|
| Site polygons from protected-area boundaries, published analog site descriptions | Site extent | A site is an area, not a point | — | 37 sites | Vector | Varies, mostly open | Low (manual, with source) | Boundaries are administrative, not geological | Indispensable |
| GLiM global lithological map [R31] | Lithology class | First-order ground material (anorthosite, basalt, sediments) | Highlands are anorthositic, maria basaltic [R15] | Global | 1:3,750,000 scale | Open, CC BY | Low | Coarse classes; anorthosite bodies are small and may be missed | Indispensable |
| National geological maps (Geological Survey of Canada, USGS, others) | Lithology at site scale | Confirms or corrects GLiM | Same | National | 1:50,000 to 1:1,000,000 | Mostly open | Medium (formats differ) | Heterogeneous legends | Strongly recommended |
| EMIT L2B mineralogy [R35] | Surface mineral groups (spectral) | Composition similarity | Compare with Kaguya / Moon Mineralogy Mapper polar maps [R15] | About 52°N to 52°S, arid regions | 60 m | NASA LP DAAC, open | Medium | Excludes polar sites; designed for dust sources | Strongly recommended |
| ASTER L2 emissivity, ASTER Global Emissivity Database | Silica content, feldspar vs mafic | Composition where EMIT does not reach | Same | Global land | 90 m (L2), 100 m (GED) | NASA LP DAAC, open | Medium | Vegetation and moisture affect emissivity | Strongly recommended |
| LOLA 5 m landing-site models [R48]; LROC NAC stereo DTMs | Lunar slope at rover scale | Compare at the scale a rover feels | Direct | Artemis regions | 2 to 5 m | NASA PDS, open | Medium | Few regions; shadowed areas less accurate | Strongly recommended |
| ArcticDEM, REMA [R58], national lidar (USGS 3DEP, others) | Earth slope at rover scale | Same, Earth side | — | Arctic, Antarctica, some countries | 1 to 8 m | Open | Medium (volume) | Temporal mismatch, snow | Strongly recommended |
| NASA POWER daily series | Interannual spread of climate values | Sigma for wind, humidity, precipitation | — | Global | About 50 km | Open | Low | Same cell problem | Strongly recommended |
| Permafrost maps [R32] and ESA CCI Permafrost | Ground ice presence | Replaces air-temperature proxy for the "frozen ground" need | Proxy for ice-bearing regolith (with the caveats of section 4.2 of the methodology) | Northern Hemisphere (Obu); global (CCI) | 1 km | Open | Low | Model output | Strongly recommended |
| SoilGrids 2.0 [R34] | Sand, silt, clay fractions | First estimate of grain size | Weak: lunar soil formation is different [R9, R40] | Global | 250 m | Open, CC BY | Low | Model predictions, poorly constrained in deserts and polar regions | Complementary |
| Diviner rock abundance and thermal inertia [R13, R14] | Lunar rock cover, regolith thermal inertia | Lunar side of a rock and thermal comparison | Direct | Global Moon | 128 to 237 m per pixel | NASA PDS, open | Medium | Polar coverage and night-time limits | Complementary |
| ESA WorldCover | Land cover | Better bare-ground filter than one NDVI pixel | — | Global | 10 m | Open, CC BY | Low | Classes, not physical properties | Complementary |
| Mini-RF, LRO LEND, Lunar Prospector neutron data | Lunar subsurface scattering, hydrogen | Lunar side of a "volatiles" scenario | Direct | Global Moon or polar | km scale | NASA PDS, open | High | Interpretation debated | Experimental |
| Sentinel-1, RADARSAT Constellation Mission SAR | Earth surface roughness at cm to dm scale | Roughness below the DEM scale | Indirect (radar scattering on the Moon differs) | Global, Canada | 5 to 20 m | Open | High | Moisture and vegetation dominate the signal on Earth | Experimental |
| Seismic station noise levels (IRIS / EarthScope station noise PDFs) | Ambient seismic noise | What actually limits a seismometer [R36] | The Moon is far quieter [R45] | Near stations only | Per station | Open | Medium | Sparse in remote regions | Experimental |

Not proposed: anything about lunar dust electrostatics, regolith cohesion or particle shape, because no global Earth data set describes them and they are not reproducible in open air (audit, section 7). Those belong to laboratory and chamber tests.
