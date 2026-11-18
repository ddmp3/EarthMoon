# T42 Comparison engine

Read first: `CLAUDE.md`, `docs/plan/README.md` sections 1 to 3, `docs/wiki/methods/comparison.md` (T23), `data/scenarios/*.yaml` (T24) and the ADRs (T30). Branch: `feat/T42-compare`.

## Goal
Implement the comparison methods chosen in T23, with separate outputs per cell or zone:
- similarity per dimension;
- operational suitability;
- requirements (`met`, `failed`, `unknown`);
- coverage;
- confidence.

## Context
- **Keep the v2 semantics:**
  - a missing value counts neither for nor against a cell;
  - coverage and bounds are reported;
  - a failed requirement is never averaged away;
  - the explanation only reorders what the assessment contains (`apps/api/src/scoring/score.ts`, `apps/api/src/analyze/explain.ts`).
- The Monte Carlo is extended as in `docs/VALIDATION_PROTOCOL.md` (T25).
- **Parity rule:** if both Python and TypeScript compute something, a test checks identical results on the real data (as in v2, `apps/api/tests/methodology.test.ts`).

## Steps (TDD)
1. Analytic tests per method (from T23).
2. Planetary self-consistency test (held-out windows).
3. Test that a failed requirement keeps the similarity values visible and is never offset by them.
4. Monte Carlo test: same seed, same output.
5. Implement in `tools/discovery/compare/`. Keep the v2 API engine working unchanged (its tests must still pass).

## Done when
- The engine runs on the pilot tiles for scenarios A and B and produces all outputs.
- Checks pass, and `docs/METHOD.md` gets a short section describing the new engine.

## Alignment with the ADRs (T30)
Every v3 number is computed once, in Python (`tools/discovery/compare` and `zones`, ADR-005), so no TypeScript port is needed. The parity rule above applies to v2 only, as long as v2 is served.
