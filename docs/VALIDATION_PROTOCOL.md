# Validation protocol v3 (frozen before run-002)

v1 was frozen with the git tag `validation-protocol-v1` before T43, v2 with `validation-protocol-v2` before run-001, v3 with `validation-protocol-v3` before run-002. Any change after a tag creates a new version, with its reason, and is reported next to the results. Results are never retuned to pass.

## Mars: protocol mars-v2 (decided by David on 23/11/2026, frozen before its Monte Carlo)

**Why.** The run-mars-001 Monte Carlo (mars-v1) kept the lunar slope noise of 0.5°, and no zone stayed stable. At the MOLA scale, Martian slopes are very low (median 0.7 to 0.8°), so a 0.5° noise is as wide as most of the reference. That value was set for 1 km lunar windows, not derived for these scales.

**What changes: only the Monte Carlo noise.** At each scale, the noise is measured from the stated DEM error (`tools/discovery/slope_noise.py`, rule written before measuring):
- **Elevation error:** independent Gaussian at the comparison pixel, with sigma 1.216 m (Copernicus DEM relative vertical accuracy, 2 m LE90 for slopes up to 20%).
- **Noise value:** the root mean square of the change of the window mean slope, bias included.
- **Sample:** 30 land tiles (seed 20261119), 3 draws each, rounded up to 0.01°.
- **Result** (`data/runs/run-mars-001/slope-noise.json`):
  - **0.25°** at 115.77 m (polar targets), over 70,797 windows;
  - **0.04°** at 463.08 m (ice-rich target), over 6,792 windows.
- **Why independent errors are conservative:** the 90 m source errors are averaged when resampled to these pixels.

**Unchanged:** everything else in mars-v1, the cells, zones and every other check of run-mars-001. The mars-v1 Monte Carlo results are kept and reported next to the mars-v2 ones.

## Mars: protocol mars-v1 (frozen before run-mars-001, 20/11/2026)

Scenario D, phase 1 targets: north polar terrain, south polar terrain, ice-rich mid-latitudes ([methods/mars](wiki/methods/mars.md)). It is v3 with the changes below; code in `tools/discovery/mars_run.py`.

**Why it differs.** Mars windows are 25 × 25 MOLA pixels (E19):
- 2.9 km at the poles (Earth at 115.77 m, a quarter of the 463.08 m pixel; the polar MOLA grid is 115.09 m, 0.6% finer);
- 11.6 km elsewhere (Earth at 463.08 m).

A 5 km cell holds at most a few such windows, so the count rule of v3 (20 valid windows) could never be met.

**What changes:**
- **Every Earth tile is assessed.** There is no screening stage at these scales.
- **Window assignment.** A window belongs to the cell that holds its centre, and also to every cell whose centre it holds. Cells under one large window share its value. A zone therefore counts more cells than independent windows, and the report gives both.
- **Confidence** uses the v3 rule written as shares: high when at least 80% of the cell's windows are valid and unmasked, and under 10% are masked or of unknown cover; medium when at least half are valid.
- **No requirement and no suitability.**
  - The lunar rover limits are never reused.
  - The MSL limits of scenario D (R43) apply at rover scale, far below these windows (E14).
- **The masks check** reads the 2.9 km window that holds each negative point.
- **Self-consistency** holds out checkerboard blocks of 5 windows: 14.5 km at the poles, 58 km elsewhere.
- **Antarctic rock sample:** spread over 0.4 of a window, as for the 1 km lunar windows (400 m).

**Unchanged:**
- the 5 km HEALPix cells, the masks and τ;
- the minimum zone size;
- the 18 negatives and every pass threshold;
- the Monte Carlo (500 runs, seed 20261119, 0.5° slope noise), the bias checks and the dossiers.

**Positives:** none for these targets. The verified controls of scenario D (R29) are volcanic plains, which wait for the Mars geologic map (Tanaka et al. 2014). Phase 1 therefore has **no positive validation**.

## Changes from v2 to v3 (19/11/2026, decided by David when signing G4)

**Why.** The dossiers of run-001 found 38 of its 40 top zones to be artefacts:
- **15 were tile-edge fragments.** Each 1° tile cut its own 5 km cells, so a cell on a tile edge was split into two thin parts with few windows.
- **23 were remnants between hidden ground.** Cells with few unmasked windows ranked as high as cells with many.

**What changed:**
- **One global grid of 5 km cells.** Cells are cells of HEALPix (RING, NSIDE 1303: 25.04 km², the same size at every latitude and a compact shape near the poles), not squares of each tile's projection. A cell that straddles tiles is one cell with the windows of all of them; it is assessed once, by the tile that holds its centre. Zones join cells that are HEALPix neighbours.
  - The task first named EASE-Grid 2.0 (EPSG:6933). It was replaced before the tag: its cells are equal-area too, but near the poles they become strips (about 1 km × 25 km at 80°S), and several targets are polar.
- **Candidates must have high confidence:** at least 20 valid windows, and less than 10% of masked windows or of windows of unknown cover. Zones are made of, and ranked on, these cells only.

**Unchanged:** the windows (the run-001 cubes), the masks, every metric, τ and the minimum zone size, the controls and every pass threshold.

**Consequence:** run-001 results are v2 results. They are reported next to run-002, not replaced.

## Changes from v1 to v2 (18/11/2026, decided by David)

**Why.** Running the checks on the 13 pilot tiles before run-001 showed that only 10 of 18 negative controls were masked or flagged. Two causes:
- **The engine masked 4 WorldCover classes** (tree, built-up, water, snow and ice). The protocol's own negatives are drawn in 6 classes where the ground is hidden: cropland, herbaceous wetland and mangroves were never masked. That is an implementation defect against the protocol's definition, not a threshold to tune.
- **The check looked at the 5 km cell, not the masked unit.** A built-up point at a town edge sat in a cell with 6% built-up cover. The engine masks 1 km windows.

**What changed:**
- **The engine masks 7 classes:** tree, cropland, built-up, snow and ice, water, herbaceous wetland and mangroves. The Earth cubes are recomputed with the fractions of all 7.
- **The masks check reads the 1 km window that holds each negative point** (90 m cube), the unit the engine masks.

**Unchanged:** the controls (`data/validation/` is identical to v1), every metric and every pass threshold.

**Consequence:** the pilot result of 10 of 18 is a v1 result. It is reported, not hidden.

## 1. Controls

**Positive controls** (`data/validation/positives.yaml`). A place qualifies only if:
- it is named in the title or abstract of a reference verified in [REFERENCES.md](REFERENCES.md);
- that text describes it as an analog site, or a test site, for the scenario's function;
- a public gazetteer locates it by name.

Applying the rule gives:

| Scenario | Controls | Source |
|---|---|---|
| D Mars (volcanic geology) | Big Craters (Idaho), Mauna Ulu, Kīlauea Iki, Kīlauea caldera (Hawaiʻi) | R29 |
| C4 Radar | Skull Cave, Valentine Cave (Lava Beds, California) | R25 |
| A, B, other C instruments | **none**: no verified reference names a site | — |

A scenario with fewer than 3 positives has **no positive validation**, and its results say so. The v2 team list (`known_for`) is not used: the same team wrote the model (L6). An independent list stays expert decision E10.

**Negative controls** (`data/validation/negatives.yaml`, made by `tools/research/controls.py`):
- 18 points, drawn uniformly on the sphere with seed 20261119, kept in draw order;
- 3 points each in ESA WorldCover 2021 classes where the ground is hidden: tree cover, cropland, built-up, permanent inland water, herbaceous wetland, mangroves;
- the same set is used for every scenario.

## 2. Metrics and pass thresholds (fixed now)

| Metric | Pass |
|---|---|
| Planetary self-consistency: held-out windows of the target profile (T23) | Kolmogorov–Smirnov distance to uniform ≤ 0.05 |
| Positives: percentile of each control cell among all evaluated cells, per dimension | Median ≥ 75th percentile; also report the share in the top 10% |
| Negatives, after masks | At most 1 of 18 in the top 10% of any scenario |
| Masks | All 18 negatives masked or flagged "ground hidden" |
| Reproducibility | A rebuild from the manifests gives identical SHA-256 |

**Why the masks test matters.** Slope alone can match under a forest. The negatives check that masks remove hidden ground; they do not check that slope is wrong there.

## 3. Uncertainty (Monte Carlo, seed 20261119, 500 runs)

**Varied:**
- data sigma per value;
- pixel scale (T22: the planetary pixel against 30 m);
- metric (two-sided percentile against the interval score of T23);
- requirement thresholds within their stated ranges (for example 20 to 25° for the LRV);
- profile boundaries, through each sensitivity grid of the T20 specs.

**Reported:** the rank interval of each zone, and the share of runs in which a zone stays above the 90th percentile.

**Not covered** (stated with every result):
- spatially correlated DEM errors;
- the effective-resolution bias until T41;
- the boundaries of the conditional environments;
- errors in the planetary products themselves beyond their stated uncertainty.

## 4. Bias checks

- Coverage and results by latitude band (every 10°) and by continent, as equal-area counts.
- Dependence on a single source: every terrain value comes from Copernicus; NASADEM (60°N to 56°S) is recomputed on the top 100 zones.
- Resolution: the top zones are recomputed at 30 m against the planetary pixel, and rank changes are reported.

## 5. Unexpected candidates

The top 20 zones per scenario that are in no control list each get a short dossier:
- data values with spread;
- imagery;
- a literature search, recording the queries used.

Each gets one outcome: **plausible**, **explained artefact** (for example edited water, a DEM void, a quarry) or **unknown**. Artefacts are reported and fixed by a rule applied everywhere, never by removing a zone by hand.

## 6. What this protocol cannot show

- That a zone is a good analog for a team. Only a field campaign can show that.
- Anything about scenarios A, B and most of C beyond self-consistency and negatives, until verified positive controls exist.
