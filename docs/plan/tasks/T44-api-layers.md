# T44 API: layers, zones, custom queries

Read first: `CLAUDE.md`, `docs/plan/README.md` sections 1 to 3, the ADRs (T30), `apps/api/README.md` and `apps/api/openapi.yaml`. Branch: `feat/T44-api-v3`. Gate G4 must be signed.

## Goal
Serve the v3 results: profiles, scenarios, layers, zones, zone detail, and custom queries over the feature cube. The v2 endpoints keep working.

## Context
- **API:** Express (ES modules), strict input validation (50 KB body limit, criteria checked one by one), rate limit 120 requests per minute, CORS restricted to the front end, OpenAPI at `/api/docs`, 154 vitest tests.
- `apps/web/src/api-schema.ts` is generated from `openapi.yaml` (`npm run generate:api`).
- **Caching (decision 6.3):** preset layers are static and precomputed, rebuilt with the refresh command. Custom queries are computed on demand over the precomputed cube, never against live external sources.

## Steps (TDD)
1. Write the OpenAPI contract first, then contract tests.
2. Endpoint tests: unknown ids return 404; oversize or invalid queries return 400 with a message; responses carry the method and data versions; missing data and coverage are present in zone detail.
3. Implement. Add a test that the v2 endpoints still return the same results (snapshot from `data/reference/expected-rankings-v2.json`).
4. Security: run `npm audit` on any new dependency; no file path ever comes from user input; responses have a size limit.

## Done when
- Contract and endpoint tests pass, `tools/check.sh all` passes (including Docker e2e, extended with v3 checks), and `docs/ARCHITECTURE.md` lists the endpoints.
- `apps/web/src/api-schema.ts` is regenerated.

## Alignment with the ADRs (T30)
- Endpoints as listed in ADR-004, under `/api/v3`.
- `cells` and `query` are forwarded by the Node API to the internal Python service `apps/discovery` (ADR-005). It has no public port and no outbound network, and its dependencies are pinned as in ADR-005.
- Add the service to `docker-compose.yml` and a `discovery` stage to `tools/check.sh`.
- The custom query limits are those of ADR-003.

## Added by T40 (18/11/2026)
- Measure the size of the exported map tiles per layer (ADR-007 had estimated about 50 MB per layer at zoom 7; T40 did not export).
