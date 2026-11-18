# T23 Comparison methods benchmark

Read first: `CLAUDE.md`, `docs/plan/README.md` sections 1 to 3, `docs/wiki/methods/sampling.md` and `docs/wiki/methods/parameters.md`. Branch: `feat/T23-comparison`.

## Goal
Choose, with evidence, how a terrestrial cell or zone is compared with a planetary environment, dimension by dimension. No algorithm is imposed without demonstrated value.

## Context
- **v2 method:** score 1 inside the lunar interquartile range, decreasing linearly to 0 at p5 and p95, applied to each parameter separately; then a weighted mean (`apps/api/src/scoring/score.ts`). Finding L2: this ignores the joint distribution.
- **Prototype ideas** in `tools/analog_backend/analog_finder/p5_similarity.py`:
  - z-score against a lunar reference;
  - quantile matching within each planet for thermal values;
  - percentile of an Earth cell among lunar cells;
  - Dirichlet weight robustness.
  Never run on real data.
- Required separation (axis 6): similarity, scientific relevance, operational suitability, eliminating constraints, and confidence are separate outputs. A good similarity never offsets an operational impossibility.

## Candidates
1. The v2 interval method (baseline).
2. The two-sided percentile of the Earth value within the planetary distribution.
3. Robust Mahalanobis distance to the planetary profile (robust covariance), expressed as the share of planetary windows that are farther away: "more typical than X% of lunar windows".
4. Nearest-neighbour or density-ratio distance to the planetary windows.
5. Distribution distances between the windows inside an Earth zone and the planetary windows: Wasserstein in 1D, energy distance in several dimensions.
6. PCA and clustering, for exploration and explanation only, not for scoring, unless the benchmark shows a gain.

## Benchmark protocol (write it before running anything)
- **Self-consistency:** held-out planetary windows must score as planetary. This gives a calibrated scale.
- **Discrimination:** planetary windows against a seeded random sample of Earth cells (AUC), per dimension.
- **Robustness:** missing dimensions, data noise (sigma), resolution change (T22 experiments).
- **Interpretability:** can each score be explained per parameter?
- **Cost:** time per million cells.
- Known analog sites are **not** used here (they belong to validation in T25).

## Steps
Implement the candidates in `tools/research/compare_*.py` with analytic tests (identical distributions give a perfect score, shifted ones a known score). Run the benchmark on the lunar south polar profile and the pilot tiles. Report the results in `docs/wiki/methods/comparison.md`, then choose one method per dimension. Then define:
- how dimensions are reported (always separately);
- whether a global similarity is shown, with which aggregation (for example a minimum or a geometric mean, not compensating), and its sensitivity analysis.

## Done when
Every candidate is either chosen or rejected with numbers.
