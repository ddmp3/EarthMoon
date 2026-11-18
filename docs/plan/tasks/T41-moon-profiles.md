# T41 Lunar profiles computed

Read first: `CLAUDE.md`, `docs/plan/README.md` sections 1 to 3, `data/profiles/spec/moon-*.yaml` (T20), `data/catalog/moon.yaml` (T10) and the ADRs (T30). Branch: `feat/T41-moon-profiles`. Gate G3 must be signed.

## Goal
Compute every lunar environment profile specified in T20 from primary data, with the same feature code as Earth (T40).

## Context
- v2 computed the south polar distribution from LOLA `LDEM_85S_40M` (71,731 windows of 1 km; SHA-256 starting with `1609e9b8`) in `tools/precompute/lunar_reference_v2.py`.
- Its percentiles (`slope_mean` p5 to p95: 2.95 / 5.23 / 8.31 / 12.89 / 20.89°) are the regression anchor.
- The effective resolution experiment is designed in T20 and decided in T22.

## Steps (TDD)
1. Test: the polar environment, recomputed with the new pipeline, reproduces the v2 percentiles to 0.01.
2. Download the products of each environment (resumable, with hashes). Apply the selection rule of each spec.
3. Compute the full distributions: per-parameter percentiles, the joint data needed by the T23 method, sample counts, and coverage gaps.
4. Run the effective resolution experiment. Apply its correction or comparison scale, as decided in T22.
5. Write `data/profiles/moon/<env>.json`, each with inputs, hashes, code version and parameters.

## Done when
- Every lunar environment of T20 is computed or documented as not computable (with the reason).
- The regression anchor passes, checks pass, and `docs/wiki/runs/moon-profiles.md` summarizes each profile in a few lines.

## Alignment with the ADRs (T30)
Code goes in `tools/discovery/profiles` (ADR-001); outputs carry a run manifest. Run the effective resolution experiment designed in `docs/wiki/methods/profiles.md` (T22 gave a first look: about 5 times less 160 m relief on LOLA).
