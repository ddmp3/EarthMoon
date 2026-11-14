# Infrastructure Azure (Terraform)

Reprise du modèle meteormadness : Resource Group, Log Analytics, Container Registry, Container Apps (API) et Static Web App (front), en `canadacentral`, souscription `dev-meteormadness`.

## Prérequis

`terraform` (>= 1.0), `az` (connecté avec `az login`), `docker`, `node`/`npm`.

## Déployer

```bash
./infra/terraform/deploy.sh
```

Le script : choisit la souscription DEV, exécute `terraform init/validate/plan`, demande confirmation, applique, construit et pousse l'image de l'API (tag = commit git), met à jour la Container App, construit le front avec `VITE_API_URL` et le déploie sur la Static Web App.

## Règles

- **Un seul membre applique l'infrastructure** (David) : le state Terraform est local et n'est jamais commité.
- DEV uniquement : aucun déploiement sur la souscription PROD.
- Détruire après le hackathon : `terraform -chdir=infra/terraform destroy`.
