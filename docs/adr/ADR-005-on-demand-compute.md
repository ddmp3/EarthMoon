# ADR-005 Which side computes on demand, and parity

Status: proposed (T30), for gate G3.

## Context
v2 computes in TypeScript and keeps a Python scorer identical, with a parity test. v3 computes everything offline in Python (ADR-001). Only `cells` and `query` need on-demand work, over Parquet files.

## Decision
- **A small internal Python service, `apps/discovery`,** answers `cells` and `query`. It imports the same `tools/discovery` functions as the offline pipeline.
  - Dependencies: `fastapi` 0.162.0 (MIT), `pydantic` 2.14.2 (MIT), `uvicorn` 0.54.0 (BSD-3-Clause), `pyarrow` 26.0.1 (Apache-2.0).
  - Each is the newest release at least 14 days old on 18 November 2026; pip-audit is clean.
- It runs in its own container, with **no public port**. Only the Node API calls it, on the Compose network. It has no write access to the data, and no outbound network.
- **One implementation of every v3 number (Python), so v3 needs no TypeScript port and no new parity risk.** The Node API forwards requests and formats responses; contract tests check the forwarded fields.
- The v2 parity test (TypeScript vs Python on 37 sites) stays as long as v2 is served.

## Rejected
- **Porting the comparison to TypeScript:** it would need a parity test for every function (windows, percentiles, zones), for no gain at request time.
- **Reading Parquet from Node (DuckDB or Arrow bindings):** native modules in the public process, and a second implementation of the queries.

## Consequences
- `tools/check.sh` gains a `discovery` stage (pytest, pip-audit, a contract test through the Node API), and `docker-compose.yml` gains one service.
- If the service is down, `cells` and `query` return 503 with a clear message. The static presets keep working.
