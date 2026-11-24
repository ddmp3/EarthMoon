# T45c Immersive interface, one experience per body (David's review, 23/11/2026)

Read first: `CLAUDE.md`, `docs/plan/README.md`, `docs/wiki/methods/` (what each result means), the current web app (`apps/web/src`). Branch: `feat/T45c-ui`.

## What David asked for
- **Two experiences, not a fifth card.** The base site is the Moon experience we built. Choosing Mars switches the **whole site** to Mars: hero image, texts, scenarios, missions, map, colours, credits. Today Mars is only one more mission card: not coherent.
- **Immersive comparison.** A 3D tile where the relief is visible, Earth analog next to the planetary reference (Earth/Moon, Earth/Mars), at the same scale, for one or several chosen constraints.
- **Understand at once** why a place is an analog and which characteristics were kept (and which were not compared).
- Scientific quality stays a requirement; the experience must be at the same level.

## Coherence rule (applies to every UI change)
Never change a tab, window or text alone. Every figure and claim shown must come from the current release (or the catalogues), never be typed by hand, and a test must fail when they drift. Check the whole site after a change, for both bodies and both languages.

## Known incoherences to fix (found 23/11/2026)
The home banner (`apps/web/src/components/Home.tsx`, `i18n.ts` `stats`) shows v2 figures:
- **37 Earth sites compared:** the v2 hand-made site list. v3 compares every Earth land cell, with no list of expected sites.
- **26 parameters per site:** the v2 parameter catalogue. v3 compares slope (T21) and shows geology, frozen ground and aridity as context.
- **8 open data sources:** typed by hand. The catalogues list 45 Earth, 36 lunar and 29 Martian products, and the releases name the ones they use.
- **71,731 lunar terrain windows (LRO LOLA):** the v2 south polar profile. v3 has 8 lunar environments, and Mars has its own profiles.
- The banner speaks of the Moon only, even in Mars mode.

## Steps (TDD)
1. David gives or validates the target design (mock-ups) for both bodies.
2. Figures from the release (`/api/v3/...`), with tests that fail on hand-typed values.
3. Body mode for the whole site; 3D comparison tile (Earth DEM against LOLA or MOLA at the same pixel); "why this place" panel.
4. Browser audit on both bodies, desktop and phone, French and English.

## Done when
David accepts the interface on both bodies, and no figure on the site is typed by hand.

## Part 2 (David, 24/11/2026)
- **3D planet globe next to the Earth map** in a mission, with a real NASA mosaic of the Moon or Mars.
- **Selection both ways:**
  - Selecting an Earth zone lights the windows of the target environment whose slope is nearest to the zone's (David's choice: "windows of the same slope"; our method compares a zone with the distribution of an environment, not with one planetary place).
  - Clicking a planetary point lights the Earth zones of the same slope.
- **Place names instead of coordinates.** Coordinates stay in the details, to ease the dialogue between scientists.
  - **Earth:** OpenStreetMap Nominatim (David's choice), queried once at release time, at most 1 request per second, cached and versioned. Only the top zones of each target and the known sites are queried; the others show their country (Natural Earth). No call from visitors' browsers.
  - **Moon and Mars:** the IAU Gazetteer of Planetary Nomenclature (USGS), verified and catalogued first. Nominatim does not cover other bodies.
- **Order:** names, then same-slope windows (zone slope median computed at export), then the globe.
