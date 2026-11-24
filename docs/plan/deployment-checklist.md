# Deployment checklist for v3 (not executed)

**Nothing on this page has been run.** Deployment is David's decision, after the NASA evaluation of the original project, whose live sites (v1) must not be touched. Until then, the hard rule of `CLAUDE.md` applies: no `terraform apply`, no `az`, no `deploy.sh`.

## Before anything
- [ ] The NASA evaluation is over, and David decides to deploy.
- [ ] Decide whether v3 replaces the v1 sites or gets new ones (the v1 URLs are cited in the hackathon submission).
- [ ] Estimate the monthly cost: API, discovery service, storage of the releases, and refresher. Each recompute is costed separately from its pre-analysis (T52b): CPU hours times the machine price.

## Infrastructure to write (Terraform, `infra/terraform/`)
- [ ] **Discovery service** (`apps/discovery`). Internal ingress only, no public endpoint.
  - Memory: about 6.2 GiB with the Moon and Mars releases loaded (measured locally on 23/11/2026).
  - This exceeds the 4 GiB of the Container Apps consumption profile (to check on the Azure page), so it needs a dedicated workload profile or another host.
- [ ] **Releases storage.** Today's local folder becomes an Azure Files share or Blob storage. Measure its size first: the Mars map tiles alone are 459 MB in 87,419 files (tiles log of 23/11/2026). The share or storage is:
  - mounted read-only in the API and the discovery service;
  - writable by the refresher only.
- [ ] **Refresher:** a Container Apps job on a schedule, not a long-running app.
  - Outbound network to the catalogue hosts only, which the code already checks.
  - Secrets (CDS key, Earthdata login, when needed) in Key Vault, never in variables or images.
- [ ] **API:** `RELEASES_DIR`, `DISCOVERY_URL` (internal), `FRONTEND_URL` for CORS, and the rate limit kept at 120 per minute per IP.
- [ ] **Static Web App:** `VITE_API_URL` set at build time to the new API URL.

## Checks after a deployment (on a staging environment first)
- [ ] `GET /api/health`, `GET /api/v3/releases`, and `GET /api/v3/status?release=mars`.
- [ ] `tools/validation/e2e.py` against the staging URLs, and the browser audit on desktop and phone.
- [ ] The discovery service is not reachable from outside.
- [ ] The refresher writes `freshness.json` and never starts a recompute.
- [ ] Logs hold no secret and no personal data. Log Analytics keeps them 30 days.

## Rollback
- [ ] The previous container images and the previous `index.json` are kept. A release switch is atomic, and the last 4 releases of each body stay readable.
