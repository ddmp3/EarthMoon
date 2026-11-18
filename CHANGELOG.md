# Changelog

One entry per merged task. Newest first. Each entry gives the PR, what changed, and the measured effect where there is one.

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
