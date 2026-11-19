# Comparison engine on the pilot tiles (T42 run, 18/11/2026)

Scenarios A (lunar base) and B (lunar robotics) on the 13 T22 pilot tiles. Summaries: `data/runs/compare-pilot-A.json` and `-B.json` (commit `e5350bc`). The full cell tables are Parquet files outside git, and their SHA-256 are in the summaries. Method: `docs/METHOD.md`, section "v3 comparison engine".

## What each cell gets

Similarity per lunar target, requirements, operational suitability, coverage, confidence and a Monte Carlo rank interval are separate outputs: none is averaged with another.

| | Scenario A | Scenario B |
|---|---|---|
| Cells (5 km) | 5,714 | 5,714 |
| Targets compared | lit highlands and PSR (40 m), pits (59.2 m) | lit highlands, PSR, polar cap (40 m), mare plains (59.2 m) |
| Not comparable | persistently lit: 100 m windows at 5 m, no Earth cube at 5 m | — |
| Requirements | base slope ≤ 10°: 3,801 met, 1,319 failed, 594 unknown | LRV 20°: 4,582 met, 538 failed (eliminated, still shown), 594 unknown; VIPER 15° (reported only): 4,270 met, 850 failed |
| Not evaluated | bearing capacity and boulders (value not set, E13) | — |
| Confidence | 2,746 high, 610 medium, 2,358 low | same cells |

"Unknown" cells have no valid window (sea or masked ground). Low confidence comes mostly from masked ground: forest, buildings, water.

## Rankings

- **Why the high-confidence list:** ranked by median typicality alone, the first cells are low-confidence ones, where a median of a few unmasked windows is high by chance. The summary therefore also gives the ranking among high-confidence cells, the one to show first.
- **Lit highlands, PSR, polar cap:** high-confidence top cells are on the pilot tile 37°N 105°E: median typicality 0.86 to 0.94, and in the top decile in 100% of Monte Carlo runs.
- **Mare plains:** high-confidence top cells are on 25°S 135°E: median 0.83 to 0.84.
- **Outputs stay separate:** a cell can meet the base-slope requirement (≤ 10°) with a suitability of only 0.16, because its mean slope is near 9°.

## Uncertainty (Monte Carlo)

- **Setup:** 500 runs, seed 20261119, Gaussian noise of 0.5° on each window slope (the T23 noise level, assumed as data sigma).
- **Cells in the top decile in at least 90% of runs:** 480 (lit highlands), 499 (PSR), 485 (polar cap), 337 (pits), 228 (mare plains), out of about 5,400 to 5,700.
- **Same seed, same output:** tested.

## Earth smoothing sensitivity (David's decision of 18/11/2026)

The pilot tiles are measured again with a 1-pixel Gaussian smoothing (40 m and 59.2 m), with the same masks:

| Scale | Earth slope, smoothed / raw | Target | Spearman of cell medians | Top-decile overlap |
|---|---|---|---|---|
| 40 m | 0.827 | lit highlands | 0.931 | 0.75 |
| 40 m | 0.827 | PSR | 0.932 | 0.78 |
| 40 m | 0.827 | polar cap | 0.932 | 0.74 |
| 59.2 m | 0.819 | pits | 0.916 | 0.61 |
| 59.2 m | 0.819 | mare plains | 0.921 | 0.50 |

The ranking keeps its order (Spearman above 0.9), but a quarter to half of the top decile changes. For mare plains, half of the best cells depend on the choice. This is why the choice is reported and not hidden; T43 shows it with the zones.

## Checks

- **Held-out lunar blocks** (35,865 polar cap windows, checkerboard of 5 km blocks): mean typicality 0.4996, Kolmogorov–Smirnov distance 0.005 to uniform.
- **Tested rules:**
  - a failed requirement keeps the similarity visible and is never offset by it;
  - a missing value counts neither for nor against a cell;
  - unknown cover stays unknown;
  - a high median from a few windows is not ranked first in the high-confidence list.
- **v2 API engine:** unchanged, and its tests pass.

## Limits

- 13 pilot tiles only: the global run is T43.
- The LRV limit is tested at 20°, the stored lower bound of 20 to 25°. The 25° window share is not in the cube, so the threshold is not varied in the Monte Carlo.
- The slope noise of 0.5° is assumed, not measured per pixel.
- Only `slope_mean` is compared: lithology and thermal dimensions arrive with T46 and T47.
