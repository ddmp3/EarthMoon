# Azure infrastructure (Terraform)

Resource Group, Log Analytics, Container Registry, Container Apps (API) and Static Web App (front end) in `canadacentral`, subscription `dev`.

**Live since 15 November 2026:** front end https://jolly-rock-05f5cb20f.3.azurestaticapps.net · API docs https://ca-api-rtzkc5ya.bluesky-19c5e80c.canadacentral.azurecontainerapps.io/api/docs

## Requirements

`terraform` (>= 1.0), `az` (signed in with `az login`), `docker`, `node`/`npm`.

## Deploy

```bash
./infra/terraform/deploy.sh          # asks for confirmation
./infra/terraform/deploy.sh --yes    # deployment already decided
```

The script targets the `dev` subscription without changing the Azure CLI default. It creates the base infrastructure, builds and pushes the API image (tag = git commit), creates or updates the Container App with it, then builds the front end with `VITE_API_URL` and the security headers and deploys it to the Static Web App. It can be re-run for updates.

After a deployment: `python3 tools/validation/e2e.py --web <front> --api <api>`.

## Rules

- The Terraform state is local (`infra/terraform/terraform.tfstate`, git-ignored) and never committed. Copy it by hand before deploying from another machine, otherwise Terraform will try to recreate everything.
- DEV only: no deployment to the PROD subscription.
- Destroy after the hackathon: `terraform -chdir=infra/terraform destroy`.
