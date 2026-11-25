# run-mars-002: Mars with the volcanic plains (T48c, 25/11/2026)

**What was run:**
- **Scenario D, four targets:** the three of phase 1, plus the volcanic plains of the Tanaka et al. 2014 geologic map.
- **Protocol:** `validation-protocol-mars-v3`, frozen and tagged before the run, decided by David on 24/11/2026.
- **Method and decisions:** [methods/mars](../methods/mars.md).
- **Data:**
  - outputs in `earthmoon-data/run-mars-002/` (not in git);
  - summaries in `data/runs/run-mars-002/`;
  - release `r-4fea11f8`, now the current Mars release of the site. A first export, `r-a673f19b`, listed the Tanaka map as "not in catalogue" in its sources; it is kept, not served.
- **Earlier run:** run-mars-001 stays as it is ([run-mars-001](run-mars-001.md)).

## Unfavourable results first
1. **The positive controls fail.** This is the first positive test on Mars.

   | Control (R29) | Cell percentile | Confidence | Basalt match (geology, E20) |
   |---|---|---|---|
   | Big Craters, Idaho | 30.4 | high | 100% |
   | Mauna Ulu, Hawaiʻi | 25.4 | medium | 100% |
   | Kīlauea Iki, Hawaiʻi | 25.4 | low (all windows hidden) | 100% |
   | Kīlauea caldera, Hawaiʻi | 38.0 | high | 89% (11% no map) |
   | **Median** | **27.9** (rule: ≥ 75) | | |

   - **The cause** ([data](../../../data/runs/run-mars-002/control-slopes.txt)):
     - at 11.6 km, the Hawaiian windows hold shield flanks and caldera walls, with mean slopes of 2.6 to 4.9°;
     - that is the 89th to 95th percentile of the Martian volcanic windows, whose median is 0.6°;
     - Big Craters comes closest (0.67° and 0.95° in two of its three windows).
   - **What it means:** the R29 sites are named as analogs for their **basalt geology**, at outcrop scale, not for their kilometre-scale relief. The rule tests them on slope, and fails, while their geology matches at all four sites.
   - **The result stands under mars-v3.** Testing controls on the dimension their reference justifies needs a new protocol version ([review and plan](../../plan/review-2026-11-25.md), A3).
2. **The masks check is 17 of 18, as in run-mars-001.** The forest point keeps a hidden share of 0.37 in its window.
3. **Slope alone barely discriminates.**
   - 33% of the high-confidence, mostly unmasked cells reach τ 0.5 for the volcanic plains.
   - Zones at τ 0.5 (3 cells or more) cover 17.4 million km².
4. **A rare Martian profile.**
   - Only 4,983 of 232,956 windows in the volcanic units hold a MOLA shot in half of their pixels (E19).
   - The rule removes windows that interpolation between tracks has smoothed ([sensitivity](../../../data/runs/run-mars-002/observed-share-sensitivity.json)): median slope 0.42° below 10% observed, 0.60° at 50% and more.
   - It does not shift latitudes.
   - Earth is fully sampled, which may still make Earth look slightly steeper (plan, C6).

## What was computed
| Step | Result |
|---|---|
| Volcanic plains profile | 11 units the map calls volcanic. 4,983 windows, slope median 0.60° (p25 0.34°, p75 1.19°). Without the 3 edifices: 4,735 windows, median 0.57° |
| Profile tail | edifices are 5% of the windows but 26% of those above the 89th percentile (2.48°) ([data](../../../data/runs/run-mars-002/profile-tail-by-unit.json)) |
| Assessed cells | 7,400,488 HEALPix cells, 32,138 tiles, 0.91 h, 0 failures |
| Geology (E20) | Macrostrat for all cells (34,241 tiles, 0 missing). Basalt match 1.1% of samples, partial 1.0%, no map 37% |
| Phase 1 targets | zones and Monte Carlo identical to run-mars-001 (checked cell by cell) |

## Zones and Monte Carlo
| Target | Zones τ 0.5, 3 cells | Area | Stable (≥ 90% of 500 runs) |
|---|---|---|---|
| Volcanic plains | 11,235 | 17.4 M km² | **1,028** (0.41 M km²) |
| Ice-rich mid-latitudes | 11,768 | 18.6 M km² | 1,111 |
| North polar terrain | 11,847 | 24.5 M km² | 0 |
| South polar terrain | 12,166 | 19.1 M km² | 0 |

- **Monte Carlo noise:** 0.04° at 463 m (mars-v2, unchanged).
- **Basalt in the zones:**
  - 110 volcanic-plains zones have half of their samples on basalt, 9 of them stable;
  - on average, zone cells have 0.7% basalt match and 52% no match.
- **Grid of τ and minimum size:** in `zones.json`.

## Unexpected candidates (dossiers)
The 20 best zones of scenario D, one dossier each in `run-mars-002/zones/` (hillshade of Copernicus GLO-90, place name, cell medians). Zones of all targets are ranked together (rule fixed before run-001).
- **6 are volcanic-plains zones** (D-01, D-02, D-08, D-09, D-10, D-11). The other 14 are ice-rich zones already in run-mars-001: their searches are reused, with the same rule.
- **Literature:** queries, findings and sources in `data/runs/run-mars-002/literature.json`. A match needs a source naming the place itself as an analog of the target, or describing its relief as the target's profile does.

| Outcome | Zones |
|---|---|
| Explained artefact | 0 (no flattened lake or DEM void in the hillshades) |
| Plausible | 0 |
| Unknown | 20 |

**None of the 6 volcanic-plains zones is volcanic.**
- They are sedimentary basin floors and plateaus:
  - Nevada, Utah and Arizona (Basin and Range);
  - the Katanga plateau (DR Congo);
  - the Kirkuk plain (Iraq);
  - the Damghan alluvial fans (Iran).
- Not one of their geology samples is basalt (E20).
- The nearest named analog is the Lunar Crater volcanic field, about 20 km north of D-01: the volcanic field itself is not in the zone.
- **What it means:** at 11.6 km, the slope of the Martian volcanic plains is the slope of any flat ground. Slope finds the relief, and geology says the rock does not match. Both are shown side by side, never combined (E20).

## Validation (protocol mars-v3)
| Check | Rule | Result | Pass |
|---|---|---|---|
| Positives (volcanic plains) | median percentile ≥ 75 | 27.9; 0 of 4 in the top 10% | **no** |
| Positives (other targets) | — | none exist | no validation |
| Negatives in the top 10% | at most 1 of 18 per target | 0 for every target | yes |
| Masks | 18 of 18 masked or flagged | 17 of 18 | **no** |
| Self-consistency | KS ≤ 0.05 | volcanic 0.037, ice-rich 0.026, north 0.004, south 0.008 | yes |
| Reproducibility | identical SHA-256 on rebuild | 5 of 5 tiles, identical cell rows | yes |

## What this run cannot show
- That a volcanic-plains zone is a good analog for a team: only a field campaign can show that.
- Rock type at outcrop scale: Macrostrat maps are 1:1 M to 1:5 M, and the Tanaka map is 1:20 M.
- Relief below the MOLA pixel, where the R29 sites are analogs.
