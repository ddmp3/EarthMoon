# ADR-004 API v3 endpoints

Status: proposed (T30), for gate G3. Contract written in `apps/api/openapi.yaml` in T44, before the code.

## Decision
The public API stays the Node/TypeScript service (`apps/api`), with its OpenAPI contract, validation, CORS and rate limits. The v2 endpoints are unchanged. v3 endpoints are added under `/api/v3`:

| Endpoint | Returns | Served from |
|---|---|---|
| `GET /api/v3/releases` | Release ids, data versions, dates, manifests | Static JSON |
| `GET /api/v3/profiles` and `/profiles/{id}` | Environment specs and computed distributions | Static JSON |
| `GET /api/v3/scenarios` and `/scenarios/{id}` | Scenarios (targets, similarity, requirements, limits) | Static JSON |
| `GET /api/v3/layers/{scenario}/{env}/{parameter}/{z}/{x}/{y}.png` | Raster tiles (zoom 0 to 7) | Static files |
| `GET /api/v3/cells?bbox=…&scenario=…&env=…` | Cells in view (zoom 8 and above), capped at 5,000 | Discovery service |
| `GET /api/v3/zones?scenario=…&env=…&tau=…&min_area=…` | Candidate zones (grid values only) | Static JSON |
| `GET /api/v3/zones/{id}` | Zone card: per-dimension statistics, requirements, confidence, provenance, "cannot reproduce" | Static JSON |
| `POST /api/v3/query` | Custom criteria over the cube (ADR-003 limits) | Discovery service |
| `GET /api/v3/status` | Freshness per source and layer, last and next check, build in progress, held releases (ADR-009) | `status.json` written by the refresher |

**Rules:**
- Every response carries `release`, `methodology_version` and, for each value, its state (`evaluated`, `partial`, `not_evaluated`, `masked`).
- `releases` lists the current release and the last 3, so a cited release id stays readable (ADR-009).
- Numbers are never returned without their spread and their source.
- `tau` and `min_area` accept only the values of the T26 sensitivity grid.
- `POST /query` rejects unknown fields (strict schemas) and limits the body to 16 KB.
