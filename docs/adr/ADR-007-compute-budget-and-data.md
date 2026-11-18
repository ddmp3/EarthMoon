# ADR-007 Compute budget and data location

Status: accepted at gate G3 (signed 18/11/2026 by David). Numbers measured in T40 on the whole Earth (90 m) and on 113 tiles (40 m), see `docs/wiki/runs/earth-cube.md`; T22 estimates in brackets.

## Decision
- **Where the data live:**
  - raw and cached products, the feature cube and releases go under `C:\Users\david\earthmoon-data\`, which is never committed;
  - git holds only specs, manifests (with SHA-256), small derived products, and one fixture release for the tests.
- **The global run is staged, so that each step can be checked and resumed:**

| Stage | Measured in T40 | Notes |
|---|---|---|
| Screening, GLO-90 (90 m) | 26,475 tiles, 0.071 TB (T22: 0.14 TB), cached locally; 1.05 h with 12 workers | Equivalent to GLO-30 at 90 m: Spearman 0.9997, median ratio 0.978 |
| Refinement, GLO-30 (40 m) | 0.589 TB streamed (T22: 0.96 TB); 903 tiles/h with 8 workers, about 29 h for all 26,450 tiles | Reading is 85% of the tile time; the stop rule (72 h) is not triggered |
| Features and comparison | Included above (windows, cells, WorldCover mask) | Comparison measured in T42 |
| Feature cube on disk | 5.4 GB at 90 m (global); 37 MB for 113 tiles at 40 m | Export tiles measured in T44 |

- **Resumable:** the ingest manifest lists done tiles; a rerun skips tiles whose output hash is present.
- **After the first global run, only changes are recomputed** (ADR-009). A source update is costed per changed tile, not per planet.
- **Parallel:** 8 workers for streamed GLO-30 (bounded by download), 12 for cached GLO-90 (bounded by CPU), on 24 CPUs.
- **Stop rule:** if the refinement measured on 100 tiles projects beyond 72 h, T40 reports it and proposes a narrower first run (for example the screening layer plus refinement of the top 10% of cells) before going further.
