# Validation of v3 (T49, 24/11/2026)

**What v3 achieves, measured with the v2 grid plus five new criteria.**
- **Counted figures** are computed from the run summaries in the repository.
- **Scores** were judged by Claude and are a proposal for gate G5, signed by David.
- No outside expert has reviewed them.

Details: [wiki/validation/v3-grid.md](wiki/validation/v3-grid.md). Checks of every run: [wiki/validation/checks-by-run.md](wiki/validation/checks-by-run.md). Protocol: [VALIDATION_PROTOCOL.md](VALIDATION_PROTOCOL.md).

## Unfavourable results first

1. **No scenario has a positive validation (0 of 4).**
   - **A and B (Moon):** no verified reference names an analog site.
   - **C (instruments):** has no run yet.
   - **D (Mars):** Mars volcanic plains: their 4 positive controls fail (median percentile 27.9; the rule needs 75). They are analogs for their basalt, and their geology matches at all 4; the frozen rule tests them on slope ([run-mars-002](wiki/runs/run-mars-002.md)). The other Mars targets have no verified control.
   - **What results show:** where Earth slopes resemble the target's slopes, and nothing more.
2. **The masks check fails in both releases.** 17 of 18 negatives are masked or flagged; the same tree-cover point is not (hidden share 0.41 in the lunar 1 km window, 0.37 in the Mars 2.9 km window, under the 0.5 rule).
3. **Rankings depend on the DEM.** Recomputed with NASADEM instead of Copernicus, only 35% (A) and 45% (B) of the top 20 lunar zones stay in the top 20. At 30 m instead of the planetary pixel, 60% and 65% stay.
4. **Several rankings are not robust.** Zones stable in 90% of the Monte Carlo runs:
   - lunar pits 16%, permanently shadowed regions 23%;
   - Mars polar terrain 0 of 24,013 zones;
   - lunar mare plains 85%, Mars ice-rich mid-latitudes 1,111 of 11,768.
5. **Self-consistency fails for lunar pits** (KS 0.056, threshold 0.05).
6. **The top zones are not shown to be analogs.** Of 60 dossiers (lunar and Mars), 4 are plausible, none is confirmed, and 56 are unknown.
7. **Geology and slope do not meet:** 0 of the 40 top lunar slope zones match the target's lithology.
8. **More than half of the land is hidden.** 53% of lunar cells are half or more masked: what is under forest, ice, water or towns is not assessed.

## Results per scenario

| Scenario | Targets compared | Positive validation | Negatives in top 10% | Masks | Self-consistency | Robust ranking |
|---|---|---|---|---|---|---|
| A Lunar base | polar lit highlands, PSR, pits | none (no verified site) | 0 of 18 | 17/18 | pits fail | partly (PSR and pits weak) |
| B Lunar robotics | polar lit highlands, PSR, mare plains, south polar cap | none | 0 of 18 | 17/18 | pass | mare plains yes, PSR weak |
| C Instruments | none yet | none | — | — | — | — |
| D Mars | volcanic plains, ice-rich mid-latitudes, north and south polar terrain | volcanic plains fail (4 controls); none for the others | 0 of 18 | 17/18 | pass | volcanic plains and ice-rich yes, polar no |

Not comparable (no Earth data at that scale), stated in every release:
- the lunar persistently lit target (5 m mosaic);
- the Mars aqueous mineral sites and rover-scale terrain (HiRISE).

Review of 25/11/2026 (simulated expert roles, not real experts) and the proposed plan: [plan/review-2026-11-25.md](plan/review-2026-11-25.md).

## Grid

Scores from 0 (absent) to 3 (meets the target), same rubric as v2.

| # | Criterion | v1 | v2 | v3 |
|---|---|---|---|---|
| 1 | Sources and traceability | 1 | 3 | 3 |
| 2 | Relevance of parameters | 1 | 2 | 2 |
| 3 | Processing | 1 | 2 | 2 |
| 4 | Validity of calculations | 2 | 3 | 3 |
| 5 | Relevance of comparison criteria | 1 | 2 | 2 |
| 6 | Missing data | 1 | 3 | 3 |
| 7 | Uncertainty | 1 | 2 | 2 |
| 8 | Mission adaptation | 1 | 2 | 2 |
| 9 | Interpretation | 2 | 2 | 2 |
| 10 | Reproducibility | 1 | 3 | 3 |
| 11 | Transparency | 2 | 3 | 3 |
| 12 | External validation | 1 | 1 | 1 |
| 13 | Ground material | 0 | 0 | 2 |
| | **Total** | **15 / 39** | **28 / 39** | **30 / 39** |

New in v3:

| # | Criterion | v3 |
|---|---|---|
| 14 | Global coverage (every land cell assessed or labelled) | 3 |
| 15 | Multi-scale comparison | 2 |
| 16 | Similarity and suitability kept apart | 3 |
| 17 | Mars on its own terms | 2 |
| 18 | Map honesty (four states) | 3 |
| | **Total** | **13 / 15** |

**What the totals hide:**
- The v3 gain over v2 is the discovery itself: every land cell, both bodies, honest maps, reproducible releases.
- The weakest criterion has not moved: external validation (12).
- The ranking of a place still rests on slope alone.

## Reproduce

```bash
python tools/validation/science_grid.py --v3     # counted indicators
tools/check.sh all                               # tests, types, audit, Docker end-to-end
```

The run reports give the commands of each check: [run-002](wiki/runs/run-002.md), [run-mars-001](wiki/runs/run-mars-001.md), [run-mars-002](wiki/runs/run-mars-002.md).
