# ADR-001 Discovery pipeline modules

Status: proposed (T30, 18 November 2026), for gate G3.

## Context
v3 must turn planetary and Earth products into profiles, cell statistics, comparisons and zones, and do it reproducibly. The research scripts of T21 to T25 (`tools/research/`) already hold the tested functions: windows, percentile typicality, two-stage screening, controls.

## Decision
A Python package `tools/discovery/` with one module per stage. Each stage reads the manifest of the previous one and writes its own:

| Module | Input | Output |
|---|---|---|
| `ingest` | Catalogue ids (`data/catalog/*.yaml`) | Downloaded or streamed products, manifest with URL, size, SHA-256, date |
| `features` | Ingest manifest, T22 rules | Feature cube: 1 km windows and 5 km cell statistics per tile and pixel scale |
| `profiles` | Specs `data/profiles/spec/*.yaml` | Planetary profiles (`data/profiles/<body>/<env>.json`) |
| `compare` | Feature cube, profiles, `data/parameters.yaml` | Typicality per window and per cell, per parameter (T23 method) |
| `zones` | Comparison, scenarios `data/scenarios/*.yaml` | Candidate zones with statistics (T26 rule) |
| `validate` | Zones, `data/validation/*.yaml` (tag `validation-protocol-v1`) | Validation report and Monte Carlo |
| `export` | Comparison, zones | Web layers and zone JSON (ADR-002) |

**Run manifest:** every stage records its inputs (with SHA-256), code version (git commit), parameters and seed. The `release` id is the hash of the run manifests.

The functions validated in `tools/research/` move into `tools/discovery/` with their tests. The research scripts then import from there, so one implementation remains.

## Consequences
- Each stage can be rerun alone and checked against its manifest.
- `tools/precompute/` (v2) stays unchanged until T50 decides the retirement of v2.
