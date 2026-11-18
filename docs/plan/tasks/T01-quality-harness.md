# T01 Quality harness and non-regression baseline

Read first: `CLAUDE.md`, `docs/plan/README.md` sections 1 to 3. Branch: `feat/T01-quality-harness`.

## Goal
One command, `tools/check.sh`, that proves a change breaks nothing: types, lint, tests, dependency vulnerabilities, Docker end-to-end and browser audit. Record today's results as the baseline every later task compares with.

## Context
- API: `apps/api` (Express, TypeScript, vitest, 154 tests). Web: `apps/web` (React 19, Vite, Tailwind, Leaflet, oxlint) has **no unit tests** yet. Python: `tools/precompute`, `tools/scoring`, `tools/validation` (pytest, 55 tests).
- End-to-end: `docker compose up --build` (web http://localhost:8080, API http://localhost:3001), then `python tools/validation/e2e.py` (15 checks).
- Browser audit: `tools/validation/ui-audit/audit.mjs`. It worked in Docker with `mcr.microsoft.com/playwright:v1.64.1-noble` and `--network host`.
- Node is not installed on the host. Run Node through Docker (`node:22-bookworm`) to avoid depending on a session folder.
- David's requirement: secure code (no dependency with a known vulnerability), no TypeScript or other error anywhere on the site, TDD, nothing broken.

## Steps
1. Write `tools/check.sh` (Bash, `set -euo pipefail`). Use stages that can run alone (`check.sh api|web|python|audit|e2e|all`):
   - api: `npm ci`, `npx tsc --noEmit`, `npx vitest run`, `npm audit --audit-level=low`;
   - web: `npm ci`, `npx tsc -b`, `npx oxlint`, `npx vitest run`, `npx vite build`, `npm audit --audit-level=low`;
   - python: `pip install -r` each requirements file, then `pytest` and `pip-audit -r` each requirements file;
   - e2e: compose up, wait for health, `e2e.py`, ui-audit (desktop and phone), compose down.
   Run Node and Python inside containers that mount the repo.
2. Web unit tests, test first: add `vitest`, `@testing-library/react`, `jsdom` (exact versions, check `npm audit`). First tests:
   - Home renders the four missions;
   - Mission renders a ranking from a fixture API response;
   - a criterion with `missing` status is shown as missing, not as 0;
   - FR and EN content files have the same keys.
3. Optional and useful: `.github/workflows/check.yml` running `tools/check.sh` on pull requests. **Test only: no secrets, no deploy step, no Azure login.**
4. Run everything and write `docs/wiki/baseline.md`: date, commit, counts of passed tests per stage, audit results, build warnings, bundle size, e2e and ui-audit results.
5. Fix any failure you find in a separate commit. If a fix changes behaviour, write a test first.

## Done when
`tools/check.sh all` passes on `main` plus this branch; the baseline is recorded; the PR lists the full output summary.

## Pitfalls
- Windows mount: `npm ci` on a mounted volume is slow. Use a named Docker volume for `node_modules`.
- Line endings: keep `check.sh` in LF (`.gitattributes`: `*.sh text eol=lf`).
- Do not "fix" an `npm audit` finding with `--force` if that upgrades a major version without tests.
