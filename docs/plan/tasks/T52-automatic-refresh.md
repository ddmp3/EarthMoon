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

## Added during T52 (David, 23/11/2026)
- **Recompute on command, not automatic:** detection stays automatic; the recompute starts with one command after its plan and estimated time are shown (no CPU load without David's go). ADR-009 is amended.
- **Local only:** an update recomputes the changed tiles, their neighbours' cells and the zones that touch them, never the whole planet. The Monte Carlo and the release export follow the same rule. Comparison units are (tile, target), so a planetary change reruns only its target.
- **New planetary products** (a new LOLA release, new HiRISE or HRSC DTMs over a target): detected from the release tables and logged as "detected, to verify" in `docs/plan/data-improvements.md`. They are never injected into a run: a new reference is a new protocol version.
- **Tile versioning for researchers:**
  - the cube manifest records `computed_at` for every tile;
  - each release publishes the provenance of every tile: source versions and dates, computation date, code version, the release where it last changed;
  - an API route serves it, and the cell panel shows it;
  - each release publishes `changes.json`: previous release, source events (what, when detected), tiles recomputed, cells and zones changed, publication decision and reasons. It is served by the API and readable in the wiki.
- **Zone rule:** with exact cell sets, a zone gaining one cell counts as one zone out and one in, so the "no zone appears or disappears" rule holds even a no-change re-release. A rule based on the share of a zone's cells that change goes to David before it is fixed.

## Done when
- `tools/check.sh all` passes, with the e2e test extended to check that the status shows `update_in_progress`, then `up_to_date`, after a forced change on a fixture tile.
- `docs/wiki/methods/refresh.md` gives the measured cadences and costs.
- Nothing runs in Azure.
