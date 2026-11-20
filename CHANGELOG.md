# Changelog

One entry per merged task. Newest first. Each entry gives the PR, what changed, and the measured effect where there is one.

## 2026-11-20 · T46 Geology dimension (PR #28)
- **Source:** Macrostrat, David's choice of 20/11 (CC-BY 4.0): `carto` vector tiles at zoom 8, which hold the finest map unit Macrostrat has at each place. 20,307 tiles, 362 MB, 0 failures. GLiM was set aside: its polygons have no stated licence, and its grid is 50 km.
- **Crosswalk E17** (`docs/wiki/methods/geology-crosswalk.md`, delegated by David to Claude, to be reviewed before G5):
  - highlands: anorthosite, with plagioclase-bearing mafic rocks as partial;
  - maria: basalt, with dolerite and diabase as partial;
  - pits: basalt as partial only;
  - a generic class or no map is unresolved, never "no match".
  - Amended after the first global run: a mixed unit counts the lunar rock only when the map lists it first. This fixed a false highland match over most of the Canadian Shield.
- **Results** (`docs/wiki/runs/run-002-geology.md`):
  - no map unit 29.2%, unresolved 21.5 to 21.8%;
  - highland match 0.05% (the Grenville and Labrador anorthosite massifs), mare match 1.1% (Paraná, Canaries, Iceland);
  - none of the 40 top slope zones matches;
  - Mistastin is no match: its anorthosite is below the 1:5M map.
- **In the product:**
  - release `r-51bfb3d5` (zones carry geology shares; the zone cache makes the next exports faster);
  - a geology tile layer per target;
  - geology of cells and sites in the discovery service;
  - in the missions: a layer picker, a geology legend, the zone card row, a site card column and the hover line.
- **Open:** mineralogy (EMIT, 52°N to 52°S) is not used; the T46 test "EMIT absence is not covered" waits for it.

## 2026-11-20 · T45b v3 inside the missions (PR #27)
- **David's review of T45:** the separate discovery page looked added at the last minute, and the missions did not use the new data. The v3 results now live in the missions:
  - **robotics (B) and colony (A):**
    - the 37 known sites keep their v2 ranking, with a v3 mark: typicality of the 5 km cell holding each site;
    - a "Discovered zones" tab;
    - one map with the v3 layers, legend, cells and coverage overlay;
    - validity line, zone card, comparison, provenance;
  - **site card:** "Our v3 data at this place", one row per lunar environment (new `GET /api/v3/sites`, discovery service `/points`). At Atacama, for B: lit highlands 0.56, shadowed regions 0.66, mare plains 0.07, polar cap 0.57, all high confidence;
  - **free criteria:** a v3 search of the whole Earth in the current map view (`POST /api/v3/query`), the map and zones before any v2 run; `#discover` opens it;
  - **calibration:** says that scenario C is not computed in v3 yet.
- **Translations:** scenarios, requirements, limits, processing steps and coverage classes served in English now have French versions (a test covers every text of a release).
- **Fixes the UI audit found:**
  - empty v3 tiles showed as broken images;
  - long French labels overflowed on phones;
  - release documents were fetched again on every screen. They are now read once per page, since a release never changes.
- **ADR-006 budget:** +17.1 KB gzip of JavaScript for v3 (145.3 against 128.2 before v3), first view 0.7 s, 24 tile requests, 0 defects on desktop and phone.

## 2026-11-20 · T45 Interface: discovery map, coverage overlay, comparison (PR #26)
- **Discovery map** (`apps/web/src/v3/`, `#discover`, linked from Home), on API v3:
  - pickers: scenario and lunar environment (targets that are not comparable stay listed, disabled, with the reason);
  - layers: topography; geology, thermal, operational and multidimensional shown disabled with their reason;
  - map: typicality tiles (cividis) to zoom 7, then 5 km cells with a confidence outline and the hover text of the map spec.
- **Coverage overlay** (David's clarification of 19/11): on by default and switchable, six classes drawn as SVG patterns (pastel `#b9c6e8`). Each class has a text label and its land share. On run-002 for B mare plains: ground hidden 43%, screened out 18%, evaluated 26%.
- **Panels:**
  - Data and method: what we cover, catalogue sources with status, processing chain, limits;
  - zone card: spread, missing dimensions by name, requirements, confidence, Monte Carlo, what Earth cannot reproduce;
  - comparison of 2 to 4 zones (strip plots);
  - provenance;
  - validity and freshness from `/api/v3/status` on the map, zone card and provenance.
- **v2 gaps fixed:**
  - deprecated parameters flagged in the criteria builder, with the replacement;
  - the unsourced "28 shallow moonquakes in 8 years" note removed;
  - radar labels wrapped;
  - a site-card assessment block: confidence, coverage with the total range, hard requirements, explanation;
  - "See the match" recomputed from terrain_v2 (Atacama 7.85° in both places; was 7.97 in the panel), 37 lunar twins searched again.
- **UI audit:** the map is walked on desktop and phone, with contrast checks and the ADR-006 budget. Measured on the run-002 release: first view 0.83 s, 8 KB gzip of v3 JavaScript (own chunk), 24 tile requests, 0 defects. Defects the audit found were fixed: phone overflow, covered checkboxes, invisible "not evaluated" text.
- **Rate limit:** the cells of a map view (one request per pan or zoom) have their own limit, 5 times the general one, like tiles. The UI audit runs its desktop and phone passes one minute apart: the 120 requests per minute and per IP stay.
- **Before and after:** screenshots of the v2 pages change only where intended (Home card, assessment block, regenerated match images).
- **Open:** the zone-against-reference Q–Q plot of ADR-006 needs window quantiles per zone in the release, so it is not built.

## 2026-11-20 · T44 API v3: layers, zones, custom queries (PR #25)
- **Static releases** (`tools/discovery/release.py`, ADR-004, ADR-009). A validated run is exported once into JSON files: release, profiles, scenarios, method, coverage, status, and the zones of every τ and size of the grid. The id is a hash of the content; the index keeps the current release and the last 3.
- **Tiles** (`tools/discovery/tiles.py`): PNG, zoom 0 to 7, typicality (cividis) and the coverage overlay per scenario and target. Measured on run-002: 127,062 tiles, 612 MB. Typicality 95.7 MB per layer, coverage 26.6 MB per layer; ADR-002 estimated 50 MB.
- **API `/api/v3`** (contract first in `openapi.yaml`):
  - releases, profiles, scenarios, method, coverage, status, zones and zone cards, served from the release files;
  - layers (own rate limit, 204 for an empty tile);
  - every answer carries the release and the methodology version.
- **Discovery service** `apps/discovery` (FastAPI, ADR-005): internal network only, read-only, no outbound network. It serves the cells in view (5,000 at most) and custom queries (1,000,000 cells, 16 KB body, 30 s).
- **Coverage and Data and method** (David's clarification of 19/11):
  - coverage: land share of six overlay classes;
  - method: catalogue sources with status and verification date, and the processing chain of the run.
- **Status** (ADR-009). The release is validated only when every protocol check passes: run-002 is "not validated" (no positives, masks 17/18, pits). Sources show "not checkable" until the refresher (T52).
- **Fixed before release:**
  - lunar sources listed twice, and the lunar cube shown as "not in catalogue";
  - zone records sorted the 6.3 M cell ids for every zone (hours per file).
- **run-002 release** `r-98f6eee4`: written in 1.8 h, tiles in 6.5 min, in `earthmoon-data/releases/` (not in git). Run the stack on it with `EARTHMOON_RELEASES=C:\Users\david\earthmoon-data\releases docker compose up --build`.
- **Tests:** API 173, discovery service 11, release 13. Docker e2e: TF-16 and TF-17 on a synthetic fixture release.

## 2026-11-19 · T43b run-002 with protocol v3 (PR #24)
- **Protocol v3** (tag `validation-protocol-v3`, David's decision when signing G4, 19/11, before run-002):
  - 5 km cells are HEALPix cells (NSIDE 1303, 25.04 km², one grid for the globe; `tools/discovery/healpix.py`, pure numpy). A cell cut by tile edges keeps the windows of every tile;
  - candidate zones are made of, and ranked on, high-confidence cells only.
  - EASE-Grid 2.0 was tried first and replaced before the tag: its cells stretch near the poles.
- **run-002:**
  - 6,296,808 cells, 0.48 h, 0 failures;
  - cells with fewer than 10 windows: 5.6% → 1.1%;
  - zones: about 30% fewer than in run-001, and a larger share stable in Monte Carlo for every target.
- **Validation:** as in run-001.
  - negatives: 0 of 18 (pass);
  - masks: 17 of 18 (fail);
  - self-consistency: 4 of 5 (pits fail);
  - rebuild: identical (pass).
- **Dossiers:**
  - no artefact left in the top 40;
  - 2 plausible places (Andrelândia, Brazil; northern Skye, Scotland), 21 unknown;
  - 36 of the 40 are shadowed-region zones.
  - ranking against NASADEM: Spearman 0.08 (A) and 0.34 (B), not robust; at 30 m: 60 and 65% of the top 20 kept (run-001: 35 and 40%).
- **Fixed during the run:** coverage and confidence are now read at the finest scale where each cell has windows. Before the fix, 7.8% of cells had no confidence. Test added; the assessment was rerun.
- `tools/discovery/run_pages.py` replaces `run001_pages.py` and writes the dossier pages of any run.
- Report: `docs/wiki/runs/run-002.md`; summary: `docs/VALIDATION.md`.

## 2026-11-19 · T43 First global discovery run, topography (PR #23)
- **Protocol v2** (tag `validation-protocol-v2`, David's decision of 18/11, before run-001). The pilot showed only 10 of 18 negatives masked. The engine now masks the 7 hidden-ground classes (cropland, herbaceous wetland and mangroves added), and the masks check reads 1 km windows. Controls and thresholds are unchanged.
- **run-001:**
  - global 90 m cube with the new masks;
  - screening: 16,520 tiles refined at 40 m and 18,363 at 59.2 m;
  - Antarctic rock outcrops used as the mask south of 60°S;
  - 545 GB of Copernicus GLO-30 downloaded once with 96 connections (3 h);
  - fine stages: 34,834 tiles, 0 failures;
  - 6.7 M cells assessed.
- **Validation:**
  - no positive controls exist for A and B;
  - negatives in the top 10%: 0 of 18 (pass);
  - masks: 17 of 18 (fail);
  - self-consistency: 4 of 5 targets (pits fail);
  - rebuild: identical (pass).
- **Unfavourable:**
  - 38 of the 40 best zones are explained artefacts (remnants between hidden ground, cells cut by tile edges);
  - the ranking is not robust to NASADEM (top-20 overlap 40 to 45%) or to 30 m (35 to 40%);
  - one plausible place (MacDonnell Ranges area, Australia);
  - two rules are proposed for run-002.
- **Also merged:** the coverage overlay and Data and method panel spec (PR #22, David's clarification of 19/11). Natural Earth was added to the catalogue for the continent bias check.
- Report: `docs/wiki/runs/run-001.md`; summary: `docs/VALIDATION.md`.

## 2026-11-18 · T42 Comparison engine (PR #21)
- New engine `tools/discovery/compare.py`, `compare_run.py`. Per 5 km cell, separate outputs, none averaged with another:
  - similarity per lunar target (two-sided percentile, T23; median, quartiles, share above 0.5);
  - requirements `met` / `failed` / `unknown`;
  - operational suitability;
  - coverage (masked and unknown cover counted apart);
  - confidence;
  - a Monte Carlo rank interval.
- Earth is compared at the scale of each lunar product (40 m, 59.2 m). Persistently lit (5 m) is not comparable.
- Pilot run, scenarios A and B on 13 tiles (5,714 cells):
  - base slope met in 3,801 cells; LRV limit eliminates 538 cells, still shown with their similarity;
  - high-confidence top cells on 37°N 105°E (polar targets) and 25°S 135°E (mare plains), stable in 100% of 500 runs.
- Ranking among high-confidence cells added: a median of a few unmasked windows can be high by chance.
- Earth smoothing, as decided by David: none by default. A 1-pixel smoothing lowers Earth slopes by 17 to 18%, keeps the order (Spearman 0.92 to 0.93), but changes a quarter to half of the top decile.
- Held-out lunar blocks: mean typicality 0.4996, KS 0.005. `docs/METHOD.md` has a short section on the engine. Report: `docs/wiki/runs/compare-pilot.md`.

## 2026-11-18 · T41 Lunar profiles (PR #20)
- All 8 lunar environments of T20 computed with the Earth window code; profiles in `data/profiles/moon/`, every selected window kept in Parquet with its hash.
- v2 anchor reproduced exactly (71,731 windows, same percentiles).
- New lunar window cube: SLDEM2015, 60°S to 60°N, 32.3 M windows of 1 km, each with Lunar Prospector FeO and its geologic unit.
- Median `slope_mean`:
  - mare plains 2.25° (5.7 M windows), fresh craters 7.52°, degraded highlands 8.24°;
  - polar lit highlands 8.33°, shadowed regions 9.49°;
  - persistently lit ridges 4.35° (100 m windows at 5 m);
  - 278 atlas pits, 229 of them in Copernican crater units.
- Fresh craters and degraded highlands now ready (geologic map verified in T14). The mare rule uses the map; the iron split (11.44 wt% FeO) is a sensitivity run.
- Effective resolution: LOLA 40 m and the 5 m mosaic give the same slopes (ratio 1.006). Matching Earth to the LOLA spectrum would lower Earth slopes by 12 to 31%, so no smoothing by default; decision for David.
- Report: `docs/wiki/runs/moon-profiles.md`.

## 2026-11-18 · T14 Catalogue coverage review (PR #19)
- David's request: review Earth, Moon and Mars sources for the widest reliable coverage. Review: `docs/wiki/data/coverage-review.md`.
- Added: Antarctic rock outcrops (mask south of 60°S, where WorldCover has no tile) and GeoMAP geology of Antarctica; FABDEM (forest and buildings removed) to check slopes; MOCAAS aqueous minerals of Mars; CaSSIS chloride candidates and the Osterloo chloride deposits; Kaguya MI mineral maps of the Moon.
- Verified from pages David read in a browser (hosts refuse automated reading): geologic maps of the Moon and Mars, Kaguya MI, CaSSIS chlorides, Global Aridity Index (moved to v3.1: v3.0 is deprecated for a dry bias). THEMIS thermal inertia: the page returns 404, still not verified.
- Parameters: `lithology_class` uses GeoMAP on Earth; `mineral_class` uses MOCAAS on Mars and Kaguya MI on the Moon (which had no mineralogy source). FABDEM and MOCAAS licences approved by David (non-commercial project).

## 2026-11-18 · T40 Earth feature cube, topography (PR #18)
- Gate G3 signed by David (18/11); ADR-001 to 009 accepted.
- New package `tools/discovery/`: vectorised 1 km window metrics, 5 km cell statistics (n, valid fraction, p5 to p95, sigma, state), one local equal-area grid per tile with each window owned once, WorldCover 2021 mask fractions, content keys from source signals (ETag, size, date, SHA-256) and a code version hashed from the sources.
- Measured:
  - global 90 m stage: 26,475 tiles in 1.05 h; cells 80.7% evaluated, 1.2% partial, 18.1% missing (water, sea or ice outside WorldCover, and only 258 land cells);
  - fine stage 40 m: 903 tiles/h, about 29 h for the Earth, under the 72 h stop rule;
  - sizes: GLO-30 0.589 TB, GLO-90 0.071 TB (T22 had estimated 0.96 and 0.14 TB);
  - GLO-90 matches GLO-30 at 90 m: Spearman 0.9997, median slope ratio 0.978;
  - the v2 anchor (37 sites) is reproduced within 0.0015.
- Fixed during the run: Antarctica had an ice fraction of 0 where WorldCover has no data (now unknown); the provenance commit is read once per run. WorldCover coverage corrected to 60°S to 84°N in the catalogue.
- Report: `docs/wiki/runs/earth-cube.md`.

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
