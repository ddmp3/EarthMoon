# Infrastructure Azure (Terraform)

Reprise du modèle meteormadness : Resource Group, Log Analytics, Container Registry, Container Apps (API) et Static Web App (front), en `canadacentral`, souscription `dev`.

**En ligne depuis le 15 novembre 2026** : front https://jolly-rock-05f5cb20f.3.azurestaticapps.net · API https://ca-api-rtzkc5ya.bluesky-19c5e80c.canadacentral.azurecontainerapps.io/api/docs

## Prérequis

`terraform` (>= 1.0), `az` (connecté avec `az login`), `docker`, `node`/`npm`.

## Déployer

```bash
./infra/terraform/deploy.sh          # demande une confirmation
./infra/terraform/deploy.sh --yes    # déploiement déjà décidé
```

Le script cible la souscription `dev` sans changer celle par défaut d'Azure CLI. Il crée d'abord l'infrastructure de base, construit et pousse l'image de l'API (tag = commit git), crée ou met à jour la Container App avec cette image, puis construit le front avec `VITE_API_URL` et les en-têtes de sécurité et le déploie sur la Static Web App. Il est relançable pour les mises à jour.

Après un déploiement : `python3 tools/validation/e2e.py --web <front> --api <api>`.

## Règles

- **Un seul membre applique l'infrastructure** (David) : le state Terraform est local (`infra/terraform/terraform.tfstate`, ignoré par git) et n'est jamais commité. Il se trouve sur le poste qui a déployé (WSL du PC de David) : le copier à la main avant de déployer depuis une autre machine, sinon Terraform voudra tout recréer.
- DEV uniquement : aucun déploiement sur la souscription PROD.
- Détruire après le hackathon : `terraform -chdir=infra/terraform destroy`.
