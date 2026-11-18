# T21 Dimensions, parameters and redundancy (design plus measurement)

Read first: `CLAUDE.md`, `docs/plan/README.md` sections 1 to 3, the catalogues `data/catalog/*.yaml`, and `docs/wiki/methods/profiles.md`. Branch: `feat/T21-dimensions`. Gate G1 must be signed.

## Goal
A short list of parameters per dimension. Each parameter has a clear meaning on both bodies and a stated class of comparability. No two parameters measure the same thing without a reason.

## Context
- Dimensions asked by David:
  - topographic and geomorphological;
  - geological and mineralogical;
  - thermal;
  - hydric and ice;
  - environmental (dust, wind, aeolian);
  - operational.
- Finding L1: on the 37 v2 sites, `slope_mean` correlates with `roughness_detrended` (r = 0.91) and with `traversable_15` (r = -0.95). The v2 robotics scenario therefore counts one property three times.
- Comparability classes (mission axis 8):
  - `direct`: same physical quantity, same scale;
  - `indirect`: related quantity, through a stated model;
  - `process`: the same process acts, for example aeolian sorting;
  - `impossible`: gravity, vacuum, radiation, Mars atmosphere;
  - `model`: comparison requires a physical model.

## Steps
1. Build the parameter table. For each parameter give: definition, unit, scale, and source on Earth, the Moon and Mars (catalogue ids). Then its class, the dimensions it serves, and what it does not measure.
2. Measure redundancy on real data. Write `tools/research/redundancy.py` (tested):
   - Spearman and Pearson correlation matrices on the lunar windows (LOLA, from the v2 pipeline) and on a seeded random sample of Earth cells (Copernicus);
   - the same with partial correlations.
   Keep the measured matrices in `docs/wiki/methods/redundancy.md`.
3. Decide, per dimension: keep, merge (for example a PCA axis), or drop. Give the reason and the number behind it.
4. List the properties that cannot be compared and say so in plain words (input to the limits document).

## Done when
- The table covers every dimension. Each kept pair with |r| > 0.8 on either body has a written justification.
- The redundancy script and its tests pass.
- Output: `docs/wiki/methods/parameters.md` and `data/parameters.yaml` (machine-readable catalogue, replacing the v2 catalog in T42 and T44).

## Pitfalls
A correlation across 37 hand-picked sites is not the same as a correlation over Earth. Sample at random.
