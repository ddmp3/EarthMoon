# API — guide d'intégration

Ce guide dit **comment appeler l'API et ce dont elle a besoin**, pour que chacun (et son assistant IA) puisse s'y brancher sans attendre. Le contrat complet est dans [`openapi.yaml`](openapi.yaml) et [`docs/contrats.md`](../../docs/contrats.md).

## En bref

- Serveur Express (Node 22, TypeScript, ES modules), port **3001**.
- Il appelle le moteur de score de David (`src/analyze/analyze.ts`) **sans le modifier**.
- **Aucune clé API, aucun compte** : toutes les sources du MVP sont publiques.
- Une source en panne ne casse jamais une réponse : ses paramètres valent `null` et le critère reçoit le verdict `missing`.

## Démarrer

```bash
cd apps/api
npm install
npm test            # 96 tests
npm run typecheck
npm run dev         # vraies sources, http://localhost:3001/api/docs
```

Avec les valeurs d'exemple de `data/fixtures/` (surtout fictives, **jamais pour la démo**) :

```bash
USE_FIXTURES=1 npm run dev          # macOS / Linux
$env:USE_FIXTURES=1; npm run dev    # Windows PowerShell
```

Vérifier les vraies sources depuis sa machine (appelle NASA POWER et USGS pour Haughton) :

```bash
npm run check:sources
```

Production : `npm run build` puis `npm start`.

## Variables d'environnement

| Variable | Défaut | Rôle |
|---|---|---|
| `PORT` | `3001` | Port d'écoute (défini par Terraform) |
| `FRONTEND_URL` | — | Origine autorisée par CORS (définie par Terraform) |
| `EXTRA_ORIGINS` | — | Autres origines autorisées, séparées par des virgules |
| `DATA_DIR` | `<racine du dépôt>/data` | Dossier des candidats, fixtures et profil lunaire |
| `USE_FIXTURES` | non | `1` : valeurs d'exemple au lieu des vraies sources |
| `RATE_LIMIT_PER_MINUTE` | `120` | Requêtes par minute et par IP |
| `NODE_ENV` | — | Hors `production`, `http://localhost:5173` est aussi autorisé par CORS |

Bonus (pas encore codé) : l'explication d'un site par Claude demandera une clé, à mettre dans un **secret de la Container App**, jamais dans le dépôt.

## Routes

| Méthode | Route | Réponse |
|---|---|---|
| GET | `/api/health` | `{ "status": "ok" }` |
| GET | `/api/modes` | `{ "modes": [{ id, name, criteria }] }` (modes 1 à 3) |
| GET | `/api/parameters` | `{ "parameters": [{ id, label, unit, source, lunar }] }` |
| GET | `/api/reference/moon` | contenu de `data/reference/moon-south-pole.json` |
| POST | `/api/analyze` | sites classés (voir ci-dessous) |
| GET | `/api/sites/{id}?mode=robotics` | un site, plus `values` (valeurs brutes) et `sources` |
| GET | `/api/docs` | Swagger UI ; le contrat brut est sur `/api/openapi.json` |

### `POST /api/analyze`

Envoyer **soit** `mode`, **soit** `criteria` (mode 4), jamais les deux.

```bash
curl -X POST http://localhost:3001/api/analyze \
  -H "content-type: application/json" \
  -d '{"mode":"robotics"}'
```

```json
{ "criteria": [{ "param": "slope_mean", "min": 5, "max": 15, "tolerance": 10, "weight": 3 }], "bareSoilOnly": false }
```

Réponse :

```json
{
  "mode": "robotics",
  "sites": [
    {
      "id": "haughton", "name": "Cratère Haughton (île Devon)", "lat": 75.38, "lon": -89.67, "role": "validation",
      "total": 90,
      "criteria": [
        { "param": "slope_mean", "value": 7.5, "score": 1, "verdict": "match" },
        { "param": "volcano_distance", "value": null, "score": 0, "verdict": "missing" }
      ]
    }
  ]
}
```

À savoir pour l'interface :

- `total` est sur 100. Les sites sont triés par `total` décroissant.
- `verdict` : `match` (≥ 0,7), `partial` (0,4 à 0,7), `mismatch` (< 0,4), `missing` (valeur absente, exclue du total).
- Filtre « sol nu » actif par défaut (`bareSoilOnly: true`) : un site végétalisé **reste dans la liste**, avec `total: 0`, `"excluded": "vegetation"`, en dernier.
- Erreurs : toujours `{ "error": "message" }`, avec 400 (requête invalide), 404, 413 (corps trop gros), 429 (trop de requêtes), 500.

## Ce dont l'API a besoin de chacun

### Ouassim — `data/candidates.json`

Format de `docs/contrats.md` §1 : un tableau de `{ id, name, lat, lon, terrain, role }`.

- `id` : minuscules, chiffres et tirets seulement, unique. `lat` entre -90 et 90, `lon` entre -180 et 180.
- `role` : `validation`, `negative` ou `candidate` (défaut si absent : `candidate`).
- Une entrée invalide est **ignorée** et signalée dans les journaux ; les autres sont gardées.
- Tant que le fichier n'existe pas, l'API utilise les 3 sites de `data/fixtures/site-values.json`.

### Jesus — `data/candidates-geometry.json` (pente, rugosité, altitude)

Calculé hors ligne à partir du Copernicus DEM, une fois la liste de sites prête :

```bash
pip install numpy rasterio
python tools/precompute/enrich_candidates.py data/candidates.json -o data/candidates-geometry.json
```

Le script est sur la branche `search-engine-geolocalization` (`tools/precompute/`). Il recopie chaque site et ajoute :

```json
"precomputed": { "elevation": 173.0, "slope_mean": 7.5, "slope_max": 24.0, "roughness": 18.0 }
```

Sans ce fichier, `slope_mean`, `slope_max`, `roughness` et `elevation` sont `missing`.

### David — déploiement

- Le Dockerfile se construit depuis la **racine du dépôt** (l'image embarque `data/`). Dans `infra/terraform/deploy.sh` :
  `docker build --platform linux/amd64 -f "$ROOT_DIR/apps/api/Dockerfile" -t "$IMAGE" "$ROOT_DIR"`
- `PORT`, `NODE_ENV` et `FRONTEND_URL` viennent déjà de Terraform. Sonde de santé : `/api/health` (hors limitation de débit).
- Si un intervalle, un paramètre ou la forme d'une réponse change dans `src/scoring/` ou `src/analyze/`, mettre à jour `openapi.yaml` dans la même PR (un test compare la liste des paramètres).

### François — front

- `VITE_API_URL` = URL de la Container App. En local : `http://localhost:3001`.
- Le client typé peut être généré depuis `openapi.yaml` ou `/api/openapi.json`.
- CORS n'autorise que `FRONTEND_URL` (et `localhost:5173` hors production).

## État des sources

| Source | Paramètres | État |
|---|---|---|
| Coordonnées | `latitude_abs` | Branché |
| NASA POWER | `t2m_mean`, `t2m_min`, `t2m_max`, `wind`, `humidity`, `precipitation`, `solar` | Branché ; testé avec des réponses simulées, **à vérifier en réel** (`npm run check:sources`) |
| USGS Earthquake Catalog | `quake_count` | Branché ; même remarque |
| Copernicus DEM | `slope_mean`, `slope_max`, `roughness`, `elevation` | Précalculé ; attend `data/candidates-geometry.json` |
| MODIS (Planetary Computer) | `ndvi`, `lst_day`, `lst_night`, `lst_amplitude` | **À faire** |
| Smithsonian GVP | `volcano_distance` | **À faire** |

Conséquence tant que MODIS manque : pas de `ndvi`, donc le filtre « sol nu » n'écarte aucun site en mode réel (l'Amazonie n'est pas exclue).

## Ajouter un connecteur (MODIS, GVP…)

Un connecteur est une fonction `({ lat, lon }) => Promise<ParamValues>` (`docs/contrats.md` §3).

```ts
// src/sources/gvp.ts
import type { Connector } from "../analyze/analyze.js";
import { fetchJson } from "./http.js";
import type { FetchJsonOptions } from "./http.js";

export function createGvpConnector(options: FetchJsonOptions = {}): Connector {
  return async ({ lat, lon }) => {
    const body = await fetchJson(/* URL de docs/sources.md */ "", options);
    return { volcano_distance: /* distance en km, ou null */ null };
  };
}
```

Règles :

1. Ne renvoyer **que ses paramètres**, avec les identifiants du catalogue (`docs/scenarios.md`). Valeur indisponible : `null`.
2. En cas d'échec (réseau, réponse inattendue), **lancer une erreur** : `analyze()` l'ignore et les critères passent à `missing`.
3. Utiliser `fetchJson` (délai maximal, nouvelles tentatives sur 5xx, utile pour le 502 de Planetary Computer) et envelopper le connecteur dans `withCache`.
4. L'enregistrer dans `src/sources/index.ts` (connecteur + nom affiché) et mettre à jour le tableau ci-dessus.
5. Ajouter des tests avec un `fetchImpl` simulé, comme dans `tests/sources.test.ts`. Aucun test ne doit appeler le réseau.

## Pour les assistants IA (Claude, Copilot)

- Lire d'abord `docs/contrats.md`, `docs/scenarios.md`, `docs/sources.md` et ce fichier.
- Ne pas modifier `src/scoring/` ni `src/analyze/` sans l'accord de David.
- Un changement de contrat (route, champ, paramètre) se fait dans une PR dédiée, avec `openapi.yaml` et `docs/contrats.md` à jour.
- Avant de proposer une PR : `npm test` et `npm run typecheck` doivent passer.
- Aucun secret, aucune donnée lourde (rasters) dans le dépôt.
- Ne jamais inventer une valeur de source : si une source ne répond pas, la valeur est `null`.
