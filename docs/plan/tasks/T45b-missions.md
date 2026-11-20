# T45b v3 inside the missions

Read first: `docs/wiki/ui/map-spec.md`, ADR-006, T45. Branch: `feat/T45b-missions`.

## Why
David's review of T45 (20/11/2026): the separate discovery page looked added at the last minute, and the missions kept ranking sites without the new data. Decisions:
- the v2 ranking of the 37 known sites stays, enriched with the v3 values at each site;
- the discovery map moves into the missions, mission 4 (free criteria) included;
- same graphic quality as the existing pages, and every text translated.

## What changes
- **Robotics = scenario B, colony = scenario A:**
  - pick the lunar environment and switch the coverage overlay in the mission's control bar;
  - a validity line under the controls;
  - a v3 mark on each ranked site;
  - a "Discovered zones" tab beside the ranking, with comparison;
  - one map with the v3 layers, legend and cells;
  - zone card and provenance under the map.
- **Site card:** a section "Our v3 data at this place", one row per environment of the scenario, from `GET /api/v3/sites` (the discovery service places each site in its HEALPix cell).
- **Free criteria (mission 4):** the v2 builder stays. A "Search the whole Earth (v3)" form runs `POST /api/v3/query` in the current map view. The map and zones show before any v2 run. `#discover` opens this mission.
- **Calibration:** scenario C is not computed in v3; the mission says so.
- **Translations:** the texts the API serves in English (scenarios, requirements, limits, processing steps, coverage classes) have French versions. Catalogue records are quoted in English, as published, and the panel says so.

## Done when
`tools/check.sh all` passes (UI audit at 0 defects, ADR-006 budget), screenshots in the PR, `apps/web/README.md` updated.
