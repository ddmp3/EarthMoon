# Sources de données

Accès testé le 2026-11-14 par requêtes GET depuis un poste de l'équipe. « Vérifié » signifie que l'endpoint répond (HTTP 200/206) et renvoie des données lisibles. Ce n'est pas une validation scientifique du jeu de données. Les licences sont à confirmer avant toute diffusion.

## Principe d'accès

Le README impose : aucun stockage côté application, accès par API uniquement.

- **Cible (Lune / Mars)** : le profil de référence (température, pente, relief, etc.) ne change pas. On le calcule une seule fois hors ligne à partir des sources ci-dessous, puis on le livre comme petit fichier de configuration JSON versionné (paramètres, pas jeu de données).
- **Candidats (Terre)** : interrogés en direct par API (REST, STAC, WMTS) ou par lecture partielle de fichiers COG via des requêtes HTTP Range, sans téléchargement complet.

## Socle (priorité 1)

| Source | Corps | Variables | Accès | Auth | Statut |
|---|---|---|---|---|---|
| LRO **LOLA** (GDR DEM, pente) | Lune | relief, pente | [ODE REST](https://oderest.rsl.wustl.edu/live2/) `ihid=LRO&iid=LOLA&pt=GDRDEM` (270 produits) ; fichiers [PDS Geosciences](https://pds-geosciences.wustl.edu/lro/lro-l-lola-3-rdr-v1/lrolol_1xxx/data/lola_gdr/polar/) | Non | Vérifié |
| LRO **Diviner** (DLRE GDR L3) | Lune | température de surface | ODE REST `ihid=LRO&iid=DLRE&pt=GDR_L3` (1 827 produits) | Non | Vérifié |
| **Copernicus DEM GLO-30** | Terre | relief, pente (calculée) | COG sur AWS : `https://copernicus-dem-30m.s3.amazonaws.com/Copernicus_DSM_COG_10_N{lat}_00_W{lon}_00_DEM/...tif` ; STAC [Planetary Computer](https://planetarycomputer.microsoft.com/api/stac/v1/collections/cop-dem-glo-30) | Non | Vérifié (lecture partielle OK) |
| **MODIS LST** (MOD11A2) | Terre | température de surface | [CMR](https://cmr.earthdata.nasa.gov/search/collections.json?short_name=MOD11A2) (recherche) ; tuiles [GIBS WMTS](https://gibs.earthdata.nasa.gov/wmts/epsg4326/best/wmts.cgi?SERVICE=WMTS&REQUEST=GetCapabilities) (visualisation) | Recherche : non. Fichiers : compte Earthdata Login (gratuit) | Vérifié (recherche + WMTS) |
| **NASA POWER** | Terre | température air (moy/min/max), vent, ensoleillement | [API REST climatologie](https://power.larc.nasa.gov/api/temporal/climatology/point?parameters=T2M,T2M_MIN,T2M_MAX,WS2M&community=RE&longitude=-89.67&latitude=75.38&format=JSON) | Non | Vérifié (exemple : cratère Haughton, T2M annuelle -14,4 °C) |

NASA POWER est le plus simple à brancher depuis un front TypeScript : JSON direct par point, sans authentification.

## Minéralogie (priorité 2, élément différenciant)

| Source | Corps | Variables | Accès | Auth | Statut |
|---|---|---|---|---|---|
| **EMIT** L2B minéraux (60 m) | Terre | minéralogie des surfaces arides | CMR `short_name=EMITL2BMIN` | Fichiers : Earthdata Login | Vérifié (recherche) |
| **ASTER GDEM / thermique** | Terre | relief, émissivité infrarouge thermique | CMR `short_name=ASTGTM` | Fichiers : Earthdata Login | Vérifié (recherche) |
| MRO **CRISM**, ODY **THEMIS** | Mars | minéralogie, inertie thermique | ODE REST (base `mars`) | Non | Instruments présents dans ODE |

## Compléments (priorité 3, bonus)

| Source | Corps | Usage | Accès | Statut |
|---|---|---|---|---|
| LRO **LEND** | Lune | hydrogène près de la surface (glace) | ODE REST `iid=LEND&pt=RDRDLD4` | Vérifié |
| LRO **Mini-RF** | Lune | radar (rugosité, glace) | ODE REST `iid=MRFLRO&pt=MOSCDR` (24 mosaïques) | Vérifié |
| LROC / QuickMap | Lune | imagerie, catalogue des pits (tubes de lave) | [quickmap.lroc.asu.edu](https://quickmap.lroc.asu.edu/) | Site accessible ; pas d'API testée |
| Moon Trek | Lune | catalogue de couches (recherche) | `trek.nasa.gov/moon/TrekServices/ws/index/eq/searchItems` | Vérifié |
| MGS **MOLA**, MRO **CTX / HiRISE / SHARAD** | Mars | altimétrie, imagerie, radar de sub-surface | ODE REST (base `mars`) | Instruments présents dans ODE |
| USGS Astrogeology | Mars / Lune | catalogues (dont grottes candidates sur Mars) | [STAC](https://stac.astrogeology.usgs.gov/api/collections) | Vérifié |
| **ICESat-2** ATL06 | Terre | élévation et rugosité des glaces | CMR `short_name=ATL06` | Vérifié (recherche) |
| **ArcticDEM / REMA** | Terre | relief fin des pôles | [STAC PGC](https://pgc-opendata-dems.s3.us-west-2.amazonaws.com/pgc-data-stac.json) | Vérifié |
| **Sentinel-1** RTC / GRD | Terre | radar (rugosité), bonus SAR | STAC Planetary Computer `sentinel-1-rtc`, `sentinel-1-grd` | Vérifié (le premier essai a échoué en 502, le second a réussi) |
| ERA5 | Terre | climat (réanalyse) | [CDS](https://cds.climate.copernicus.eu/) | Catalogue vérifié ; téléchargement : compte CDS |
| Smithsonian **GVP** | Terre | volcans holocènes (champs volcaniques, tubes de lave) | [WFS GeoJSON](https://webservices.volcano.si.edu/geoserver/GVP-VOTW/ows?service=WFS&version=1.0.0&request=GetFeature&typeName=GVP-VOTW:Smithsonian_VOTW_Holocene_Volcanoes&outputFormat=application/json&maxFeatures=1) | Vérifié |
| RADARSAT-1 / RCM (ASC) | Terre | radar | Liens fournis dans l'énoncé du défi | Non testé |
| Earth Impact Database (UNB) | Terre | cratères d'impact | `passc.net` redirige vers une page « lander » (domaine qui semble parqué) | **À retrouver** |
| GLiM | Terre | lithologie globale | — | Non testé |

## Correspondance scénarios → variables

| Scénario | Variables | Lune / Mars | Terre |
|---|---|---|---|
| Entraînement (rovers) | pente, relief, rugosité | LOLA / MOLA | Copernicus DEM, ICESat-2 |
| Calibration (instruments) | minéralogie, thermique | Diviner / CRISM, THEMIS | EMIT, ASTER |
| Implantation humaine | température, sous-sol, cavités | Diviner, pits LROC / grottes USGS | MODIS LST, NASA POWER, GVP |
| Ressources (glace, ISRU) — proposé | hydrogène, glace enfouie | LEND, Mini-RF / SHARAD | ArcticDEM, Sentinel-1 |

## Jeu de validation

Les analogues reconnus doivent obtenir un score élevé : Atacama, Dry Valleys (Antarctique), cratère Haughton (île Devon), Mauna Kea, Rio Tinto, Svalbard, Islande. Un témoin négatif (Amazonie) doit obtenir un score bas.

## Limites connues

- Le SAR (Mini-RF contre Sentinel-1/RCM) n'est pas directement comparable : longueurs d'onde et polarisations différentes. On le garde en bonus sur 1 ou 2 sites, avec ses limites expliquées.
- Les fichiers MODIS, EMIT, ASTER et ICESat-2 demandent un compte Earthdata Login. Le jeton ne doit jamais être commité.
