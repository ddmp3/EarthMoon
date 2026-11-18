# T48 Mars profiles and discovery

Read first: `CLAUDE.md`, `docs/plan/README.md` sections 1 to 3, `data/catalog/mars.yaml` (T11), `data/profiles/spec/mars-*.yaml` (T20), `docs/SCENARIOS.md` scenario D (T24), and the ADRs. Branch: `feat/T48-mars`.

## Goal
Compute the Mars environment profiles and run discovery for scenario D with its own parameters, requirements and validation controls.

## Context
- Mars is analysed on its own terms (mission rule): atmosphere, dust, aeolian processes, past water, ice and sediments. Lunar criteria are never reused by changing weights.
- The interface already shows a "Mars: next phase" toggle on the home page (`apps/web/src/components/Home.tsx`).

## Steps (TDD)
1. Regression and analytic tests for the Mars feature code (the same terrain functions applied to MOLA, HRSC or CTX grids).
2. Compute the profiles, with the effective-resolution handling decided in T22.
3. Run discovery with scenario D's controls (frozen in T25 or in a new protocol version made before the run). Report as in T43, including unexpected candidates.
4. Interface: activate the Mars toggle, using the same layer components as T45.

## Done when
The Mars layers and zones are served, displayed and validated, and the report is in `docs/wiki/runs/`.
