# Mapping methodology (T26)

Wireframes, legends and accessibility: [../ui/map-spec.md](../ui/map-spec.md). Inputs: T22 (cells), T23 (typicality), [SCENARIOS.md](../../SCENARIOS.md).

## Layers

One layer per similarity parameter of the selected scenario, each shown alone.

| Layer | Value shown | Legend text | Valid scale |
|---|---|---|---|
| Topography | Median typicality of the 1 km windows of the cell | "As typical as the X% most central windows of <environment>" | 5 km cell; windows at the planetary pixel scale (T22) |
| Geology | Share of the cell in the target lithology class | "X% of the cell mapped as <class> (GLiM / Macrostrat)" | Map unit, never finer than the map |
| Mineralogy | Presence of the target mineral group | "Detected / not detected (EMIT, 60 m)" | 60 m, 52°N to 52°S |
| Thermal | Typicality of the day–night amplitude or thermal inertia | As topography, with "model" in the legend | 1 km |
| Hydric and ice | Ground ice class; dryness typicality | Class, or typicality with "model" | 1 to 9 km, flagged when coarser than the cell |
| Environment | Aerosol and wind typicality (Mars only) | Typicality, with "model" for wind | 1 km to 0.25° |
| Operational | Pass or fail of each requirement | "Slope ≤ 25° on half the window (LRV, NTRS 20250011301)" | As the requirement |
| Multidimensional | Minimum of the dimension typicalities | "Weakest dimension: X" | **Hidden** until two non-redundant dimensions exist (T23) |

- **Colour:** one sequential, perceptually uniform, colour-blind safe scale for every typicality layer, *cividis* (matplotlib), with stops generated at build time, not hand-picked.
- **Classes and presence:** categorical marks; operational results are outlines, never fills.
- **Zoom-out:** cells are aggregated into H3 cells **with area weights** (H3 is not equal-area, T22).

## Four states, always distinct without colour

| State | Rule | Look |
|---|---|---|
| Evaluated | Every criterion of the layer has data, valid fraction ≥ 50% | Value colour |
| Partial | Some criteria or windows missing, or valid fraction below 50% | Value colour of what exists, plus **pastel hatching** (`#b9c6e8`, already used in v2). Hover lists the missing criteria |
| Not evaluated | No data coverage (for example EMIT beyond 52°, SLDEM2015 beyond 60°) | Neutral grey dots (`--off`), with the reason |
| Masked | Water, ice, closed vegetation or built-up (WorldCover) | No fill, thin cross-hatch outline, with the reason |

Missing is never drawn as a low value.

## Confidence

Confidence is a **separate layer** and a section of the zone card, never mixed into the value colour. It is derived from:
- the valid fraction;
- the spread of window typicalities;
- the Monte Carlo stability: the share of runs above the 90th percentile (T25);
- whether the inputs are models or interpretations.

The label thresholds stay expert decision E11.

## Candidate zones

**Rule:**
- a cell is a candidate when its typicality is at least τ, every **eliminating** requirement of the scenario passes, and the cell is not masked;
- candidate cells are joined into zones by 8-neighbour connection;
- a zone of fewer than a minimum number of cells is dropped.

**Sensitivity:**
- τ ∈ {0.5, 0.7, 0.9}, default 0.5: as typical as the median planetary window;
- minimum area ∈ {1, 3, 9} cells, default 3, i.e. 75 km².

Counts are reported at every setting, and none of these values is tuned on controls.

**A zone card shows:**
- per dimension: the median and IQR of window typicalities, the share of windows above 0.5, n, the valid fraction, and "model" or "interpretation" tags;
- strengths and weaknesses: the best and worst dimensions, by numbers;
- each requirement with its source or E label;
- confidence and Monte Carlo stability;
- the sources, with product versions;
- **what Earth cannot reproduce**, from the scenario's `cannot_assess` list, always visible.

## Comparison

- **2 to 4 zones side by side:** one row per dimension, showing the distribution of window typicalities (strip plot with median), and the requirements as pass or fail.
- **A zone against the reference environment:** a quantile–quantile plot of the zone windows against the planetary windows, per parameter, with the planetary p5 to p95 band.

## Provenance

Every number opens a panel with:
- the product and its version;
- the catalogue id and its verification date;
- the processing step, with code version and parameters;
- the input SHA-256 and the run id.

The links lead to `data/catalog/*.yaml` and the run manifest (T40).
