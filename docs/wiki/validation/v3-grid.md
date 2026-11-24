# v3 evaluation grid (T49, 24/11/2026)

The 13 criteria of the v2 grid ([v2/SCIENTIFIC_VALIDATION.md](../v2/SCIENTIFIC_VALIDATION.md)), with the same rubric, plus 5 criteria for what v3 adds.

**Who judged:**
- **Counted indicators** come from `python tools/validation/science_grid.py --v3`, which reads the run summaries in `data/runs/` and the catalogues.
- **Scores** were judged by Claude against the rubric, with the evidence given here. They are a proposal for David to review at gate G5. No outside expert has reviewed them (E10).

| Level | Meaning |
|---|---|
| 0 | Absent |
| 1 | Present but with errors that change results |
| 2 | Correct for what it covers, with known gaps |
| 3 | Meets the target stated for the criterion |

## Counted indicators

Output of `science_grid.py --v3`. run-002 is the lunar release, scenarios A and B. run-mars-001 is the Mars release, scenario D.

| Indicator | run-002 | run-mars-001 |
|---|---|---|
| Cells assessed (5 km, equal-area) | 6,296,808 | 7,400,488 |
| Negatives in the top 10% (pass: at most 1 of 18) | 7/7 targets | 3/3 targets |
| Masks check (pass: 18/18) | 17/18 | 17/18 |
| Self-consistency (KS <= 0.05) | 4/5 targets (fails: moon-pits 0.056) | 3/3 targets |
| Reproducibility (identical SHA-256) | 5/5 tiles | 5/5 tiles |
| Monte Carlo: zones stable in 90% of runs | 16 to 85% per target (mare plains 85%, polar lit highlands 75%, PSR 23%, pits 16%) | ice-rich 1,111 of 11,768; north and south polar 0 |
| Dossiers of the top zones | plausible 4, unknown 36 | unknown 20 |
| NASADEM instead of Copernicus, top 20 kept (A, B) | 35%, 45% | not computed |
| 30 m instead of the planetary pixel, top 20 kept (A, B) | 60%, 65% | not computed |
| Sources of the releases: verified, with a refresh block, watched | 15/16, 16/16, 11/16 | (same) |
| Scenarios with a positive validation (3 or more verified controls that pass) | 0 of 4 | |

## The 13 criteria of the v2 grid

| # | Criterion | v1 | v2 | **v3** | Evidence for v3 | Remaining gap |
|---|---|---|---|---|---|---|
| 1 | Sources and traceability | 1 | 3 | **3** | 15/16 release sources verified in the catalogue; SHA-256 of inputs and outputs; protocol, release and commit in every answer; provenance of every Earth tile (T52) | One source not verified; 5 sources have no automatic signal |
| 2 | Relevance of parameters | 1 | 2 | **2** | No invalid indicator; the terrain metrics reduce to slope (T21), so slope is compared and the rest is shown as context | Slope alone barely discriminates (35 to 44% of high-confidence Mars cells reach τ 0.5) |
| 3 | Processing | 1 | 2 | **2** | Earth resampled to the planetary pixel; 7 hidden-ground classes masked; one global equal-area grid | Masks check 17/18 in both releases; ranking depends on the DEM (NASADEM keeps 35 to 45% of the top 20) |
| 4 | Validity of calculations | 2 | 3 | **3** | Test-first code throughout; rebuilds give identical SHA-256 (5/5 tiles, both releases); the local zone update equals a full recomputation | |
| 5 | Relevance of comparison criteria | 1 | 2 | **2** | Every similarity rests on a planetary measurement (LOLA, SLDEM, MOLA); no expert weights (E5) | Base and rover requirements beyond slope are not assessed (E13, E14) |
| 6 | Missing data | 1 | 3 | **3** | Four map states; missing is never a bad value; geology "no map" and "unresolved" kept apart from "no match" | |
| 7 | Uncertainty | 1 | 2 | **2** | Monte Carlo (500 runs, seeded) with rank intervals; Mars noise measured from the DEM error (mars-v2) | Lunar noise of 0.5° not derived per scale; correlated DEM errors not modelled; polar Mars and lunar PSR and pits rankings are not robust |
| 8 | Mission adaptation | 1 | 2 | **2** | Scenarios A to D with their own targets; LRV limit verified; lunar limits never reused on Mars | VIPER limit not verified (E1); instrument requirements open (E15); scenario C has no run |
| 9 | Interpretation | 2 | 2 | **2** | Validity and freshness on every page; coverage, confidence, dossiers, provenance per tile | David's review (23/11): the interface does not yet make clear why a place is an analog (T45c) |
| 10 | Reproducibility | 1 | 3 | **3** | Frozen releases, seeds, manifests; identical SHA-256 on rebuild | |
| 11 | Transparency | 2 | 3 | **3** | Method, protocol and catalogue served by the API; frozen protocol tags; reports with unfavourable results first | |
| 12 | External validation | 1 | 1 | **1** | 18 negative controls, drawn at random before the runs (target of 10 or more met) | No positive validation in any scenario; no independent expectation list (E10) |
| 13 | Ground material | 0 | 0 | **2** | Lithology class compared through crosswalk E17 (T46): basalt fields and an anorthosite body recognized | No composition (EMIT open); half the land has no usable lithology; 0 of 40 top slope zones match by geology |
| | **Total** | **15 / 39** | **28 / 39** | **30 / 39** | | |

## Criteria added for v3

| # | Criterion | Target (3) | **v3** | Evidence | Remaining gap |
|---|---|---|---|---|---|
| 14 | Global coverage | Every Earth land cell assessed, or labelled with the reason | **3** | 6.3 M lunar and 7.4 M Mars cells; every cell has a state and a reason | 53% of lunar cells are half or more hidden by vegetation, ice, water or towns |
| 15 | Multi-scale comparison | Each target compared at its planetary pixel, and the result checked at another scale | **2** | Same-pixel comparison (T22); lunar top zones recomputed at 30 m (60 to 65% kept) | Targets below 40 m (5 m lunar mosaic, HiRISE) are "not comparable"; not checked on Mars |
| 16 | Separation of similarity and suitability | Similarity, requirements and suitability reported apart, never merged | **3** | Typicality per target, requirements as met, failed or unknown, suitability apart; no weighted sum (T23) | |
| 17 | Mars | The phase 1 targets assessed and validated on their own terms | **2** | 3 of 4 targets (polar, ice-rich), protocol mars-v1 then mars-v2, no lunar criterion reused | Volcanic plains wait for the Tanaka map (R5), and so do the only positive controls; polar rankings not robust |
| 18 | Map honesty | The four states shown everywhere, hidden ground never drawn as a result | **3** | Evaluated, partial, hidden and no data drawn on every layer, in both languages; status says "not validated" | |
| | **Total** | | **13 / 15** | | |

## How to reproduce

```bash
python tools/validation/science_grid.py --v3      # counted indicators of this page
python tools/validation/science_grid.py           # the v1 and v2 grid
```

The checks of each run: [checks-by-run.md](checks-by-run.md). Runs: [run-002](../runs/run-002.md), [run-mars-001](../runs/run-mars-001.md).
