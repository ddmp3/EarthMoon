# ADR-006 Front end

Status: proposed (T30), for gate G3. Specification: `docs/wiki/ui/map-spec.md` (T26).

## Decision
- **Keep the stack:** React 19, Vite, Tailwind 4, react-leaflet 5, zustand. **No new runtime dependency** is needed:
  - layers are Leaflet tile layers on the v3 tile URLs;
  - cells at zoom 8 and above are Leaflet GeoJSON;
  - hatching at those zooms uses an SVG `<pattern>` (pastel `#b9c6e8`, as in v2);
  - charts (strip plots, Q–Q plots) are hand-written SVG, as the v2 radar is.
- **New views:** the scenario and environment pickers, the layer list (with "waiting for Txx" layers shown but disabled), the four-state legend, the zone list and zone card, comparison of 2 to 4 zones, a zone against the reference, the provenance panel, and the permanent "Earth cannot reproduce" line.
- **Tests:** the existing vitest suite plus Testing Library tests for each state and view; the UI audit (desktop and phone) extended to the v3 map.
- **v2 views stay** until T50.

## Performance budget (checked by the UI audit in T45)
- JavaScript added by v3: at most 60 KB gzip.
- First map view: under 2.5 s on the local Docker stack.
- At most 40 tile requests per view.
- A zone card opens in under 300 ms with data cached.
