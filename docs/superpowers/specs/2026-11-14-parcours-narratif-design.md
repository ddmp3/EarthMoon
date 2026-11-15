# Parcours narratif de recherche de sites analogues — conception

Date : 2026-11-14 · Auteur : Yann (expérience utilisateur) · Statut : à valider

## Intention

L'utilisateur est une personne ou une équipe qui **prépare une mission lunaire**. Elle cherche le meilleur site sur Terre pour y mener des tests avant la mission, et doit **en choisir un**.

La maquette actuelle (`docs/maquettes/index.html`) est une boîte à outils : choix du site lunaire, scénario, liste, globes, fiches, mais aucun fil ne relie ces écrans, et la comparaison Lune-Terre est cachée derrière une case « Superposer » dans la fiche d'un site.

On veut que l'interface **raconte la recherche comme une histoire**, avec un fil logique et naturel, et que **la comparaison entre la Lune et la Terre devienne le cœur de l'expérience**.

À la fin, l'équipe a entre les mains, pour le site retenu : ses caractéristiques, ses analogies et ses différences avec le site lunaire, et donc **la portée des tests possibles et leurs limites**.

## Objectifs

- Un parcours en 6 chapitres, toujours dans le même ordre, qui suit le raisonnement d'une équipe de mission : la Lune d'abord, la Terre ensuite.
- Une comparaison des **3 meilleurs candidats** face au site lunaire, avec leurs forces et leurs faiblesses.
- Un **dossier final** qui traduit chaque analogie ou différence en portée de test.
- La possibilité de revenir à tout moment à un chapitre précédent pour changer un choix.

## Hors périmètre

- La présentation au jury et la démo.
- Le partage, l'impression et le téléchargement du dossier : pour le MVP, il est **seulement consulté à l'écran**.
- Les vraies données (les valeurs restent fictives ou indicatives dans la maquette).
- Le développement de la vraie application (`apps/web`), qui revient à François-Xavier à partir de la maquette.
- Mars.

## Ce qui ferait échouer le projet, même s'il fonctionne

- Un tunnel : l'utilisateur ne peut pas revenir changer le site lunaire ou le scénario sans tout recommencer.
- Une comparaison qui redevient secondaire (cachée dans une fiche ou derrière une option).
- Des animations qui ralentissent une équipe qui travaille : chaque transition doit rester courte et ne jamais bloquer une action.
- La perte de ce que la maquette offre déjà : critères libres, aide, glossaire, états de chargement et d'erreur, aperçu mobile, annotations API.

## Contraintes

- La maquette reste **un seul fichier HTML** (`docs/maquettes/index.html`), publié aussi comme artefact claude.ai : scripts uniquement depuis les CDN autorisés (cdnjs, jsDelivr, unpkg), aucune image externe.
- On garde les briques existantes : thème « salle de contrôle », globes three.js (Terre avec contours ECharts, Lune générée), moteur de score de `scenarios.md`, adaptation des critères au site lunaire, 14 sites lunaires, 12 sites terrestres fictifs, 18 paramètres et leurs familles.
- La mise en page mobile repose sur des container queries (elle doit fonctionner dans l'aperçu mobile comme sur un vrai téléphone).
- Le travail se fait sur la branche `maquettes-yann` (PR ddmp3/nasa-space-app-challenge-2026-cyber-space#48).

## Approches envisagées

| Approche | Principe | Avantages | Inconvénients |
|---|---|---|---|
| **1. Parcours guidé par chapitres, avec une scène 3D commune** (retenue) | Barre de 6 chapitres, un écran par chapitre, Suivant / Retour ; les globes forment une scène qui change à chaque chapitre | Logique, on ne se perd pas ; retour en arrière facile, adapté à un vrai travail de préparation | Réorganisation profonde de la maquette |
| 2. Récit en défilement continu | Une longue page ; les globes, fixés sur un côté, s'animent au défilement | Le plus fluide | Revenir changer un choix est pénible ; le plus lourd à construire |
| 3. Fil conducteur posé sur l'écran actuel | Guide latéral des 6 étapes au-dessus de l'écran Explorer | Le moins de travail | La comparaison reste secondaire : ne répond pas à la demande |

Yann a choisi l'**approche 1**.

## Ce qui est décidé

### Les 6 chapitres

Une barre de chapitres reste visible en haut de l'écran : numéro, titre court, état (à faire, en cours, fait). Un chapitre déjà atteint est cliquable ; les suivants se déverrouillent dans l'ordre. Chaque écran a un bouton « Suivant » (libellé explicite, par exemple « Voir les candidats ») et « Retour ».

La **scène 3D** occupe une large partie de l'écran et change avec le chapitre (transition animée courte).

| # | Chapitre | Ce que fait l'utilisateur | Scène 3D |
|---|---|---|---|
| 1 | **Mission** | Choisit le site lunaire (liste avec recherche ou clic sur la Lune 3D) et ce qu'il veut tester : un scénario 1 à 3, ou ses propres critères (le formulaire des critères libres s'ouvre dans ce chapitre) | Lune seule, qui tourne vers le site choisi |
| 2 | **Le site lunaire** | Découvre ce qui caractérise le site (contenu de l'actuelle fiche lunaire) et **ce qu'il faudra retrouver sur Terre** : les critères du scénario avec leurs valeurs cibles, adaptées au site | Lune, zoom sur le site |
| 3 | **Candidats** | Voit les sites terrestres classés : liste, filtre par plage de notes, filtre par instrument (scénario 2), états de chargement / erreur / aucun résultat. Les 3 meilleurs sont mis en avant. Peut remplacer l'un des 3 par un autre site de la liste | Terre ; les candidats s'allument, les 3 meilleurs ressortent |
| 4 | **Comparer** | Compare les 3 candidats face au site lunaire (voir plus bas) et clique « Choisir ce site » sur l'un d'eux | Lune et Terre côte à côte, les 3 candidats marqués sur la Terre |
| 5 | **Choisir** | Confirme le site retenu : les raisons du choix (familles fortes), ce qu'il faudra compenser (familles faibles), les 2 autres candidats en rappel ; peut revenir comparer | Terre, zoom sur le site retenu |
| 6 | **Dossier** | Consulte le dossier du site retenu (voir plus bas) | Lune et Terre côte à côte, site lunaire et site retenu mis en évidence |

**Revenir en arrière** : changer le site lunaire, le scénario ou les critères au chapitre 1 recalcule le classement. Les chapitres 4 à 6 se mettent à jour.

**Règles du trio comparé** (choix de conception de Claude, à relire) :
- Le trio = les 3 meilleurs sites non exclus pour les critères en cours. Le filtre par instrument (scénario 2) change les critères, donc recalcule le trio ; la **plage de notes** ne fait que filtrer l'affichage de la liste et des points, elle ne change pas le trio.
- Un site **remplacé à la main** reste dans le trio tant qu'il figure dans les résultats (non exclu), même après un retour au chapitre 1.
- Le site retenu au chapitre 4 est annulé seulement s'il sort du trio ; l'utilisateur en est prévenu en une ligne.
- **Moins de 3 candidats** : la comparaison porte sur ceux qui restent (1 ou 2 cartes). Avec 0 candidat (état vide ou erreur), les chapitres 4 à 6 restent verrouillés et le chapitre 3 explique comment élargir la recherche.
- Au chapitre 3, cliquer un site ouvre sa **fiche actuelle** (réutilisée), avec un bouton « Mettre dans la comparaison » qui remplace le candidat le moins bien noté du trio.

### Chapitre 4 : la comparaison

Retenu : **duel par familles de critères**, avec la **superposition des surfaces au clic**.

- **Une carte par candidat** (3 cartes côte à côte, empilées sur mobile) : nom, note globale, une jauge par famille de critères, une phrase de verdict, et deux boutons « Superposer » et « Choisir ce site ».
- **Familles** : celles du catalogue (Relief, Températures, Atmosphère et climat, Énergie et position, Géologie). Seules les familles qui contiennent au moins un critère du scénario apparaissent. La note d'une famille est la moyenne pondérée des notes de ses critères.
- **Verdict** : une phrase courte construite à partir de la famille la plus forte et de la plus faible (par exemple « Idéal pour la mobilité, froid insuffisant »).
- **Détail** : un clic sur une famille ouvre ses critères, avec la valeur du site terrestre, la valeur lunaire et la note.
- **Superposer** : un graphique de surface (radar, celui de la fiche actuelle) montre la surface lunaire en fond, semi-transparente. Chaque clic sur « Superposer » ajoute ou retire la surface d'un candidat, dans sa couleur. On peut superposer les 3 en même temps pour les départager.
- En tête du chapitre, un rappel : « Comparés à : [site lunaire] · scénario [n] ».

### Chapitre 6 : le dossier

Une page de l'application, consultée à l'écran.

1. **En-tête** : site retenu, site lunaire de référence, scénario, note globale.
2. **Caractéristiques** du site terrestre : les valeurs des 18 paramètres, groupées par famille (information ; choix de conception de Claude).
3. **Analogies et différences** : pour chaque critère **du scénario** (choix de conception de Claude), la valeur terrestre et la valeur lunaire, côte à côte. Les critères sans équivalent lunaire (température de l'air, altitude) sont signalés comme tels.
4. **Portée des tests** : chaque comparaison est traduite en conséquence pour les tests, en langage de mission.
   - Trois niveaux : **Représentatif** (note de critère ≥ 0,7), **Partiel** (0,4 à 0,7), **Non représentatif** (< 0,4).
   - Une phrase par famille, liée au type de test : Relief → mobilité et franchissement ; Températures → tests thermiques ; Atmosphère et climat → calibration des capteurs (vent, gaz) ; Géologie → forage et sismomètres ; Énergie et position → énergie solaire et éclairage. Exemple : « Sol bien moins froid la nuit (-30 °C contre -190 °C) : tests thermiques à compléter en chambre à vide. » La portée ne concerne que les critères du scénario.
   - Un bloc permanent **« Jamais reproductible sur Terre »** : gravité, vide, rayonnement.

### Ce qui change dans la navigation actuelle

- Les écrans Accueil et Explorer laissent place au parcours. L'accueil devient l'entrée du chapitre 1 (la Lune 3D cliquable de l'accueil y reste).
- Les **critères libres** deviennent une option du chapitre 1.
- L'**Aide** et le **glossaire** restent accessibles en permanence depuis la barre du haut ; l'Aide décrit les 6 chapitres.
- On garde : l'aperçu mobile, les annotations API, l'état démo (au chapitre 3).

### Décisions complémentaires (Yann, 2026-11-14)

- **Analogie = option A** : le classement, les jauges et le verdict gardent la note du scénario. Dans le dossier, la portée des tests tient aussi compte de l'écart réel à la Lune : un critère bien noté mais loin de la valeur lunaire est classé « Partiel ».
- **Thème selon le scénario** : une base commune ; chaque scénario change la couleur d'accent, un motif de fond et le rendu des globes (robotique : ocre et courbes de niveau ; instruments : cyan et grille d'oscilloscope ; colonie : or solaire et trame d'habitat ; critères libres : neutre).
- **Fichier** : nouveau fichier `docs/maquettes/parcours.html` et nouvel artefact ; l'ancienne maquette reste telle quelle pour comparer.

### Révision après revue de la maquette (Yann, 2026-11-14)

Le parcours passe de 6 à **4 chapitres** : **Mission, Candidats, Comparer, Synthèse**.
- **Mission** : sous les scénarios, la liste des critères sur lesquels la mission sera évaluée (valeurs cibles, mention « adapté »). Le chapitre « Le site lunaire » disparaît : un bouton **Fiche du site** près de la sélection ouvre la fiche lunaire en superposition, et « Suivant » mène directement aux candidats.
- **Candidats** : sur le globe, les 3 meilleurs ressortent (couleur, taille, étiquette « A · 92 »), chaque site affiche sa note, et le survol d'un site ouvre sa **fiche de synthèse** en superposition. Dans la liste, une icône ouvre la même fiche.
- **Fiche de synthèse** : visuels du site lunaire et du site terrestre quand ils sont disponibles ; indicateurs au choix en **jauges** ou en **radar** (surface lunaire superposée).
- **Comparer** : le bouton « Revoir le site retenu » est retiré. Le chapitre « Choisir » disparaît : « Ce qui joue en sa faveur » et « Ce qu'il faudra compenser » figurent dans chaque carte, avec un bouton « Retenir ce site ».
- **Synthèse** (ex-« Dossier ») : titre « Synthèse finale : [site] », visuels des deux sites quand ils sont disponibles.
- **Général** : jauges au format ▰▰▰▰▱ ; les sites peu étudiés sont signalés par une pastille « ✦ Peu étudié » (liste, globe, fiches, cartes, synthèse).
- **Visuels** (choix de Claude) : mosaïque LRO WAC de NASA Moon Trek pour la Lune, imagerie Esri World Imagery pour la Terre, chargées par tuile ; « Visuel non disponible » si le chargement échoue ou est bloqué (cas de l'artefact claude.ai). Licence et source définitives à confirmer par l'équipe.

## Ce qui est laissé au constructeur

- L'apparence exacte de la barre de chapitres, des cartes et du dossier, dans le thème existant.
- La durée et le style des transitions de la scène 3D (courtes, coupées si l'appareil demande moins d'animations).
- Les modèles de phrases du verdict et de la portée des tests, dans l'esprit des exemples ci-dessus.
- La réorganisation du code et la réutilisation des fonctions existantes (moteur, globes, fiches, radar).
- La mise à jour de `docs/parcours-utilisateur.md` pour décrire le nouveau parcours.
