# T22 Spatial and statistical sampling (design plus experiments)

Read first: `CLAUDE.md`, `docs/plan/README.md` sections 1 to 3, `docs/wiki/methods/profiles.md` and `docs/wiki/methods/parameters.md`. Branch: `feat/T22-sampling`.

## Goal
Decide how Earth and planetary data are sampled so that comparisons are physically meaningful, and so that a whole-Earth search is feasible on this PC.

## Context
- v2 uses one 1 km window (25 x 25 pixels of 40 m) centred on each site, and the spread of the 3 x 3 neighbouring windows as sigma (`tools/precompute/terrain_metrics.py`, `site_terrain.py`). David: "do not impose one resolution on all data; compare at physical scales, not identical pixel sizes".
- Scales to define: regional (tens of km), local (a few km), site (about 1 km), operational (metres to tens of metres, rover scale), fine (where data allow).
- Discovery must cover all land. 40 m everywhere in one pass is probably not feasible locally: estimate it, do not assume it.

## Steps
1. For each parameter of `data/parameters.yaml`, record:
   - the native resolution and the effective resolution (from the catalogues);
   - the scale or scales at which it is compared, and the reason.
2. Choose the spatial index of the search. Candidates: an equal-area discrete global grid (for example H3), or 1° tiles with a local equal-area projection. Criteria: equal area, multi-scale, tooling, licence. Justify the choice.
3. Define the statistics per cell: distribution summary (median, interquartile range, p5 and p95), valid fraction, edge rules (a minimum valid fraction, coast and water masks). A cell is never represented by one value without its spread.
4. Define the multi-stage search: a coarse global screening, then refinement of the cells that pass. Measure the risk that the screening drops true matches. Test: on pilot tiles, run both stages at full resolution and count the misses.
5. Experiments (`tools/research/sampling_*.py`, tested, seeded):
   - pilot tiles chosen by a stated rule (for example 10 tiles drawn at random with seed 20261117 among land tiles, plus 3 tiles of contrasting terrain types);
   - scale sensitivity: how each metric changes from 30 m to 90 m and from 1 km to 5 km windows;
   - the effective resolution test designed in T20.
6. Compute budget: time and disk per stage, measured on the pilot tiles and extrapolated.

## Done when
`docs/wiki/methods/sampling.md` contains the decisions with their numbers, and the experiments are reproducible from the repository.

## Pitfalls
- 1° tiles are not equal-area: never compare raw cell counts across latitudes.
- Pilot tiles are for engineering, never for tuning similarity thresholds.
