# Architecture decision records (v3)

One page each. Proposed in T30 (18 November 2026); accepted at gate G3, signed 18/11/2026 by David.

| ADR | Decision |
|---|---|
| [001](ADR-001-pipeline-modules.md) | Python pipeline `tools/discovery/`: ingest, features, profiles, compare, zones, validate, export, each with a run manifest |
| [002](ADR-002-storage-formats.md) | Parquet feature cube per tile; PNG raster tiles at zoom 0 to 7 with the four states drawn in; zone JSON |
| [003](ADR-003-caching-and-refresh.md) | Presets precomputed; custom queries over the cube only, never live sources |
| [004](ADR-004-api-v3.md) | `/api/v3` endpoints beside v2, in the Node API's OpenAPI contract |
| [005](ADR-005-on-demand-compute.md) | One Python implementation; an internal service for cells and custom queries, with no public port |
| [006](ADR-006-front-end.md) | Same front-end stack, no new runtime dependency, a performance budget |
| [007](ADR-007-compute-budget-and-data.md) | Data outside git; staged, resumable global run; a stop rule if it projects beyond 72 h |
| [008](ADR-008-deferred.md) | AI assistant and deployment deferred; Azure stays frozen |
| [009](ADR-009-automatic-refresh.md) | Automatic source watching, incremental recompute, freshness and validity shown to every user |
