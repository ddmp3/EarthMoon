# API

Express server (Node 22, TypeScript, ES modules) on port **3001**. Full contract: [`openapi.yaml`](openapi.yaml), live docs on `/api/docs`.

- No API key, no account: every source is public.
- A failing source never breaks a response: its parameters are `null` and the criterion gets the verdict `missing`.

## Run

```bash
cd apps/api
npm install
npm test             # 111 tests
npm run typecheck
npm run dev          # real sources, http://localhost:3001/api/docs
npm run check:sources   # checks the real sources from your machine
USE_FIXTURES=1 npm run dev   # sample values from data/fixtures (mostly fictional, never for the demo)
```

Production: `npm run build` then `npm start`.

## Environment variables

| Variable | Default | Purpose |
|---|---|---|
| `PORT` | `3001` | Listening port |
| `FRONTEND_URL` | — | Origin allowed by CORS |
| `EXTRA_ORIGINS` | — | Other allowed origins, comma-separated |
| `DATA_DIR` | `<repo root>/data` | Candidates, fixtures and lunar profile |
| `USE_FIXTURES` | off | `1`: sample values instead of the real sources |
| `RATE_LIMIT_PER_MINUTE` | `120` | Requests per minute and per IP |
| `GVP_WFS_URL` | Smithsonian WFS | Alternative URL for the volcano list |

## Routes

| Method | Route | Response |
|---|---|---|
| GET | `/api/health` | `{ "status": "ok" }` |
| GET | `/api/modes` | Modes 1 to 3 with their criteria |
| GET | `/api/parameters` | Parameter catalog |
| GET | `/api/sources` | Data sources and attributions |
| GET | `/api/reference/moon` | Lunar reference profile |
| POST | `/api/analyze` | Ranked sites for a `mode` or free `criteria` |
| GET | `/api/sites/{id}?mode=robotics` | One site with raw values, sources and lunar references |

```bash
curl -X POST http://localhost:3001/api/analyze -H "content-type: application/json" -d '{"mode":"robotics"}'
```

- Send either `mode` or `criteria` (mode 4), never both. `total` is out of 100, sites are sorted by descending `total`.
- `verdict`: `match` (≥ 0.7), `partial` (0.4 to 0.7), `mismatch` (< 0.4), `missing` (no value, excluded from the total).
- The bare-soil filter (`bareSoilOnly`, on by default) keeps vegetated sites in the list with `total: 0` and `"excluded": "vegetation"`, last.
- Errors are always `{ "error": "message" }` with 400, 404, 413, 429 or 500.

## Data

- `data/candidates.json`: the candidate sites. Invalid entries are skipped and logged.
- `data/candidates-precomputed.json`: Copernicus DEM geometry and MODIS values computed offline by `tools/precompute/` (see its scripts). Without it, those 8 parameters are `missing`.

## Adding a connector

A connector is a function `({ lat, lon }) => Promise<ParamValues>` (see `src/sources/gvp.ts`).

1. Return only your parameters, using catalog identifiers (`docs/scenarios.md`); `null` when unavailable.
2. Throw on failure: `analyze()` ignores it and the criteria become `missing`.
3. Use `fetchJson` (timeout, retries on 5xx) and wrap the connector in `withCache`.
4. Register it in `src/sources/index.ts` and add tests with a mocked `fetchImpl`: no test may call the network.
5. Never invent a source value: if a source does not answer, the value is `null`.
