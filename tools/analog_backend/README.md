# analog_backend — premier jet d'analyse (référence, hors application)

Premier prototype d'analyse en Python, écrit avant l'architecture actuelle du projet.
**Il ne fait pas partie de l'application** (l'API reste en Node/TS, voir `docs/architecture.md`).
Il est conservé ici comme référence et pour une vérification indépendante du classement.

## Ce que fait le prototype

Pipeline : audit des entrées → ingestion → détection de lacunes d'observation → similarité Terre/Lune → export JSON.
Il calcule pente, rugosité et fraction d'ombre sur une base géométrique commune (Terre et Lune), compare les
variables thermiques par quantile propre à chaque planète, et produit un indice de similarité multicritère (MCSI).

## Différences avec le projet actuel

- Entrées : NLDAS (États-Unis continentaux) et RCM (SAR). Le projet utilise NASA POWER, Copernicus DEM, MODIS, USGS et GVP.
- Il traite des grilles complètes ; le projet évalue une liste de points candidats.
- Score : distance pondérée + cosinus vers un vecteur cible lunaire ; le projet utilise intervalle cible + tolérance + poids (`docs/scenarios.md`).
- `schema/analogs.ts` est un format exploratoire, **pas** le contrat de l'API (OpenAPI à écrire en premier).
- Le Dockerfile n'est pas inclus.

## Ce qui est réutilisable

- `analog_finder/lro.py` + `p5_similarity.build_target_from_rasters` : profil de référence lunaire (LOLA + Diviner)
  pour `data/reference/moon-south-pole.json`.
- `p2_ingest.slope_roughness_arrays` : pente et rugosité (voir aussi `tools/precompute/`).
- `p3_gaps.py` / `p4_model.py` : zones critiques et nouveauté, pistes pour la phase 2.

## État des tests

`tests/test_smoke.py` passe sur des données **synthétiques** générées par `tests/make_fixtures.py`.
Le pipeline n'a pas été exécuté sur de vraies données LRO, NLDAS ou RCM.

```
pip install -r requirements.txt -r requirements-dev.txt
pytest
```
