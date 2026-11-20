# Discovery service (internal)

Python service behind the Node API (ADR-005). It answers `/api/v3/cells`, `/api/v3/query` and `/api/v3/sites` (values at the known sites, at most 100 points) over the cells of a release, and nothing else. It loads the current release at start-up.

- No published port: only the Node API calls it, on the Compose `backend` network, which has no outbound route.
- Read-only: the container file system and the releases folder are mounted read-only.
- Limits (ADR-003, ADR-004): 5,000 cells per view; 1,000,000 cells in a query area; 16 KB body and 30 s, enforced by the Node API.

```bash
tools/check.sh discovery     # tests and dependency audit
```
