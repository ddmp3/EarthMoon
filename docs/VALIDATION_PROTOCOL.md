# Validation protocol v2 (frozen before run-001)

v1 was frozen with the git tag `validation-protocol-v1` before T43. v2 is frozen with the tag `validation-protocol-v2`, also before the first global run (run-001). Any change after a tag creates a new version, with its reason, and is reported next to the results. Results are never retuned to pass.

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
