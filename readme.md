# 🛰️ Cyber&Space Montréal — NASA Space Apps Challenge 2026

## 🌍 Le défi

**Identifier sur Terre des sites analogues aux futures bases permanentes sur la Lune et sur Mars.**

À partir des données ouvertes de la NASA et d'autres agences spatiales, identifier et caractériser des sites terrestres analogues (déserts, régions polaires, terrains volcaniques ou arides, grottes, etc.), expliquer **ce qui les rend analogues et ce qui ne l'est pas**, puis présenter les résultats sous forme de carte, de visualisation ou d'outil.

Objectif : ne pas simplement retrouver les analogues connus, mais **faire émerger des sites peu étudiés**.

## 🎯 Public cible (proposition, à valider)

- **Principal** : scientifiques et ingénieurs de mission (choix de sites de test pour les rovers, les instruments et les opérations humaines).
- **Secondaire** : enseignants, étudiants et grand public (vulgarisation).

## 💡 Concept de l'application

Une **application web visuelle** permettant à l'utilisateur :

- soit de **choisir un scénario prédéfini** ;
- soit de **définir ses propres critères** de recherche.

Pour chaque site proposé, l'application affiche :

- un **score global** de similarité ;
- un **score par critère** ;
- ce qui **correspond** et ce qui **ne correspond pas**.

## 🧭 Scénarios prédéfinis

Chaque scénario comporte la même liste de tâches :

- [ ] Établir le moteur de comparaison.
- [ ] Établir la liste des paramètres du cas d'usage, avec pour chacun :
  - les valeurs types ou les intervalles de valeurs ;
  - les sources de données où les obtenir.
- [ ] Comprendre comment comparer les sources entre elles.

| # | Scénario | Variables principales | Lune / Mars | Terre |
|---|---|---|---|---|
| 1 | **Entraînement** de rovers et d'autres équipements | pente, relief, rugosité | LOLA / MOLA | Copernicus DEM, ICESat-2 |
| 2 | **Calibration** d'instruments scientifiques | minéralogie, thermique, lithologie | Diviner / CRISM, THEMIS | EMIT, ASTER, GLiM |
| 3 | **Implantation humaine** (sol et sous-sol) | température, sous-sol, cavités | Diviner, pits LROC / grottes USGS | MODIS LST, NASA POWER, GVP |
| 4 | **Ressources** (glace, ISRU) | hydrogène, glace enfouie | LEND, Mini-RF / SHARAD | ArcticDEM, Sentinel-1 |

Filtre commun à tous les scénarios : **exclusion des zones végétalisées** (MODIS NDVI).

## ✅ Validation

- Les analogues reconnus doivent obtenir un score élevé : Atacama, Dry Valleys, cratère Haughton, Mauna Kea, Rio Tinto, Svalbard, Islande.
- Un témoin négatif (Amazonie) doit obtenir un score bas.

## 📡 Sources de données

La liste complète des sources, leurs modes d'accès et leur statut de test est maintenue dans [docs/sources.md](docs/sources.md).

Principes retenus :

- **Aucun stockage de données** côté application.
- **Accès par API uniquement** (REST, STAC, WMTS, lecture partielle de COG).
- **Profil de référence Lune / Mars** : calculé une seule fois hors ligne, puis livré sous forme d'un fichier JSON versionné.
- **Sécurité** : le jeton Earthdata Login ne doit **jamais** être commité.

## ⚠️ Limites de l'analogie terrestre

La Terre ne reproduit pas :

- la gravité réduite ;
- le vide lunaire ;
- l'atmosphère ténue de Mars ;
- l'environnement de rayonnement.

La biologie et l'habitabilité sont hors du périmètre de ce projet.

## 🛠️ Stack technologique

- **TypeScript**
- **React**
- **OpenAPI**

Option : proposer un **accès API** à notre application.

## 🤖 Intelligence artificielle utilisée

- **Claude** (Anthropic) : modèle(s) à préciser.
- **Microsoft Copilot**

## 👥 Équipe

Équipe locale **Cyber&Space Montréal**.
