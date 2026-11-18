# T40 Earth feature cube: topography

Read first: `CLAUDE.md`, `docs/plan/README.md` sections 1 to 3, `docs/adr/` (T30), `docs/wiki/methods/sampling.md` and `docs/wiki/methods/parameters.md`. Branch: `feat/T40-earth-cube`. Gate G3 must be signed.

## Goal
Compute the topographic and geomorphological parameters for every land cell at the scales chosen in T22, with spread, valid fraction, flags and a manifest.

## Context
- **Reuse:** `tools/precompute/terrain_metrics.py` (slope, detrended roughness, traversable share, 40 m pixels, 25 x 25 windows, tested) and `site_terrain.py` (Copernicus GLO-30 reprojected to a local equidistant grid).
- **Storage, format and module layout:** see the ADRs.
- Data files live in `C:\Users\david\earthmoon-data\`. Only manifests and small summaries are committed.

## Steps (TDD)
1. **Tests first:**
   - analytic surfaces (plane, noise, crater-like bowl) give the expected metrics through the new pipeline;
   - the pipeline gives exactly the v2 values for the 37 sites at the v2 scale (regression anchor with `data/dataset-v2.json`);
   - the manifest lists every input with SHA-256;
   - a rebuild gives identical outputs.
2. Ingest the DEM tiles for the pilot tiles, then globally for the coarse stage, with a resumable download and hash checks.
3. Compute the features per cell and per scale: distribution summary, sigma, valid fraction, and flags (water, flat artefact, edge, ice).
4. Masks: water and ice from the catalogue sources chosen in T12 and T21.
5. Measure the time and disk used, and compare them with the T22 estimate.

## Done when
- The global coarse stage and the pilot-tile fine stage are complete.
- The regression anchor passes, `tools/check.sh` passes, and `docs/wiki/runs/earth-cube.md` records versions, hashes, timings and coverage (share of land evaluated, partial, not covered).

## Alignment with the ADRs (T30)
- Code goes in `tools/discovery/ingest` and `tools/discovery/features` (ADR-001). Move the tested functions of `tools/research/sampling.py` there first, with their tests.
- Output: Parquet per tile, pixel scale and data version, with windows and cell statistics tables (ADR-002). GLO-30 is streamed, not stored.
- Run the two-stage search of T22. First measure the COG range-read time on 100 tiles and apply the ADR-007 stop rule before any global run.
- Check that the GLO-90 product matches GLO-30 resampled to 90 m on the pilot tiles, and count the GLO-90 tiles.
