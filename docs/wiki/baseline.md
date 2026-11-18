# Quality baseline (T01, 18 November 2026)

Reference state that every later task is compared with. Produced by `tools/check.sh all` on branch `feat/T01-quality-harness` (from `main` at `ee16216`), Docker Desktop 28.5.1 on Windows.

## Results

| Stage | Result |
|---|---|
| API | `tsc --noEmit` clean (strict); vitest **154 passed**; gate self-test 6 passed |
| Web | API contract in sync; `tsc -b` clean (strict, enabled in T01: 0 errors); oxlint 0 warnings, 0 errors; vitest **13 passed** (new); `vite build` OK, bundle 417 KB |
| Python | pytest **55 passed** (precompute, scoring, validation) plus 1 (analog_backend prototype) |
| Dependencies | production: **0 vulnerabilities** (API and web); development: 1 advisory, allowlisted (below); Python environment: 0 after upgrading the image's setuptools and wheel |
| Docker e2e | **15/15** (`tools/validation/e2e.py`) |
| Browser audit | **0 defects**, desktop and phone (`tools/validation/ui-audit/audit.mjs`) |

## Found and fixed in T01

| Finding | Fix | Test |
|---|---|---|
| A missing value was displayed as a 0% match in the scorecard, and at the centre (score 0) of the radar chart | Missing value shows "—" with a pastel hatched bar; radar draws no point and a dashed axis for it | `SiteDetail.test.tsx`, `Radar.test.tsx` |
| `apps/web/src/api-schema.ts` was not regenerated after the v2 contract change | Regenerated; `check.sh web` fails if it drifts again | gate step |
| The 8 parameters added by v2 had no label in the interface (raw ids shown) | English and French labels and help texts | `api.test.ts`, compile-time check in `api.ts` |
| Home page stated "18 parameters" (hard-coded) | Count taken from the catalogue (26) | `Home.test.tsx` |
| Web TypeScript was not in strict mode | Enabled (no error found) | `tsc -b` |
| Old setuptools and wheel in the Python base image (8 advisories) | Upgraded in the check environment | `pip-audit` |

## Accepted, with review date

- **GHSA-fc5q-39xc-vjpf, picomatch ≤ 4.0.7 (ReDoS), high.** No patched version exists. Reached only through vite and vitest (build and test tools), with our own glob patterns. Absent from the production images. Allowlisted until 2026-12-17 in `tools/security/audit-allowlist.json`.

## Known gaps, not fixed here

| Gap | Where it will be handled |
|---|---|
| Dockerfiles use floating tags (`node:22-slim`, `nginx:1.27-alpine`): the same commit can build different images | T30 (architecture) or a small fix PR |
| Python `requirements.txt` use `>=` and there is no lock file | T30 / T40, when the discovery pipeline gets its own dependencies |
| `npm ci` is done with npm 10 but adding vitest needed npm 11 (npm 10 crashes with `edgesOut` on vitest's peer set) | Add dependencies with `npx npm@11 install`, then check that `npm ci` works under npm 10 (the gate does) |
| Radar labels close to the frame edge on long names | T45 |
| Scorecard cites `docs/scenarios.md` as a source text | T02 (docs move) |
