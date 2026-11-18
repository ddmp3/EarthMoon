# Changelog

One entry per merged task. Newest first. Each entry gives the PR, what changed, and the measured effect where there is one.

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
