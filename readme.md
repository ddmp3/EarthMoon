# 🛰️ Cyber&Space Montréal — NASA Space Apps Challenge 2026

## 🌍 Le défi

**Identifier sur Terre des sites analogues aux futures bases permanentes sur la Lune et sur Mars.**

À partir des données ouvertes de la NASA et d'autres agences spatiales, identifier et caractériser de nouveaux sites terrestres analogues (déserts, régions polaires, terrains volcaniques ou arides, grottes, etc.) partageant des conditions avec la surface lunaire ou martienne, puis présenter les résultats sous forme de carte, de visualisation ou d'outil.

## 🎯 Public cible

> **À définir** : identifier les personnes à qui notre application est destinée.

## 💡 Concept de l'application

Une **application web visuelle** permettant à l'utilisateur :

- soit de **choisir un scénario prédéfini** ;
- soit de **définir ses propres critères** de recherche.

### Scénarios prédéfinis (3 à 4)

1. **Entraînement** : entraîner des rovers ou d'autres équipements.
2. **Calibration** : calibrer des instruments scientifiques.
3. **Implantation humaine** : analyser la structure géologique du sol et du sous-sol pour favoriser l'installation d'une base.
4. **Ressources (proposé)** : repérer les sites analogues pour la glace et l'hydrogène (extraction de ressources sur place, ISRU).

### Moteur de comparaison

> **Proposition, à valider par l'équipe.**

- Cible de référence : le pôle Sud lunaire (profil de température Diviner, pente et relief LOLA).
- Chaque site candidat est représenté par un vecteur de variables normalisées (température, pente, relief, puis minéralogie).
- Le scénario choisi fixe le poids de chaque variable.
- Score de similarité = 1 − distance pondérée normalisée, avec un détail par variable (ce qui est similaire, ce qui ne l'est pas, à quoi le site servirait).
- Validation : les analogues reconnus (Atacama, Dry Valleys, Haughton, Mauna Kea, Rio Tinto, Svalbard, Islande) doivent obtenir un score élevé, et un témoin négatif (Amazonie) un score bas.
- Bonus : rugosité radar (SAR) sur 1 ou 2 sites seulement.

## 📡 Sources de données

Liste détaillée, avec l'accès API et le statut de vérification : **[docs/sources.md](docs/sources.md)**.

Socle : LOLA et Diviner (Lune), Copernicus DEM, MODIS LST et NASA POWER (Terre). En complément : EMIT ou ASTER pour la minéralogie.

Principes retenus :

- **Aucun stockage de données** côté application.
- **Accès par API uniquement** aux sources.
- Exception assumée : le profil de la cible (Lune, Mars) est précalculé une fois et livré comme petit fichier de configuration versionné. Ce sont des paramètres, pas un jeu de données.

## 🛠️ Stack technologique

- **TypeScript**
- **React**
- **OpenAPI**

### Option

- Proposer un **accès API** à notre application.

## 🤖 Intelligence artificielle utilisée

- **Claude** (Anthropic) : modèle(s) à préciser parmi Haiku, Sonnet, Opus et Fable.
- **Microsoft Copilot**

## 👥 Équipe

Équipe locale **Cyber&Space Montréal**.
