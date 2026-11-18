# T30 Target architecture and ADRs

Read first: `CLAUDE.md`, `docs/plan/README.md` sections 1 to 3, `docs/architecture.md` (or `docs/ARCHITECTURE.md` after T02), `docs/wiki/methods/*.md`, `docs/SCENARIOS.md`, `docs/VALIDATION_PROTOCOL.md`. Branch: `docs/T30-architecture`. Gate G2 must be signed.

## Goal
An architecture for the discovery engine that keeps every v2 guarantee, and a short decision record (ADR) for each choice.

## Context
- **Today:**
  - `apps/api`: Express, TypeScript, OpenAPI. It scores `data/dataset-v2.json`, with no database and no network call at scoring time.
  - `apps/web`: React and Leaflet.
  - `tools/`: Python offline processing.
  - Deployment: Azure Container Apps and Static Web App, manual via Terraform. **Frozen: never deploy.**
- **Guarantees to keep:**
  - data versioning and SHA-256 of inputs;
  - reproducibility (fixed seeds, no live fetch at scoring time);
  - per-value uncertainty and quality flags;
  - missing values are never bad values;
  - per-zone explanation;
  - Python/TypeScript parity where both compute;
  - all existing tests.
- **David's decision 6.3:**
  - preset scenarios use precomputed layers with a simple refresh command;
  - custom criteria need computation on demand;
  - an AI assistant may come later (T51).

## Decisions to make (one ADR each, in `docs/adr/ADR-0xx-<name>.md`, 1 page max)
1. **Pipeline modules** under `tools/discovery/`:
   - `ingest`: download plus manifest with hashes;
   - `features`: feature cube per tile and per scale;
   - `profiles`;
   - `compare`;
   - `zones`;
   - `validate`;
   - `export` (web tiles).
2. **Storage formats:** the feature cube (for example Cloud-Optimized GeoTIFF, Zarr or Parquet) and web layers (for example raster tiles or PMTiles). Criteria: size, reproducibility, browser support, licence and security of each library.
3. **Caching and refresh:**
   - preset layers built offline, served as static files, rebuilt by one command (`tools/discovery/refresh.sh <scenario>`);
   - custom criteria computed on demand **over the precomputed feature cube**, never by fetching external sources at request time (reproducibility rule). A new source becomes available by an offline ingest that creates a new data version. Explain this trade-off to David in the ADR.
4. **API v3 endpoints**, alongside the v2 ones: profiles, scenarios, layers (tiles), zones, zone detail, custom query (with a size limit and strict validation). Specify them in OpenAPI.
5. **Which side computes on demand** (Python service or TypeScript port), and how parity is tested.
6. **Front end:**
   - layer switching;
   - pastel hatching (SVG pattern or canvas);
   - zone cards and comparison;
   - performance budget.
7. **Compute budget** (from T22) and where large data live: `C:\Users\david\earthmoon-data\`, never in git.
8. **Deferred:** the AI assistant (T51); deployment (David decides after the NASA evaluation).

## Done when
- The ADRs exist, `docs/ARCHITECTURE.md` shows the target diagram, and each new dependency is listed with version and audit status.
- The work is split into PR-sized steps that update T40 to T47 if needed.
- Gate G3 is signed.
