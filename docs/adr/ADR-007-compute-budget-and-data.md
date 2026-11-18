# ADR-007 Compute budget and data location

Status: proposed (T30), for gate G3. Numbers measured in T22 on 13 pilot tiles.

## Decision
- **Where the data live:**
  - raw and cached products, the feature cube and releases go under `C:\Users\david\earthmoon-data\`, which is never committed;
  - git holds only specs, manifests (with SHA-256), small derived products, and one fixture release for the tests.
- **The global run is staged, so that each step can be checked and resumed:**

| Stage | Measured or estimated | Notes |
|---|---|---|
| Screening, GLO-90 (90 m) | About 0.14 TB of download (5 to 8 h) and about 3 h of CPU | Tile count and GLO-90 equivalence to check in T40 |
| Refinement, GLO-30 (40 m), passing cells only | About half the cells pass; the time for COG range reads is **not measured** | Measured on 100 tiles in T40 before the global run |
| Features and comparison | About 0.8 s per tile of CPU at 40 m | 26,450 tiles |
| Export, tiles at zoom 7 | About 50 MB per layer (estimate) | Measured in T40 |

- **Resumable:** the ingest manifest lists done tiles; a rerun skips tiles whose output hash is present.
- **Parallel:** up to 8 workers locally, bounded by download bandwidth.
- **Stop rule:** if the refinement measured on 100 tiles projects beyond 72 h, T40 reports it and proposes a narrower first run (for example the screening layer plus refinement of the top 10% of cells) before going further.
