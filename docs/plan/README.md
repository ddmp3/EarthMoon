# EarthMoon v3 plan: from ranking known sites to discovering analogs

Owner: David (project lead, validates each gate). Executor: Claude, one task per session or less. Started 17 November 2026.

## 1. Context (read once per session)

**The challenge** (NASA Space Apps 2026, "Identify Earth Locations that Analog the Permanent Moon Base Locations and Mars", PDFs at repository root): use open Earth, Moon and Mars data to identify and characterize **new** terrestrial analogs, anywhere on Earth, explain what is analogous and what is not, at the right scale, and present it as a map or tool. "The goal is not simply to rediscover well-known analog sites."

**Where the project is (v2, merged 17 Nov 2026, PR #1).** A Node/TypeScript API scores 37 hand-picked Earth points against the lunar south polar cap (LOLA 40 m terrain, 71,731 windows of 1 km), for 3 scenarios (rover mobility, instrument calibration, colony). It is honest and reproducible: a frozen data set with value, sigma and flags per value (`data/dataset-v2.json`, SHA-256 of inputs), criteria with role and basis, hard requirements, coverage, Monte Carlo, per-site explanation, Python scorer identical to the API. Read `docs/SCIENTIFIC_*.md` for the details.

**Why v3.** v2 can only rank the 37 points it is given; the candidate list decides the result. Diagnosis of 17 Nov 2026 (phase 1 audit), findings to fix:

| # | Finding |
|---|---|
| L1 | Robotics criteria are redundant: on the 37 sites `slope_mean` vs `roughness_detrended` r = 0.91, vs `traversable_15` r = -0.95 |
| L2 | Comparison is per parameter; the joint lunar distribution is ignored |
| L3 | Same 40 m grid is not the same effective resolution: LOLA polar grids are interpolated between tracks, Copernicus is not. Possible bias, not quantified |
| L4 | Similarity, operational suitability and proxies are averaged into one total; calibration and colony have 0% lunar basis |
| L5 | Climate data at 50 km and one MODIS pixel cannot support fine discovery; Earth and Moon temperatures are not comparable in absolute terms |
| L6 | Validation is circular; a global search will produce false positives that must be measured |
| L7 | Montréal presentation in `docs/` still states v1 claims |
| L8 | Unverified references (NTRS rover limits, Moriarty and Petro, R9, R10, R32 and R37 titles) |
| L9 | Lapse-rate correction applied to minimum temperature, where inversions dominate |
| L10 | Lunar side only has terrain shape: no Diviner, composition, hydrogen, illumination, radar |
| L11 | No Mars at all |

Reusable as is: `tools/precompute/terrain_metrics.py` (any grid), the value/sigma/flags format, versioning and hashes, the `assess` engine, Monte Carlo, explanations, Python/TS parity. Reusable as design input only: `tools/analog_backend` (grid prototype, never run on real data).

## 2. Decisions taken by David (17 Nov 2026)

- The interface may change, under the quality rules of section 3.
- Order: lunar profiles, then global discovery on topography, then lithology, then other dimensions, then Mars.
- **Missing data is shown, never hidden**: regions or sites with partial or missing data are labelled as such, and map areas where one or more criteria have no data are **hatched in a soft pastel colour**, so that comparisons stay honest.
- Caching: preset scenarios use precomputed layers with a simple refresh command; custom criteria are computed on demand (see task T30 for the reproducibility constraint).
- An AI assistant for scientists is an option for later (task T51), not now.
- The project is rebuilt for demonstrated scientific value. All docs are rewritten short; detail goes to `docs/wiki/`.
- The GitHub wiki is enabled (17 Nov 2026). Source of truth: `docs/wiki/` in the repository (versioned, reviewed in PRs). A script (`tools/docs/publish_wiki.py`, T02) mirrors it to the GitHub wiki for reading. Never edit the GitHub wiki by hand: edits there would be overwritten.

## 3. Rules for every task

**Safety**
- Never deploy to Azure, never run `infra/terraform/deploy.sh`, `terraform apply`, `az`. Local Docker only.
- Never touch `ddmp3/nasa-space-app-challenge-2026-cyber-space`.

**Quality gate (`tools/check.sh`, created by T01; must pass before every merge)**
- API: `tsc --noEmit`, vitest. Web: `tsc -b`, `oxlint`, unit tests, `vite build`. Python: pytest.
- Security: production dependencies have 0 vulnerabilities, no exception (`npm audit --omit=dev`). Development dependencies: every advisory must be in `tools/security/audit-allowlist.json` with a reason and a review date (allowed only if no patch exists, it does not reach production and is not exploitable in our use). Python: `pip-audit` on the installed environment, 0. New dependency: exact version, maintained, no known CVE, justified in the PR. To add an npm dependency use `npx npm@11 install --save-exact`, then check that `npm ci` (npm 10) still works.
- CI: `.github/workflows/check.yml` runs `tools/check.sh all` on every pull request (no secrets, no deployment).
- Docker: `docker compose up --build`, then `tools/validation/e2e.py` and `tools/validation/ui-audit/audit.mjs` (desktop and phone).
- TDD: write the failing test first. No regression: existing tests keep passing unless the PR explains why a result changed.

**Science**
- No invented data, resolution, availability or reference. A fact about a data set is checked at its source page and the URL is recorded. Otherwise it is written "not verified".
- Results never depend on the list of expected sites. Known analogs are used only for validation, fixed before results are seen.
- Missing is not bad. Proxy is never presented as a measurement. Similarity is never presented as equivalence.
- No weight without sensitivity analysis. No two parameters measuring the same property without a stated reason.
- Every computed product records its inputs (with SHA-256), code version and parameters.

**History (decision 6.2)**
- One branch per task: `feat/T<nn>-<short-name>` (or `docs/`, `fix/`).
- PR description: what, why, files, tests run with their output, scientific effect, risks.
- Merge with a merge commit (keeps the task history). Then update the status table below and `CHANGELOG.md`.
- Commit messages: `feat: …`, `fix: …`, `test: …`, `docs: …`, `refactor: …`, `chore: …`.

**Documentation**
- Short, for humans. One page per topic in `docs/`; long material (data inventories, experiments) in `docs/wiki/`.
- Update the docs a task touches in the same PR.

## 4. Gates (David signs off)

| Gate | After | David checks |
|---|---|---|
| G1 | T10 to T13 | The data inventories are credible and the sources are the right ones |
| G2 | T20 to T26 | The methodology (profiles, scales, metrics, scenarios, validation) before any engine code |
| G3 | T30 | The architecture and the caching choice |
| G4 | T43 | The first discovery map (topography) and its validation report |
| G5 | T49 | The v3 validation report before release |

No task after a gate starts before the gate is signed (write "G1 signed DD/MM by David" in the table).

## 5. Tasks and status

Status: `todo`, `doing`, `done (PR #n)`, `blocked (reason)`.

| Task | Title | Depends on | Status |
|---|---|---|---|
| [T01](tasks/T01-quality-harness.md) | Quality harness and non-regression baseline | – | done (PR #3) |
| [T02](tasks/T02-docs-reset.md) | Docs reset: short README, wiki, history | T01 | done (PR #4; wiki publication waits for a first "Home" page on GitHub) |
| [T10](tasks/T10-moon-data.md) | Lunar data inventory | T01 | done (PR #5; 9 products need a browser check before G1) |
| [T11](tasks/T11-mars-data.md) | Mars data inventory | T01 | done (PR #6; 8 products need a browser check before G1) |
| [T12](tasks/T12-earth-data.md) | Earth data inventory | T01 | done (PR #7; 6 products need a browser check before G1) |
| [T13](tasks/T13-references.md) | Reference verification | T01 | done (PR #8; VIPER 15° and Lunar Sourcebook still unverified) |
| G1 | Gate: data inventories | T10-T13 | G1 signed 18/11 by David (unreadable sources stay "not verified") |
| [T20](tasks/T20-planetary-profiles.md) | Planetary environment profiles | G1 | done (PR #9; 6 lunar and 5 Martian ready specs, 5 conditional) |
| [T21](tasks/T21-dimensions.md) | Dimensions, parameters, redundancy | G1 | done (PR #10; terrain metrics reduce to slope; detrended roughness differs between bodies) |
| [T22](tasks/T22-sampling.md) | Spatial and statistical sampling | T20, T21 | done (PR #11; same-pixel comparison, 5 km equal-area cells, 2-stage search with 0.17% misses) |
| [T23](tasks/T23-comparison.md) | Comparison methods benchmark | T22 | done (PR #12; two-sided percentile per parameter; minimum across dimensions) |
| [T24](tasks/T24-scenarios.md) | Scenarios v3 (A base, B robotics, C instruments, D Mars) | T21 | done (PR #13; 4 scenarios, 7 instruments, E13 to E16 added) |
| [T25](tasks/T25-validation-protocol.md) | Uncertainty and independent validation protocol | T23, T24 | todo |
| [T26](tasks/T26-mapping.md) | Mapping methodology | T23 | todo |
| G2 | Gate: methodology | T20-T26 | todo |
| [T30](tasks/T30-architecture.md) | Target architecture and ADRs | G2 | todo |
| G3 | Gate: architecture | T30 | todo |
| [T40](tasks/T40-earth-feature-cube.md) | Earth feature cube, topography | G3 | todo |
| [T41](tasks/T41-moon-profiles.md) | Lunar profiles computed | G3 | todo |
| [T42](tasks/T42-comparison-engine.md) | Comparison engine | T40, T41 | todo |
| [T43](tasks/T43-discovery-topography.md) | First global discovery run and validation | T42 | todo |
| G4 | Gate: first discovery map | T43 | todo |
| [T44](tasks/T44-api-layers.md) | API: layers and zones | G4 | todo |
| [T45](tasks/T45-ui-map.md) | Interface: layer map, hatching, comparison | T44 | todo |
| [T46](tasks/T46-geology.md) | Geology and mineralogy dimension | G4 | todo |
| [T47](tasks/T47-thermal-hydric.md) | Thermal, ice and hydric dimensions | G4 | todo |
| [T48](tasks/T48-mars.md) | Mars profiles and discovery | T46, T47 | todo |
| [T49](tasks/T49-validation-report.md) | v3 validation report and limits | T45-T48 | todo |
| G5 | Gate: release | T49 | todo |
| [T50](tasks/T50-release.md) | Docs, release notes, v2 retirement decision | G5 | todo |
| [T51](tasks/T51-assistant.md) | AI assistant for scientists (optional) | T50 | todo |

## 6. Tooling

- Run Node and Python through Docker so no host install is needed: `tools/check.sh` (T01) does it. If a host Node is needed, use Node 22 LTS installed under `C:\Users\david\tools\node` (not the session scratchpad, which is erased).
- Python on host: `python` 3.11. Run scripts that read downloaded files with `python -I`.
- Large downloads go to `C:\Users\david\earthmoon-data\` (outside the repo, never committed). Only small derived products and manifests (with SHA-256) are committed.
- The Windows mount truncates or pads large files written in quick succession (see `_dev.project/CLAUDE.md`): after writing a large script, check its tail.
