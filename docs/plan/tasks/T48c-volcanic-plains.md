# T48c Mars volcanic plains (R5, protocol mars-v3)

Read first: `CLAUDE.md`, `docs/plan/README.md`, [T48](T48-mars.md), `docs/VALIDATION_PROTOCOL.md` (mars-v3), [methods/mars](../../wiki/methods/mars.md). Branch: `feat/T48c-volcanic-plains`.

## Goal
Add the fourth target of scenario D, the volcanic plains, now that David has downloaded the Tanaka et al. 2014 map (24/11/2026). It is the only Mars target with verified positive controls (R29).

## Decisions (David, 24/11/2026)
- **Units:** all 11 units that the map itself describes as volcanic. The run without the 3 edifices is a sensitivity test.
- **Protocol mars-v3:** frozen and tagged before the run; every threshold unchanged; new run run-mars-002, with run-mars-001 kept.

## Steps (TDD)
1. Map reader and unit rule (`tools/discovery/mars_geology.py`). Profile from the 16 global MOLA tiles (`mars.py --only volcanic`).
2. Positive control check (`validate_run.py positives`), with the protocol rule and missing values left out.
3. Geology context E20 (`geology.py`, group `mars-volcanic`).
4. Freeze mars-v3. Then run run-mars-002: assess, zones, checks, Monte Carlo, geology, context, release, tiles, names.
5. Interface: the volcanic plains mission is no longer "soon". Same design, French and English texts.
6. Report in `docs/wiki/runs/run-mars-002.md`, including:
   - the positive controls;
   - unexpected candidates;
   - the observed-share sensitivity.

## Done when
The volcanic plains layer and zones are served and displayed. The positive controls are reported with their pass or fail. The report is in `docs/wiki/runs/`.
