# T49 v3 validation report and limits

Read first: `CLAUDE.md`, `docs/plan/README.md` sections 1 to 3, `docs/VALIDATION_PROTOCOL.md`, all `docs/wiki/runs/*.md`, and `docs/wiki/v2/SCIENTIFIC_VALIDATION.md` (the v2 evaluation grid, 13 criteria, v1 15/39, v2 28/39). Branch: `docs/T49-validation`.

## Goal
One honest report of what v3 achieves, measured with the same grid as v2 plus the new criteria (discovery, multi-scale, Mars, mapping), and an updated list of limits and expert decisions.

## Steps
1. Re-score the 13 v2 criteria with their rubric, and add criteria for:
   - global coverage;
   - multi-scale comparison;
   - separation of similarity and suitability;
   - Mars;
   - map honesty (the four states).
   Counted indicators are computed by a script (extend `tools/validation/science_grid.py`). Judged ones state who judged them.
2. Summarize the protocol results per scenario. Unfavourable results come first.
3. Update `docs/LIMITS.md`:
   - what results do not mean;
   - what Earth cannot reproduce (gravity, vacuum, Mars atmosphere, radiation, space weathering of regolith);
   - the comparability classes;
   - the open expert decisions.

## Done when
`docs/VALIDATION.md` is at most 3 pages, with the details in the wiki. Gate G5: David signs.
