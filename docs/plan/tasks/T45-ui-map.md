# T45 Interface: layer map, missing-data hatching, zone comparison

Read first: `CLAUDE.md`, `docs/plan/README.md` sections 1 to 3, `docs/wiki/ui/map-spec.md` (T26), the ADRs (T30), and `apps/web/README.md`. Branch: `feat/T45-ui-map`.

## Goal
Scientists can choose a planetary environment and a scenario, display each dimension separately, see where data are partial, missing or not covered, open a zone, compare zones, and trace every number to its source.

## Context
- **Web app:** React 19, Vite, Tailwind 4, react-leaflet 5, zustand.
  - Components: `Home.tsx`, `Mission.tsx` (map with 37 `CircleMarker`), `SiteDetail.tsx`, `Stability.tsx`.
  - Content: `content-fr.ts` and `i18n.ts` (FR and EN).
  - Design: dark theme, Inter and Space Grotesk fonts.
- **Already fixed in T01:** labels of the v2 parameters; a missing value shown as "—" with pastel hatching in the scorecard and radar (`.match-bar-missing`, `.radar-axis-missing` in `styles.css`). Reuse that style for the map.
- **v2 gaps to fix here:**
  - deprecated parameters are offered in the free-criteria builder without warning (mark or hide them);
  - confidence, coverage, failed requirements and explanation are not displayed;
  - radar labels can touch the frame edge on long names;
  - the lunar note of `quake_count` ("28 shallow moonquakes in 8 years", `apps/web/src/api.ts` MOON_NOTES and `content-fr.ts`) is not confirmed by its cited source (T13, `docs/REFERENCES.md` section 8): source it or remove it;
  - the "See the match" panel uses the v1 manifest (`apps/web/public/sites/manifest.json`, built by `tools/precompute/site_visuals.py`). Regenerate it from `terrain_v2`: Atacama shows 7.97° in the panel and 7.85° in the scorecard.
- **David's decision:** areas with partial or missing data are labelled and hatched in a soft pastel colour.
- **Quality (decision 6.1):** no TypeScript error, no lint error, no vulnerable dependency, TDD, no regression.

## Steps (TDD)
1. Unit tests (vitest and Testing Library, harness from T01):
   - four map states (evaluated, partial with hatching, not covered, masked) with an accessible text equivalent;
   - legend texts;
   - zone card content;
   - FR and EN keys complete;
   - every parameter id has a label.
2. Implement the layer selector, the hatching (SVG pattern), the confidence channel, zone cards, the comparison of 2 to 4 zones, and the provenance panel. Keep the existing pages working.
3. Extend `tools/validation/ui-audit/audit.mjs`: the new screens on desktop and phone, no console error, no layout overflow, contrast checks on the pastel hatching.
4. Screenshot comparison of the existing pages before and after: differences only where intended.

## Done when
`tools/check.sh all` passes (including ui-audit at 0 defects), screenshots are in the PR, and `apps/web/README.md` is updated.

## Alignment with the ADRs (T30)
No new runtime dependency (ADR-006): Leaflet tile layers for zoom 0 to 7, GeoJSON with an SVG hatching pattern above that, and hand-written SVG charts. Check the ADR-006 performance budget in the UI audit. Show the ADR-009 validity and freshness indicators from `GET /api/v3/status`, with a test per state.
