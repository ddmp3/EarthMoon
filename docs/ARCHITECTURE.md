# Architecture (v3)

**What runs:**
- **Offline:** a pipeline writes frozen releases.
- **Local Docker stack:** serves them. Nothing is deployed: Azure is frozen during the NASA evaluation, and deployment is David's decision.

Decisions: [adr/](adr/README.md). The v2 page is kept in [history/v2-architecture.md](history/v2-architecture.md).

```
OFFLINE (tools/discovery, Python; data in earthmoon-data/, never in git)
  profiles (planetary windows) ─┐
  Earth cube (Parquet per 1° tile and scale) ─► compare ─► cells (HEALPix 5 km) ─► zones ─► validate ─► release
                                                                                   (JSON, Parquet, PNG tiles,
                                                                                    provenance, changes)
LOCAL STACK (docker compose)
  web (React, Leaflet) ──► api (Node, Express, OpenAPI): /api/v3 from the releases, /api (v2) from the v2 data set
                             └──► discovery (Python, internal network only, read-only): cells in view, queries
  refresher (profile "refresh", on request): watches the sources, writes freshness and the pre-analysis of
             each change; never recomputes (David, 24/11/2026)
```

## Isolation (tested in `tools/validation/test_compose.py`)

| Container | Network | Data |
|---|---|---|
| api | published port 3001 | releases read-only |
| discovery | internal network only, no published port | releases read-only, read-only root file system |
| web | published port 8080 | none |
| refresher | outbound to catalogue hosts only (checked in code), no port | the only writer of the data folder; every capability dropped, read-only root |

## Releases
- **Writers:** `tools/discovery/release.py` (JSON, cells, provenance, changes) and `tools/discovery/tiles.py` (PNG tiles, zoom 0 to 7).
- **`index.json`** names the current release of each body (`current_by_body`) and keeps up to 4 releases per body. The API rereads it when it changes.
- **A refreshed release** is published only through the gate of `tools/discovery/publish.py` (validation, regression anchor, change share). Otherwise it is held for David.
- **Without `EARTHMOON_RELEASES`,** compose serves `data/releases-fixture` (synthetic test data).

## API
- **Contract:** [`apps/api/openapi.yaml`](../apps/api/openapi.yaml), with live docs on `/api/docs`.
- **v3 routes:**
  - `releases`, `profiles`, `scenarios`, `method`, `status`, `changes`, `coverage`, `zones`, `layers`;
  - `tiles/{tile}/provenance`;
  - `cells`, `query` and `sites` (forwarded to the discovery service).
- **Every answer** carries `release` and `methodology_version`. `?release=` reads an older release, or the current one of a body (`release=mars`).
- **The v2 routes** (`/api/analyze`, `/api/sites`, `/api/modes`, `/api/parameters`, `/api/sources`, `/api/reference/moon`) score the frozen v2 data set. Their future is proposed in the release notes.

## Quality gate
`tools/check.sh [api|web|python|discovery|e2e|all]`, in pinned Docker images:
- **Static checks:** strict types, lint and unit tests.
- **Drift checks:** API contract drift, Markdown links, and the figures quoted in the docs against the run summaries.
- **Dependency audit.**
- **End-to-end:** Docker end-to-end tests and the browser audit (desktop and phone).

It must pass before every merge. GitHub Actions runs it on every pull request (`.github/workflows/check.yml`).

## Security (review of 15/11/2026, still valid)
- **Repository:** no secret in git history. Production dependencies have no known vulnerability (allowlist policy in `tools/security/`).
- **Containers:** non-root API image. The refresher reads credentials, when a source needs them, from an uncommitted `.env.refresher`.
- **API:** CORS allows the front-end origin only. Rate limit of 120 requests per minute per IP. Strict input validation, with a 16 KB query body limit.
- **Data exposed:** open data only. No personal data, no accounts.

## Azure (frozen)
- **What exists:** resource group, Log Analytics, Container Registry, Container Apps (API), Static Web App, region `canadacentral` ([infra/terraform/README.md](../infra/terraform/README.md)).
- **Do not deploy during the NASA evaluation.**
- **The v3 stack adds** the discovery service and the refresher. Their Azure resources are not written yet: see the deployment checklist in the release notes.
