# Architecture

Static front end, containerized API, Terraform infrastructure on Azure. No database: the API scores a frozen, versioned data set built offline (see [METHOD.md](METHOD.md)). Without that file it falls back to reading the sources live.

```
Browser ──► Azure Static Web App (React)
                │  HTTPS (VITE_API_URL)
                ▼
           Azure Container App (Node/TypeScript API, OpenAPI)
                │  no database, no network call when scoring
                ▼
   data/dataset-v2.json  (frozen, versioned; built offline by tools/precompute/build_dataset.py from
                          Copernicus DEM, MODIS, and NASA POWER / USGS / Smithsonian GVP snapshots)
```

## Repository layout

```
apps/api/         API (Express, ES modules), scoring engine, source connectors, openapi.yaml
apps/web/         React + TypeScript + Vite + Tailwind + Leaflet
data/             candidates.json, candidates-precomputed.json, reference/moon-south-pole.json, fixtures/
docs/             short pages; plan/ (v3 plan and tasks); wiki/ (long material, mirrored to the GitHub wiki); history/
infra/terraform/  Azure infrastructure + deploy.sh
tools/            precompute (offline data), validation (e2e, rankings, ui-audit), scoring (Python reference scorer),
                  security (dependency audit gate), docs (link checker, wiki mirror), check.sh (quality gate)
```

## Design rules

- **The scoring engine only knows the parameter catalog, never the sources.** Each source is an adapter (`apps/api/src/sources/`) returning catalog values, so Mars can be added without touching the engine.
- **A failing source never breaks a response:** its parameters are `null`, the criterion is `missing` and excluded from the total.
- **Nothing is invented:** a value that cannot be measured stays `null`; every value on a site card shows its source.
- A Python scorer (`tools/scoring/score_sites.py`) gives results identical to the TypeScript engine; a test checks it on every site and mode of the real data set.

## API

Contract: [`apps/api/openapi.yaml`](../apps/api/openapi.yaml), live docs on `/api/docs`. Guide: [`apps/api/README.md`](../apps/api/README.md).

## Data files

- `data/candidates.json`: `{ id, name, lat, lon, terrain, role, note?, known_for? }`. `role` is `validation` (known analog), `negative` (control) or `candidate` (site to validate).
- `data/reference/moon-south-pole.json`: lunar reference values with sources, plus `earth_limits` (what Earth cannot reproduce).
- `data/candidates-precomputed.json`: candidates with a `precomputed` block (terrain geometry and MODIS values). Regenerate with `tools/precompute/` after changing `candidates.json`, then run `tools/validation/rankings.py` and `tools/validation/e2e.py`.

## Quality gate

`tools/check.sh [api|web|python|e2e|all]` runs, in pinned Docker images:
- types (strict), lint and unit tests;
- the API contract drift check, the Markdown link check and the dependency audit;
- `docker compose up --build`, the end-to-end tests and the browser audit (desktop and phone).

It must pass before every merge, and GitHub Actions runs it on every pull request (`.github/workflows/check.yml`, test only). The baseline is in [wiki/baseline.md](wiki/baseline.md).

## Azure infrastructure

Resource group, Log Analytics (30-day retention), Container Registry (Basic), Container Apps environment and API app (0.5 vCPU, 1 Gi, 1 to 5 replicas, port 3001), Static Web App (Free), region `canadacentral`. **Frozen during the NASA evaluation: do not deploy.** Deployment, when David decides it, uses `infra/terraform/deploy.sh` (see [its README](../infra/terraform/README.md)).

## Security review (15 November 2026)

| Check | Result |
|---|---|
| Secrets in git history | None found (AWS keys, GitHub tokens, private keys, Azure connection strings, passwords) |
| Dependencies (`npm audit`, API and front end) | 0 vulnerabilities |
| API image | Non-root user, production dependencies only |
| CORS | Front-end origin only |
| Rate limit | 120 requests per minute per IP on `/api` (health probe excluded) |
| Input validation | Strict: 50 KB body limit, criteria checked one by one, 400 with a message |
| Headers | API: `nosniff`, `no-referrer`, no `X-Powered-By`. Front end: CSP, `X-Frame-Options: DENY`, `Referrer-Policy`, `Permissions-Policy` |
| Data exposed | Open data only; no personal data, no accounts |

Known and accepted for the hackathon: Container Registry admin access is enabled (a managed identity would be cleaner), and the Terraform state stays local and out of git.
