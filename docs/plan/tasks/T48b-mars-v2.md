# T48b Mars protocol mars-v2 (measured Monte Carlo noise)

Read first: `CLAUDE.md`, `docs/VALIDATION_PROTOCOL.md` (mars-v1 and mars-v2), `docs/wiki/runs/run-mars-001.md`. Branch: `feat/T48b-mars-v2`.

## Goal
Rerun the run-mars-001 Monte Carlo with a slope noise measured from the DEM error at each Martian scale, as decided by David on 23/11/2026, instead of the lunar 0.5°.

## Steps (TDD)
1. Measure the noise with a rule written before measuring (`tools/discovery/slope_noise.py`), tag `validation-protocol-mars-v2`.
2. Rerun the Monte Carlo only; keep the mars-v1 results and report both.
3. Export the Mars release under mars-v2.

## Done when
The report gives mars-v1 and mars-v2 side by side, and the Mars release states protocol mars-v2.
