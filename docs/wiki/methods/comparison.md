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

## Results (run of 18 November 2026, 33 s)

**Data:**
- Moon: 71,503 lunar windows with both features.
- Earth: 109,465 windows from the 13 pilot tiles, 20,000 of them drawn for scoring, plus the 1,410 random T21 windows.

**Second feature.**
- `slope_regional` vs `slope_mean`: Spearman **0.79 on the Moon** and **0.91 on Earth**.
- That is above 0.8 on Earth, so under the protocol the 2D results below cannot justify a 2D method.

| Method | Held-out lunar mean (0.5 = calibrated) | KS to uniform | AUC Moon vs pilots | AUC vs random T21 | Spearman under 0.5° noise | Spearman under 1° noise | Regional feature removed | s per million |
|---|---|---|---|---|---|---|---|---|
| v2 interval (1D) | 0.715 | 0.49 | 0.776 | 0.825 | 0.870 | 0.796 | — | < 0.01 |
| **Two-sided percentile (1D)** | **0.494** | **0.014** | **0.801** | **0.855** | **0.951** | 0.891 | — | 0.19 |
| Robust Mahalanobis (2D) | 0.497 | 0.012 | 0.686 | — | 0.974 | 0.918 | 0.667 | 0.25 |
| k-nearest neighbours (2D) | 0.500 | 0.007 | 0.787 | — | 0.961 | 0.896 | 0.803 | 175 |
| Wasserstein, 5 km zone | 0.442 | 0.117 | 0.781 | — | 0.994 | 0.988 | — | 89 |
| Energy distance, 5 km zone | 0.444 | 0.107 | 0.790 | — | 0.991 | 0.964 | — | 1,888 |

Zone methods used 300 calibration blocks, 300 held-out blocks and 300 Earth blocks.

## Decisions

- **Chosen: the two-sided percentile, per parameter.**
  - It is calibrated, the most discriminating, and the cheapest after v2.
  - At 0.5° of noise it keeps a Spearman of 0.95. At 1° it falls to **0.891, just below the 0.9 rule**, and no window method passes at 1° with a comparable AUC. The slope uncertainty is therefore propagated (T25) rather than ignored.
  - Its meaning is simple: "this window is as typical as the X% most central lunar windows".
- **Rejected:**
  - **v2 interval score:** not calibrated. Half of the lunar windows (all of p25 to p75) score 1, so 1 means nothing precise. It is also the least robust.
  - **Mahalanobis and k-nearest neighbours:** the second feature is redundant on Earth. They discriminate no better (AUC 0.69 and 0.79), and k-NN is 900 times slower. Re-test when a non-redundant dimension exists (T46, T47).
  - **Zone methods (Wasserstein, energy):** not calibrated (KS 0.11 to 0.12). Held-out lunar blocks are less typical than calibration blocks, so lunar blocks differ spatially and 300 blocks do not cover them. They are very robust to noise, so re-test with more blocks in T25.
  - **PCA and clustering:** exploration only.
- **A zone is reported** by the distribution of its window typicalities (median, and the share of windows above 0.5), never by one number.
- **Dimensions are always reported separately.**
  - A global similarity is shown only when at least two non-redundant dimensions exist.
  - It is then the **minimum** of the dimension typicalities: not compensating, so a good slope never hides a bad lithology.
  - Its rankings are compared with the geometric mean, as a sensitivity analysis, in T43.
  - Operational suitability, eliminating constraints and confidence stay separate outputs and never enter the similarity.

## Limits of this benchmark

- The protocol split lunar windows at random, so neighbouring windows sit in both halves and self-consistency is optimistic. The zone split was done by block.
- AUC measures how well a method separates the Moon from ordinary Earth, not whether it finds good analogs (that is T25).
- One profile only (south polar cap); the choice is re-checked per profile in T41.
