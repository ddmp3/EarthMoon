# Changelog

One entry per merged task. Newest first. Each entry gives the PR, what changed, and the measured effect where there is one.

## 2026-11-18 · T30 Automatic refresh (PR #17)
- David's decision: refresh is automatic. New ADR-009:
  - sources watched per family on a machine signal (S3 ETag, CMR `revision_date`, CDS update date, PDS file checksums and release tables, DOI versions), with the published cadences read on 18/11 and the rest labelled not verified;
  - incremental recompute by content keys: a changed Earth tile reruns only its cells, zones and map tiles; a planetary change reruns compare without touching Earth features; validation always reruns in full;
  - automatic publication only if validation, the regression anchor and a change threshold pass, otherwise held for David; the last 3 releases stay readable;
  - validity and freshness shown to every user (up to date, update in progress, held, check failed, overdue, not checkable, newer release);
  - a local `refresher` container, the only one with outbound network and write access; nothing in Azure.
- ADR-003 to 007, `docs/ARCHITECTURE.md`, the map spec and tasks T40 and T45 aligned; new task T52.

## 2026-11-18 · T30 Target architecture (PR #16)
- Gate G2 signed by David (18/11).
- `docs/adr/` holds ADR-001 to 008, one page each:
  - Python pipeline `tools/discovery/`, with a run manifest per stage;
  - Parquet feature cube, PNG raster tiles with the four states drawn in, zone JSON;
  - presets built offline; custom queries over the cube only, never live sources (the trade-off is explained);
  - `/api/v3` beside v2;
  - one Python implementation, with an internal service that has no public port;
  - no new JavaScript dependency;
  - a staged, resumable global run with a 72 h stop rule;
  - the AI assistant and deployment deferred.
- `docs/ARCHITECTURE.md`: target diagram and new dependencies. Each is the newest release at least 14 days old (FastAPI 0.164.0, published the same day, and pydantic 2.14.3 were therefore not taken), and pip-audit is clean.
- Tasks T40 to T45 gained an "Alignment with the ADRs" section.

## 2026-11-18 · T26 Mapping methodology (PR #15)
- `docs/wiki/methods/mapping.md`:
  - one layer per similarity parameter, with its value, legend text and valid scale;
  - one colour scale for all typicality layers (cividis, colour-blind safe);
  - four states that differ by pattern, not only by colour: evaluated, partial (pastel hatching listing the missing criteria), not evaluated (grey dots, with the reason), masked (outline);
  - confidence as a separate layer;
  - candidate zones by rule (typicality τ, eliminating requirements, masks, 8-connected, minimum area), with the sensitivity grids τ ∈ {0.5, 0.7, 0.9} and area ∈ {1, 3, 9} cells;
  - comparison of 2 to 4 zones, a zone against the reference environment, and a provenance panel for every number.
- `docs/wiki/ui/map-spec.md`: ASCII wireframes (main screen, hover, zone card, comparison, provenance) and accessibility notes, in the existing dark theme with Space Grotesk and Inter.
- The multidimensional layer stays disabled until two non-redundant dimensions exist (T23).

## 2026-11-18 · T25 Validation protocol v1 (PR #14, tag `validation-protocol-v1`)
- `docs/VALIDATION_PROTOCOL.md`: controls, metrics and pass thresholds fixed before any discovery run; the Monte Carlo scope, bias checks, the unexpected-candidate dossiers, and what the protocol cannot show.
- **Positive controls by rule** (`data/validation/positives.yaml`): only places named in the abstract of a verified reference as analog or test sites, and located by a public gazetteer.
  - Mars geology (D): 4 sites from R29 (Big Craters; Mauna Ulu; Kīlauea Iki; Kīlauea caldera).
  - Radar (C4): 2 lava tubes from R25 (Skull Cave and Valentine Cave).
  - **A, B and the other instruments have none**, and say so. The v2 team list is not used (L6).
- **Negative controls by rule** (`data/validation/negatives.yaml`, `tools/research/controls.py`, 4 tests): 18 seeded random points in 6 WorldCover classes where the ground is hidden. The class legend was read from the files' metadata.
- From the R43 abstract, scenario D now has sourced Mars rover limits: 22° on bedrock, 28° on cohesive soil, embedding at 17° in loose sand. Which one applies stays E14.

## 2026-11-18 · T24 Scenarios v3 (PR #13)
- `data/scenarios/{A-lunar-base,B-lunar-robotics,C-instruments,D-mars}.yaml` and `docs/SCENARIOS.md`. They replace `scenarios-v2.json` in T42.
- Each scenario lists its target environments (T20), its similarity parameters (only those kept in T21, either available or waiting for a task), its requirements and eliminating constraints, its proxies, and what it cannot assess. Scenario C covers 7 instruments.
- The only number with a checked source is the Apollo LRV slope (20 to 23°, maximum 25°, NTRS 20250011301), which eliminates in B and C7. All other numbers carry an expert label.
- `docs/LIMITS.md`: E3 and E5 updated (colony scenario replaced; no weights); E13 to E16 added (base site requirements beyond slope, Mars rover limits, instrument requirements, target environment per scenario).
- The validator `validate_scenario` (8 tests) refuses:
  - a similarity parameter that is not kept or is operational;
  - a requirement without a source in REFERENCES.md or an E label in LIMITS.md;
  - an eliminating constraint that is not a requirement;
  - a proxy that does not say what it stands for.

## 2026-11-18 · T23 Comparison methods benchmark (PR #12)
- The protocol was committed before the run (`4580530`). `tools/research/compare_methods.py` (7 analytic tests) benchmarks six candidates on 71,503 lunar windows, 20,000 pilot windows and the 1,410 random T21 windows. Output: `data/research/comparison-t23.json`, `docs/wiki/methods/comparison.md`.
- **Chosen: the two-sided percentile per parameter.** It is calibrated (KS 0.014), the most discriminating (AUC 0.80, 0.86 on random Earth), and robust at 0.5° of noise (0.95). At 1° it falls to 0.891, just below the rule, so the uncertainty is propagated in T25.
- **Rejected, with numbers:**
  - v2 interval score: not calibrated (KS 0.49);
  - Mahalanobis and k-NN: the regional slope is redundant on Earth (Spearman 0.91), and they do not discriminate better;
  - Wasserstein and energy zone distances: not calibrated (KS 0.11 to 0.12), to re-test in T25.
- **Reporting:** dimensions are always separate. A global similarity exists only with two or more non-redundant dimensions; it is the minimum (not compensating), with the geometric mean as a sensitivity check in T43.
- Fixed during the run: zone blocks are now split by block, and Earth block ids were made unique across tiles.

## 2026-11-18 · T22 Spatial and statistical sampling (PR #11)
- `tools/research/sampling.py` (8 tests): 10 random area-weighted GLO-30 land tiles (seed 20261117) and 3 contrasting tiles; resampling to 30, 40 and 90 m; a two-stage screening test; spectra; H3 cell areas; tile count from the bucket listing. Output: `data/research/sampling-t22.json`.
- Decisions (`docs/wiki/methods/sampling.md`):
  - **compare at the planetary pixel scale:** 30 m vs 90 m keeps the rank order (Spearman 0.87 to 0.99), but slope falls by a terrain-dependent factor of 0.47 to 0.96;
  - **processing unit:** the 1° tile in a local equal-area projection (26,450 tiles);
  - **statistics:** 5 km equal-area cells, with median, IQR, p5, p95 and valid fraction; partial or missing cells are hatched;
  - **H3 for display only:** its cells vary by a factor of 1.95 in area at resolution 7;
  - **two-stage search:** 90 m screening with a 2° margin misses 34 of 20,490 fine matches (0.17%) and keeps 48% of the cells.
- **Effective resolution, first look:** at matched slope, LOLA blocks carry about 5 times less relief at 160 m than Earth blocks. This is consistent with L3; the T41 count-map test decides.
- **Budget:** GLO-30 is about 0.96 TB, so it is streamed rather than stored; about 6 h of CPU at 40 m; stage 2 reads only the passing cells (to measure in T40).
- A bug found and fixed during the run: windows of 25 and 11 pixels (1,000 m and 990 m) drift apart, so windows are now assigned to cells by coordinates (new test).

## 2026-11-18 · T21 Dimensions, parameters and redundancy (PR #10)
- `tools/research/redundancy.py` (7 tests) measures Spearman, Pearson and partial correlations of the terrain metrics on all 71,731 lunar windows (LDEM_85S_40M, SHA-256 identical to v2) and on 4,000 seeded random Earth points (1,410 land windows kept; ocean and incomplete windows counted, not scored). Output: `data/research/redundancy-t21.json`, `docs/wiki/methods/redundancy.md`.
- **Result:** the eight v2 terrain metrics carry one independent property, slope (Spearman 0.87 to 0.99 with `slope_mean` on both bodies). Finding L1 is confirmed beyond the 37 sites.
- **New finding:** detrended roughness is almost independent of slope on the Moon (0.18) but almost identical to it on Earth (0.98). It likely reflects the interpolated lunar grid (L3); it stays out of comparison until T41 tests it.
- `data/parameters.yaml`: 31 parameters over six dimensions, each with a comparability class and a decision (keep, context, drop) and its reason. Kept: `slope_mean`, lithology, minerals, day-night amplitude, thermal inertia, ground ice, specific humidity, precipitation, aerosols, wind. Dropped: absolute temperatures, relative humidity, earthquake count, volcano distance, insolation, redundant slope statistics. Rover slope limits move to operational context.
- The validator (`tools/profiles/profiles.py`, 6 new tests) refuses a kept pair with |Spearman| > 0.8 without a written reason.
- `docs/wiki/methods/parameters.md` summarizes the decisions; `docs/LIMITS.md` states the slope finding.

## 2026-11-18 · T20 Planetary environment profiles (PR #9)
- Gate G1 signed by David (18/11): sources that could not be read stay "not verified".
- `data/profiles/spec/`: 16 environment specs, each selected from planetary data by a written rule.
  - Moon, ready: south polar cap (v2 regression anchor, SHA-256 `1609e9b8…`, 71,731 windows), lit polar highlands, permanently shadowed regions, persistently lit areas, mare plains, pits (site set).
  - Mars, ready: ice-rich mid-latitudes (SWIM), north and south polar terrain, aqueous mineral sites (site set), HiRISE rover-scale terrain.
  - Conditional, blocked by unverified maps or catalogues: lunar fresh craters and degraded highlands, Martian volcanic plains, sedimentary basins and caves.
  - `rejected.yaml`: 5 environments rejected, with reasons (for example Mars dune fields: no catalogue, and images alone would select on appearance).
- `tools/profiles/profiles.py` (31 tests, in the gate) checks the specs: products exist in the catalogues; ready specs use no unverified product; thresholds without values carry a sensitivity grid; no circular selection; distributions keep percentiles and joint data.
- `docs/wiki/methods/profiles.md`: one line per environment and the design of the effective resolution experiment (L3) for T41.

## 2026-11-18 · T13 Reference verification (PR #8)
- `tools/research/verify_refs.py` (7 tests, in the gate) checks every DOI of `docs/REFERENCES.md` on Crossref: 59 of 59 verified. Report: `docs/wiki/references-check.md`.
- NTRS reports read through the NTRS API:
  - the **VIPER 15° limit is not stated** in the abstracts, so expert decision E1 stays unverified;
  - the Apollo LRV capability (20 to 23°, max 25°) is verified;
  - NTRS 19930008250 is by Oberst and Nakamura (1992), not Nakamura alone.
- Added R63 (Moriarty and Petro 2022, EPSC, verified) and R64 (Obu et al. 2018 permafrost data).
- The Lunar Sourcebook and SP-4214 remain not verified.

## 2026-11-18 · T12 Earth data inventory (PR #7)
- `data/catalog/earth.yaml`: 41 Earth products (22 verified, 12 partly verified, 6 not verified, 1 not available: no global cave inventory exists). Each records its licence, attribution and use (similarity, mask, qualification, operations). The schema requires these for Earth entries (2 new tests).
- `docs/wiki/data/earth.md`:
  - scales: GLO-90 for screening, GLO-30 for refinement, 2 m only in polar regions;
  - composition is the weak dimension (GLiM open grid 0.5°; EMIT excludes the poles);
  - caves cannot be discovered from global data;
  - Terra MODIS ends 1 December 2026;
  - licences still to check.

## 2026-11-18 · T11 Mars data inventory (PR #6)
- `data/catalog/mars.yaml`: 26 Martian products (7 verified, 11 partly verified, 8 not verified), each fact with source URL and date.
- `docs/wiki/data/mars.md`:
  - profiled now: ice-rich mid-latitudes and polar deposits;
  - partly: aqueous, sedimentary and volcanic terrain;
  - not yet: dunes and caves, which need catalogues.
  - Mars has 1,377 HiRISE DTMs at 1 to 2 m, so terrain can be compared at rover scale.

## 2026-11-18 · T10 Lunar data inventory (PR #5)
- `data/catalog/moon.yaml`: 35 lunar products. Each records nature (measured, derived, model, interpretation), coverage, pixel and effective resolution, units, uncertainty, access and limits, read at the source page with URL and date.
  - Status: 10 verified, 16 partly verified, 9 not verified (hosts refused automated access or rendered nothing).
- `tools/catalog/catalog.py`: shared schema check and table renderer for the Moon, Mars and Earth catalogues; 9 tests; part of the gate.
- `docs/wiki/data/moon.md`:
  - can be profiled now: polar highlands, shadowed regions, lit ridges;
  - partly: mare plains, pits;
  - not yet: crater-age environments, which need the crater database or geologic map, still unverified.
- `tools/docs/publish_wiki.py`: reuses the repository author when committing to the wiki. The wiki is published (8 pages).

## 2026-11-18 · T02 Docs reset (PR #4)
- Short pages:
  - `docs/METHOD.md`, `VALIDATION.md`, `LIMITS.md` (new, condensed from the v2 documents);
  - `DATA.md` and `ARCHITECTURE.md` (renamed, updated);
  - `REFERENCES.md` (renamed);
  - README rewritten (62 lines).
- Full v2 documents moved unchanged to `docs/wiki/v2/`; rankings report to `docs/wiki/rankings.md`; v1 criteria and the Montréal presentation to `docs/history/`, with a note on which of their figures are superseded.
- `tools/docs/check_links.py` (part of the gate: 0 broken links) and `tools/docs/publish_wiki.py` (mirror of `docs/wiki/` to the GitHub wiki; 10 tests).
- Code comments, `openapi.yaml` and `moon-south-pole.json` point to the new paths. No change to scores or data values.

## 2026-11-18 · T01 Quality harness (PR #3)
- `tools/check.sh [api|web|python|e2e|all]`: types, lint, tests, dependency audit, Docker e2e and browser audit, all in pinned Docker images. GitHub Actions runs it on every PR (test only).
- Dependency policy: production 0 vulnerabilities; development advisories only through `tools/security/audit-allowlist.json` (tested gate). One entry: picomatch ReDoS, no patch exists, dev tools only.
- Web unit tests added (vitest, Testing Library, jsdom): 13 tests. Web TypeScript now strict.
- Fixed: a missing value was shown as a 0% match and at score 0 on the radar; now "—" with pastel hatching. Web API contract regenerated (was stale since v2) and checked by the gate. Labels for the 8 v2 parameters. Parameter count on the home page computed (26, was "18").
- Baseline: `docs/wiki/baseline.md` (API 154, web 13, Python 56 tests; e2e 15/15; browser audit 0 defects).

## 2026-11-17 · Plan v3 (PR #2)
- Added the v3 plan: `CLAUDE.md` (session entry point), `docs/plan/README.md` (context, rules, gates, status), and one self-contained task file per task in `docs/plan/tasks/`.
- Decisions recorded:
  - interface changes allowed under quality gates;
  - missing data hatched in pastel;
  - precomputed preset layers, custom criteria computed over a precomputed cube;
  - GitHub wiki as a mirror of `docs/wiki/`;
  - AI assistant deferred.
- No code change.

## 2026-11-17 · Methodology v2 (PR #1, merge `dfd9454`)
- Frozen, versioned data set `data/dataset-v2.json` (value, sigma, flags; SHA-256 of inputs).
- Data corrections: temperature corrected to site elevation; earthquakes counted at M ≥ 4.5; volcano distance replaced by lava tube evidence levels; specific humidity.
- Terrain on the 40 m lunar grid on both bodies, with detrended roughness and traversable share.
- Scoring: criteria with role, basis and rationale; hard requirements; coverage and bounds; Monte Carlo on data and expert choices; confidence label; per-site explanation; Python scorer identical to the API.
- Measured: evaluation grid 15/39 → 28/39; team expectations 9/11 → 8/11 (not retuned). Tests: API 154, Python 55, Docker e2e 15/15.
- Not deployed.

## 2026-11-15 · v1 (hackathon, NASA Space Apps 2026, Montréal)
37 Earth sites ranked against the lunar south pole for 3 missions plus free criteria. Original repository: `ddmp3/nasa-space-app-challenge-2026-cyber-space` (frozen during the NASA evaluation).
