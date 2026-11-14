# Expérience utilisateur : après le MVP

> **Statut : à faire une fois le MVP livré** (dim 15 nov après la soumission, ou phase 2). Le MVP reste la priorité : carte, fiche site, 4 modes fonctionnels.

## Intention

L'application ne doit pas ressembler à un tableau de bord de données. Elle doit faire **voir** et **ressentir** pourquoi un coin de la Terre ressemble au pôle Sud lunaire, et laisser l'utilisateur explorer en direct. Les tableaux restent en détail secondaire (panneau « données brutes » replié).

## Principe technique qui rend tout dynamique

Le moteur de score (`apps/api/src/scoring/`) est une fonction pure, sans dépendance. Le front l'importe et **recalcule le classement dans le navigateur** :

- l'API ne sert qu'à charger une fois les valeurs brutes des sites (`GET /api/sites` avec `values`) ;
- chaque changement de mode, de curseur ou de poids recalcule tous les scores en quelques millisecondes, sans appel réseau ;
- un seul code de score pour le front et l'API : pas de divergence possible.

Prérequis : une route qui renvoie les valeurs brutes de tous les sites (à ajouter au contrat), et le partage du dossier `scoring/` entre `apps/api` et `apps/web` (paquet commun ou import relatif).

## Éléments, par ordre de priorité

| # | Élément | Ce que voit l'utilisateur | Technique pressentie | Effort |
|---|---|---|---|---|
| 1 | Re-classement en direct | Les sites montent et descendent dès qu'on touche un réglage | moteur importé côté front, zustand | S |
| 2 | Mode 4 en curseurs | Curseurs d'intervalle et de poids par paramètre, effet immédiat sur la carte | composant range double, debounce léger | S |
| 3 | Modes présentés comme des missions | Cartes illustrées « Tester un rover », « Calibrer un sismomètre », « Fonder une colonie », avec l'enjeu en une phrase | composants React, textes de Yann | S |
| 4 | Signature radar | Graphique en étoile du site superposé au profil lunaire : on voit d'un coup d'œil où il colle et où il s'écarte | Recharts ou visx (RadarChart) | M |
| 5 | Vue « jumeau lunaire » | Écran partagé : imagerie du site (NASA GIBS) à gauche, région du pôle Sud (Moon Trek WMTS) à droite, jauges d'écart par paramètre au centre | Leaflet × 2, tuiles GIBS et Moon Trek | M |
| 6 | Sites peu étudiés mis en avant | Badge « découverte », fiche narrative (pourquoi ce site, ce qu'on pourrait y tester) | contenu d'Ouassim, explication par Claude (bonus API) | M |
| 7 | Globe 3D | La Terre tourne, les sites sont des points lumineux dont la taille et la couleur suivent le score ; changer de mode les anime | globe.gl (three.js) | L |

S = quelques heures, M = une demi-journée, L = une journée.

## Règles de conception

- **Une idée par écran** : choisir une mission, explorer la carte, comprendre un site.
- **Le score se voit avant de se lire** : couleur, taille, position ; le chiffre vient en second.
- **Toujours relier à la Lune** : chaque valeur terrestre est montrée à côté de sa référence lunaire (`data/reference/moon-south-pole.json`).
- **Honnêteté** : une valeur manquante est montrée comme manquante (verdict `missing`), jamais masquée ; les valeurs fictives des fixtures n'apparaissent jamais.
- **Accessible** : couleurs lisibles en clair et en sombre, contrastes suffisants, navigation au clavier, animations désactivées si `prefers-reduced-motion`.

## Répartition proposée

- **Yann** : parcours et maquettes des éléments 1 à 6, textes des missions.
- **François** : éléments 1 à 5, puis 7.
- **Ouassim** : contenu des fiches « découverte » (élément 6).
- **Jesus** : route des valeurs brutes de tous les sites, explication par Claude.
- **David** : partage du moteur entre API et front, arbitrage de l'ordre.
