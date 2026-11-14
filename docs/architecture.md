# Architecture

Même modèle que meteormadness (NASA Space Apps 2025) : front statique, API conteneurisée, infrastructure Terraform sur Azure.

```
Navigateur ──► Azure Static Web App (React)
                   │  appels HTTPS (VITE_API_URL)
                   ▼
              Azure Container App (API Node/TS, OpenAPI)
                   │  cache mémoire, aucune base de données
                   ▼
   NASA POWER · Copernicus DEM (COG) · Planetary Computer (MODIS)
   USGS Earthquakes · Smithsonian GVP · (fonds de carte : Moon Trek WMTS, appelé par le navigateur)
```

## Arborescence cible du repo

```
apps/
  api/          API Node.js + TypeScript + Express (ES modules), Dockerfile, openapi.yaml
  web/          Front React + TypeScript + Vite + Tailwind + Leaflet
data/
  reference/moon-south-pole.json   profil de référence lunaire (paramètres)
  candidates.json                  points candidats du MVP
docs/           sources, scénarios, architecture, plan projet
infra/terraform Infrastructure Azure (Terraform) + deploy.sh
```

## API (contrat OpenAPI à écrire en premier)

| Méthode | Route | Rôle |
|---|---|---|
| GET | `/api/health` | sonde de santé (Container Apps) |
| GET | `/api/parameters` | catalogue des paramètres (mode 4) |
| GET | `/api/modes` | modes 1 à 3 et leurs critères prédéfinis |
| GET | `/api/reference/moon` | profil de référence lunaire |
| POST | `/api/analyze` | entrée : `mode` ou `criteria[]` ; sortie : sites classés avec score global et score par critère |
| GET | `/api/sites/{id}` | fiche détaillée d'un site (valeurs brutes, correspond / ne correspond pas) |
| GET | `/api/docs` | documentation Swagger UI |

Chaque source est isolée dans un adaptateur (`apps/api/src/sources/<source>.ts`) qui renvoie des valeurs du catalogue (`docs/scenarios.md`). Le moteur de score ne connaît que le catalogue, pas les sources : on pourra ajouter Mars en phase 2 sans le modifier.

## Infrastructure Azure (reprise de meteormadness)

| Ressource | Paramètre |
|---|---|
| Souscription | `dev-meteormadness` (DEV uniquement, aucun déploiement en PROD) |
| Région | `canadacentral` (Static Web App : `eastus2`, régions limitées) |
| Resource Group | `rg-cyberspace-analogues-<suffixe>` |
| Log Analytics | SKU `PerGB2018`, rétention 30 jours |
| Container Registry | SKU `Basic` |
| Container Apps Environment + Container App API | 0,5 vCPU, 1 Gi, 1 à 5 réplicas, port 3001 |
| Static Web App | SKU `Free` |

Déploiement : `infra/terraform/deploy.sh` (init, validate, plan, confirmation, apply, build et push de l'image, mise à jour de la Container App). Voir [infra/terraform/README.md](../infra/terraform/README.md).

## Sécurité (revue Xavier)

- Aucun secret dans le repo : `.env`, `*.tfstate`, `tfplan` sont ignorés par git.
- Le state Terraform reste local pour le hackathon : un seul membre (David) applique l'infrastructure.
- L'API limite le débit (`express-rate-limit`) et restreint CORS au domaine de la Static Web App.
- Point connu hérité de meteormadness : l'accès admin de l'ACR est activé. Acceptable pour le hackathon ; à remplacer par une identité managée ensuite.
