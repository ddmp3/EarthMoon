# Comparison methods benchmark (T23)

Code: `tools/research/compare_methods.py`. Output: `data/research/comparison-t23.json`. The protocol below was committed **before** the first run.

## Protocol (fixed before running)

**Reference:** profile `moon-south-polar-cap-v2` (all 1 km windows of LDEM_85S_40M south of 85°S). Split at random (seed 20261119) into a reference half and a held-out half.

**Features.** T21 kept one terrain similarity parameter, so the benchmark uses:
- **1D:** `slope_mean`, 1 km windows at 40 m;
- **2D:** `slope_mean` plus `slope_regional`, the mean slope of the enclosing 5 km window at 200 m pixels. It is a candidate second scale (T22). Its redundancy with `slope_mean` is measured first; if |Spearman| > 0.8 on either body, the 2D results are reported but cannot justify a 2D method.

**Earth samples** (never known analog sites):
- 1D: the 1,410 random land windows of T21 (seed 20261118);
- 1D and 2D: 20,000 windows drawn with seed 20261119 from the 13 T22 pilot tiles, at 40 m.

**Candidates**, each turned into a *typicality* between 0 and 1 (1 = like the median planetary window):
1. v2 interval score: 1 inside p25 to p75, falling linearly to 0 at p5 and p95.
2. Two-sided percentile: 2 × min(F, 1 − F), with F the empirical lunar distribution.
3. Robust Mahalanobis distance, with location and scatter from the 75% most central reference windows. Typicality is the share of reference windows farther away.
4. k-nearest-neighbour distance (k = 10, robust-scaled features, 5,000 reference windows). Typicality is the share of held-out windows with a larger distance.
5. Zone methods, for a 5 km cell of 25 windows against the reference windows: 1D Wasserstein and energy distance. Typicality is the share of held-out lunar 5 km blocks farther away.
6. PCA and clustering: exploration only, not benchmarked for scoring with one or two features.

**Measures:**
- **Self-consistency:** typicality of held-out lunar windows. It should be uniform for calibrated methods (mean 0.5; Kolmogorov–Smirnov distance to uniform).
- **Discrimination:** AUC between held-out lunar and Earth typicalities.
- **Robustness:**
  - Spearman correlation of Earth typicalities before and after adding noise of 0.5° and 1° to slope;
  - for 2D methods, the same correlation with the regional feature removed.
- **Cost:** seconds per million windows.
- **Interpretability:** can the score be split by parameter.

**Decision rule:** choose the simplest method that is calibrated (KS distance below 0.05), at least as discriminating as the others (AUC within 0.02 of the best), and robust (noise Spearman of at least 0.9).

## Results

To be filled by the run.
