# T26 Mapping methodology (design)

Read first: `CLAUDE.md`, `docs/plan/README.md` sections 1 to 3, `docs/wiki/methods/comparison.md` and `docs/SCENARIOS.md`. Branch: `docs/T26-mapping`.

## Goal
Specify the maps: which layers, how values, missing data, uncovered areas and confidence look, and how candidate zones are delineated and compared.

## Context
- Today the map (`apps/web/src/components/Mission.tsx`, react-leaflet) shows 37 circle markers coloured by score.
- David's decision: areas where data are partial or missing on one or more criteria are **hatched in a soft pastel colour**, and labelled as partial or missing, so that comparisons stay scientific.
- Layers requested: topographic, geological, mineralogical, thermal, hydric, environmental, geomorphological, and operational correspondence, plus a multidimensional view. Each layer can be displayed alone.

## Steps
1. **Layer list per scenario.** For each layer, define:
   - the value shown (for example "percentile among lunar windows") and its legend text;
   - the colour scale (colour-blind safe, perceptually uniform);
   - the scale at which it is valid.
2. **Four states,** visually distinct:
   - evaluated;
   - evaluated with partial data (hatched pastel, with the list of missing criteria on hover);
   - not evaluated because the data have no coverage (a different pattern or grey, with the reason);
   - masked (water, ice, or other masks, with the reason).
3. **Confidence:** a separate layer or an opacity/texture channel. Never mixed into the value colour.
4. **Candidate zones:** the rule (for example a threshold on similarity plus connected components plus a minimum area), with the zone statistics. A zone card shows: per-dimension values with spread, strengths and weaknesses, requirements, confidence, sources, and what Earth cannot reproduce.
5. **Comparison:** 2 to 4 zones side by side, plus a zone against the reference environment.
6. **Provenance panel:** every number links to its source, product version and processing step.
7. Write ASCII wireframes for the main screens.

## Outputs
`docs/wiki/methods/mapping.md` and `docs/wiki/ui/map-spec.md` (wireframes, states, legends, accessibility notes).

## Done when
The spec covers the four states, each layer, zones, comparison and provenance, and is consistent with the existing design (fonts Inter and Space Grotesk, dark theme).
