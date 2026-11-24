# T52b Pre-analysis of updates (no recompute)

Read first: `CLAUDE.md`, `docs/adr/ADR-009-automatic-refresh.md` (with its T52 amendments), `docs/wiki/methods/refresh.md`. Branch: `feat/T52b-impact`. Depends on T52.

## David's decision (24/11/2026)
- **The refresher checks and identifies; it never starts a recompute.**
- **Before any compute**, the volume of an update is analysed: what changed, what it would recompute, and how long it would take.
- **The app will later run on Azure**, where every recompute has a cost. Nothing is deployed now (hard rule while the NASA evaluation runs), but the pre-analysis is built so a cost can be added from machine prices.

## Steps (TDD)
1. **Impact of each detected change**, computed by the refresher without any heavy step. It gives:
   - the source and the items changed, withdrawn or added;
   - the 1° Earth tiles they cover, and the tiles reassessed with their neighbours;
   - the targets and releases concerned;
   - the estimated number of cells;
   - the estimated CPU time, from the measured calibration;
   - a planetary change: its targets only, every tile, no Earth feature.
2. **Shown to users** in `GET /api/v3/status` (`impact`), with its basis ("estimated from the calibration of 23/11/2026").
3. **Recompute command:** later, only on David's decision, from the pre-analysis. The zone rule for publication is fixed then.

## Done when
`tools/check.sh all` passes, and a detected change shows its impact in the status without any compute being started.
