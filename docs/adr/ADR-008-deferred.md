# ADR-008 Deferred: AI assistant and deployment

Status: accepted at gate G3 (signed 18/11/2026 by David).

## Decision
- **AI assistant (T51):** not designed now. When it is, it can only read releases through the API v3 (no other data path), and must cite the provenance of every number it repeats. It is optional and comes after T50.
- **Deployment:** none. The NASA evaluation is in progress, and the Azure resources (`infra/terraform/`) are frozen. v3 runs on the local Docker stack only. Whether and how v3 is deployed (including the new internal service and the release files) is David's decision after the evaluation, recorded then as a new ADR.
- **Retiring v2:** decided in T50, with the v3 validation report.
