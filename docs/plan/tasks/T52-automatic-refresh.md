# T52 Automatic refresh and incremental recompute

Read first: `CLAUDE.md`, `docs/plan/README.md` sections 1 to 3, ADR-009 (and ADR-001, 005, 007). Branch: `feat/T52-auto-refresh`. Depends on T43 (a first global release exists) and T44 (`/api/v3`).

## Goal
Sources are watched automatically. A change is ingested and only the affected units are recomputed. The result is published when the checks pass. Users always see how old the data are, whether they are validated, and whether a newer version is on its way.

## Steps (TDD)
1. **Catalogue:**
   - add a `refresh:` block (signal, published cadence, check interval, verified URL) to every source used by a `keep` or `context` parameter or by a site set;
   - read each cadence at its source page, and write "not verified" otherwise;
   - test that no such source lacks the block.
2. **Watchers, one per family of ADR-009 (S3, CMR, CDS, PDS, DOI or landing page):**
   - test them on recorded responses (no network in tests): unchanged, changed, withdrawn and unreachable;
   - an unreachable source gives `check_failed`, never "unchanged".
3. **Planner:**
   - keys `sha256(input keys + code commit + parameters)` and a dry-run plan;
   - tests: a one-tile change reruns exactly that tile's units plus the global steps; a planetary change reruns compare but no Earth features; no change reruns nothing.
4. **Publication:**
   - the staging release, the conditions of ADR-009 (validation protocol, regression anchor, change below the threshold), the atomic switch, the last 3 releases kept, and `release.py approve|reject`;
   - tests for each hold reason.
5. **Status:**
   - `status.json` schema in the OpenAPI contract, `GET /api/v3/status`, and the `check_overdue` rule (older than twice the interval);
   - contract tests for every state.
6. **Container:**
   - a `refresher` service in `docker-compose.yml`: outbound hosts restricted in code to the catalogue, write access to the data directory, no port, credentials from an uncommitted env file;
   - add a test that the API and `apps/discovery` containers still cannot write the data.
7. **Calibration:**
   - replay one real update (the first one detected, or a forced one on 100 tiles);
   - measure its incremental cost against a full run;
   - set the 1% change threshold from what was measured, and record it in ADR-009.

## Done when
- `tools/check.sh all` passes, with the e2e test extended to check that the status shows `update_in_progress`, then `up_to_date`, after a forced change on a fixture tile.
- `docs/wiki/methods/refresh.md` gives the measured cadences and costs.
- Nothing runs in Azure.
