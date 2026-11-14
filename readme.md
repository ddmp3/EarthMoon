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

## 🧭 Scénarios prédéfinis (3 à 4)

### 1. Entraînement de rovers et d'autres équipements

**À faire :**

- [ ] Établir le moteur de comparaison.
- [ ] Établir la liste des paramètres du cas d'usage, avec pour chacun :
  - les valeurs types ou les intervalles de valeurs ;
  - les sources de données où les obtenir.
- [ ] Comprendre comment comparer les sources entre elles.

### 2. Calibration d'instruments scientifiques

**À faire :**

- [ ] Établir le moteur de comparaison.
- [ ] Établir la liste des paramètres du cas d'usage, avec pour chacun :
  - les valeurs types ou les intervalles de valeurs ;
  - les sources de données où les obtenir.
- [ ] Comprendre comment comparer les sources entre elles.

### 3. Implantation humaine

Analyser la structure géologique du sol et du sous-sol pour favoriser l'installation d'une base.

**À faire :**

- [ ] Établir le moteur de comparaison.
- [ ] Établir la liste des paramètres du cas d'usage, avec pour chacun :
  - les valeurs types ou les intervalles de valeurs ;
  - les sources de données où les obtenir.
- [ ] Comprendre comment comparer les sources entre elles.

### 4. *(À définir)*

**À faire :**

- [ ] Définir le scénario.
- [ ] Établir le moteur de comparaison.
- [ ] Établir la liste des paramètres du cas d'usage, avec pour chacun :
  - les valeurs types ou les intervalles de valeurs ;
  - les sources de données où les obtenir.
- [ ] Comprendre comment comparer les sources entre elles.

## 📡 Sources de données

La liste complète des sources, leurs modes d'accès et leur statut de test est maintenue dans docs/sources.md.

Principes retenus :

- **Aucun stockage de données** côté application.
- **Accès par API uniquement** aux sources (REST, STAC, WMTS, lecture partielle de COG par requêtes HTTP Range).
- **Profil de référence Lune / Mars** : calculé une seule fois hors ligne, puis livré sous forme d'un petit fichier JSON versionné (des paramètres, pas un jeu de données).
- **Sites candidats sur Terre** : interrogés en direct par API.
- **Sécurité** : le jeton Earthdata Login ne doit **jamais** être commité.

Sources prioritaires (socle) :

| Source | Corps | Variables |
|---|---|---|
| LRO LOLA | Lune | relief, pente |
| LRO Diviner | Lune | température de surface |
| Copernicus DEM GLO-30 | Terre | relief, pente |
| MODIS LST | Terre | température de surface |
| NASA POWER | Terre | température de l'air, vent, ensoleillement |

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
