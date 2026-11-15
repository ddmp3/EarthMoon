# Azure infrastructure (Terraform)

Resource Group, Log Analytics, Container Registry, Container Apps (API) and Static Web App (front end) in `canadacentral`, subscription `dev`.

**Live since 15 November 2026:** front end https://jolly-rock-05f5cb20f.3.azurestaticapps.net · API docs https://ca-api-rtzkc5ya.bluesky-19c5e80c.canadacentral.azurecontainerapps.io/api/docs

## Update the live site from any machine (no Terraform state needed)

```bash
az login                         # once per machine
./infra/update.sh                # API and front end
./infra/update.sh --api-only
./infra/update.sh --web-only
```

`infra/update.sh` finds the existing resources with Azure CLI (subscription `dev`), builds and pushes the API image, updates the Container App, then builds and deploys the front end. It needs `az`, `docker` (running) and Node 22+, and it does **not** read the Terraform state. Use it for every code or data update. On an Apple Silicon Mac the API image is built for `linux/amd64`, which is slower than a native build.

Terraform (`deploy.sh` below) is only needed to create or change the infrastructure itself.

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

- The Terraform state is local (`infra/terraform/terraform.tfstate`, git-ignored) and never committed: it holds the registry password and the front-end deployment token in clear text. It lives on the machine that created the infrastructure (WSL on David's PC). Running `deploy.sh` from a machine without it would try to create a second copy of everything; use `infra/update.sh` instead.
- DEV only: no deployment to the PROD subscription.
- Delete everything after the hackathon: `terraform -chdir=infra/terraform destroy` from the machine that holds the state, or, from any machine, `az group delete --subscription dev --name rg-cyberspace-analogues-rtzkc5ya`.
