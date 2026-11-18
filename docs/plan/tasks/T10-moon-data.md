# T10 Lunar data inventory

Read first: `CLAUDE.md`, `docs/plan/README.md` sections 1 to 3. Branch: `docs/T10-moon-data`. Research task: no engine code.

## Goal
A verified map of the lunar data that can build environment profiles beyond the south polar cap. For each product: what it measures, where, at what resolution, how well, how to get it.

## Context
- v2 uses only LRO LOLA `LDEM_85S_40M` (terrain shape, south of 85°S). Finding L10: no temperature, composition, hydrogen, illumination or radar data on the lunar side. Finding L3: polar LOLA grids are interpolated between tracks, so their effective resolution is coarser than the pixel size.
- Lunar environments to cover (decision 6.3):
  - highlands and anorthositic terrain;
  - maria and basalt;
  - north and south polar regions;
  - impact craters, fresh and degraded;
  - permanently shadowed and persistently lit regions;
  - thermal extremes;
  - volatiles and ice;
  - pits, skylights and lava tubes;
  - regolith with particular properties.

## Candidates to check (not exhaustive; each fact must be verified)
- **LRO:** LOLA (global and polar gridded topography, slope and roughness products, polar high-resolution grids, illumination products), Diviner (temperature, rock abundance, thermal inertia or H-parameter, ice stability), Mini-RF (circular polarization ratio), LAMP (far-UV albedo, frost in shadowed regions), LROC (WAC global mosaic and topography, TiO2 map; NAC images and DTMs; pit atlas), LEND (hydrogen).
- **Other missions:** SLDEM2015 (LOLA with Kaguya Terrain Camera); Lunar Prospector (GRS and NS: FeO, Th, H); Chandrayaan-1 M3 (mineralogy, OH/H2O); Kaguya (TC, MI, SP, LRS); Chandrayaan-2 (IIRS, DFSAR, OHRC, CLASS; ISRO PRADAN portal); Clementine UVVIS; GRAIL gravity; Chang'e data (check whether access is open).
- **Maps and catalogs:** USGS Unified Geologic Map of the Moon; crater databases; LROC pit list.
- **Literature:** ice distribution and regolith properties. Link to `docs/SCIENTIFIC_REFERENCES.md` (R1 to R23, R39 to R48).

## Where to verify
PDS Geosciences Node and Orbital Data Explorer, LROC website, PDS Imaging, USGS Astrogeology, JAXA DARTS (SELENE), ISRO PRADAN, ESA PSA. Use the `web-fetch` agent or WebSearch, and record the URL and the date of each fact.

## Outputs
1. `data/catalog/moon.yaml`: one entry per product with these fields:
   - `id`, `mission`, `instrument`, `product`, `producer`;
   - `url`, `access` (format, approximate size, licence, account needed);
   - `coverage`, `resolution_spatial`, `resolution_effective`, `resolution_temporal`, `units`;
   - `nature`: one of `measured`, `derived`, `model`, `interpretation`;
   - `uncertainty`, `limitations`, `dimensions` (topography, thermal, composition…), `environments`;
   - `verified_on`, `verified_url`, `status`: one of `verified`, `partly verified`, `not verified`, `not available`.
2. `docs/wiki/data/moon.md`: a readable table generated from the YAML (write a small script, tested), plus one page of synthesis: which environments can be profiled now, which cannot, and why.

## Done when
- Every candidate above has an entry, with a status.
- No field is filled from memory without the `not verified` status.
- The synthesis names the products needed by T20 for each environment.
- `tools/check.sh` passes, including a test that validates the YAML schema.

## Pitfalls
- Do not confuse a pixel size with an effective resolution, or a model with a measurement (example: ice stability depth is a model).
- Large files: record size and access, do not download now (T41 does).
