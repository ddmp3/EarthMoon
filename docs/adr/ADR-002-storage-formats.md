# ADR-002 Storage formats

Status: accepted at gate G3 (signed 18/11/2026 by David).

## Context
T22 measured the volumes:
- the full GLO-30 is about 0.96 TB, too large to keep, so it is streamed;
- the output is per-cell statistics: about 6 million land cells of 5 km per pixel scale;
- per-window values are needed for zone distributions and the Q–Q plots (T26).

## Decision
- **Feature cube:** Apache Parquet, one file per 1° tile, pixel scale and data version.
  - Rows are windows (1 km), with `cell_id`, coordinates, parameter values, valid fraction and flags. A second table holds the cell statistics.
  - Library: `pyarrow` 26.0.1 (Apache-2.0, released 3 November 2026, pip-audit clean).
  - Parquet is columnar, compressed, typed and readable without a server; files are hashed in the manifest.
- **Raw products:** never stored when they can be streamed (GLO-30). Small products (profiles, masks at coarse scale) are cached under `C:\Users\david\earthmoon-data\` with their hash.
- **Web layers:**
  - **Raster XYZ PNG tiles** for zoom 0 to 7. The four states of T26 (value colour, pastel hatching, grey dots, masked outline) are drawn into the tile, so the browser needs no new library: Leaflet already shows XYZ tiles. Rendering uses `pillow` 13.0.0 (MIT-CMU, pip-audit clean).
  - At zoom 8 and above, the browser asks the API for the cells in view (GeoJSON, capped).
- **Zones:** JSON per scenario and environment, with per-dimension statistics and provenance.

## Rejected
- **Zarr:** good for dense cubes, but the data are per-window tables, so Parquet is simpler.
- **PMTiles or vector tiles:** they would add a JavaScript library and a tile builder outside Python. Reconsider if raster tiles exceed the budget (ADR-007).
- **A database server:** contrary to the v2 rule "no database, no network call when scoring".

## Consequences
- **Size estimate, to measure in T40:** about 50 MB of tiles per layer at zoom 7 (about 5,000 land tiles of about 10 KB each).
- Releases live under `earthmoon-data/releases/<release-id>/`, never in git. A small fixture release (one pilot region) is committed for the tests.
