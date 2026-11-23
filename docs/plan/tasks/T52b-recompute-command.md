# T52b Incremental recompute on command

Read first: `CLAUDE.md`, `docs/adr/ADR-009-automatic-refresh.md` (with its T52 amendments), `docs/wiki/methods/refresh.md`. Branch: `feat/T52b-recompute`. Depends on T52.

## Goal
One command recomputes what the refresher detected, and only that. It shows the plan and the estimated time first.

## Steps (TDD)
1. **`plan`**: build the planner world from the run (tile lists, targets and their sources) and the refresher state, then print the dry run.
2. **`run`**, local at every step:
   - features of the changed tiles;
   - assessment of the (tile, target) units;
   - local zones (`zones_local.py`) and the Monte Carlo of the zones touched;
   - cheap checks.
3. **Incremental export:**
   - a new release that shares unchanged files by hard link;
   - only the zones and map tiles that changed are rewritten;
   - `provenance.json` and `changes.json` with the source events;
   - the publication gate, then `refresher.consumed` for the sources used.
4. **Progress:** written to the refresher state, so the status shows `update_in_progress`.
5. **Zone rule:** David decides the replacement for "no zone appears or disappears" (calibration: a one-cell change counts as one zone out and one in).
6. **e2e:** a forced change on a fixture tile shows `update_detected`, then `update_in_progress`, then `up_to_date` once published.

## Done when
`tools/check.sh all` passes with the e2e step, and a forced 10-tile update runs end to end on Mars in minutes, never the whole planet.
