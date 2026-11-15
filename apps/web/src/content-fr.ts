// French versions of the content that comes from the API or the data files (site names, parameters,
// what Earth cannot reproduce, sources). The API and the data stay in English; the interface texts are in i18n.ts.
// A missing key falls back to the English text, so a new site or parameter never breaks the French interface.

export const FR_SITES: Record<string, string> = {
  haughton: 'Cratère Haughton (île Devon, Nunavut)',
  atacama: 'Désert d’Atacama (Chili)',
  'dry-valleys': 'Vallées sèches de McMurdo, vallée Wright (Antarctique)',
  'mauna-kea': 'Mauna Kea, flancs supérieurs (Hawaï)',
  'svalbard-bockfjorden': 'Bockfjorden, volcan Sverrefjellet (Svalbard)',
  'iceland-holuhraun': 'Champ de lave d’Holuhraun (Islande)',
  'death-valley': 'Bassin de Badwater, vallée de la Mort (Californie)',
  'meteor-crater': 'Meteor Crater (Arizona)',
  'black-point': 'Coulée de Black Point (Arizona)',
  amazon: 'Forêt amazonienne (témoin négatif)',
  mistastin: 'Structure d’impact de Mistastin, rive est (Labrador)',
  tunnunik: 'Cratère Tunnunik (île Victoria, T.N.-O.)',
  'axel-heiberg': 'Station de recherche arctique McGill, île Axel Heiberg (Nunavut)',
  pingualuit: 'Cratère des Pingualuit, rebord ouest (Nunavik, Québec)',
  manicouagan: 'Île René-Levasseur, Manicouagan (Québec)',
  'peary-land': 'Terre de Peary (nord du Groenland)',
  popigai: 'Cratère de Popigaï (Sibérie)',
  elgygytgyn: 'Cratère d’El’gygytgyn, rebord est (Tchoukotka)',
  tolbachik: 'Tolbatchik (Kamtchatka)',
  erebus: 'Mont Erebus, île de Ross (Antarctique)',
  'qaidam-lenghu': 'Yardangs de Lenghu, bassin du Qaidam (Chine)',
  changtang: 'Plateau du Changtang (Tibet)',
  gobi: 'Plaines de graviers du Gobi (Mongolie)',
  uyuni: 'Salar d’Uyuni (Bolivie)',
  licancabur: 'Licancabur, Altiplano (Bolivie-Chili)',
  payunia: 'Champ volcanique de la Payunia (Argentine)',
  'namib-gobabeb': 'Plaines de graviers du Namib, Gobabeb (Namibie)',
  lut: 'Kaluts du désert de Lut (Iran)',
  dallol: 'Dallol, dépression du Danakil (Éthiopie)',
  'erta-ale': 'Erta Ale (Éthiopie)',
  'hoggar-atakor': 'Champ volcanique de l’Atakor, Hoggar (Algérie)',
  'harrat-khaybar': 'Harrat Khaybar (Arabie saoudite)',
  aorounga: 'Cratère d’Aorounga (Tchad)',
  tenoumer: 'Cratère de Tenoumer (Mauritanie)',
  'wolfe-creek': 'Cratère de Wolfe Creek (Australie)',
  'gosses-bluff': 'Gosses Bluff (Australie)',
  'craters-of-the-moon': 'Craters of the Moon (Idaho)',
}

export const FR_PARAMS: Record<string, { label: string; unit?: string; help: string }> = {
  slope_mean: { label: 'Pente moyenne', help: 'Inclinaison moyenne du terrain sur 1 km. Au pôle Sud lunaire, la moitié des zones de 1 km ont une pente moyenne entre 5 et 13° (LOLA).' },
  slope_max: { label: 'Pente maximale', help: 'Pente la plus forte sur 1 km : elle dit si un rover peut passer. Les rovers lunaires franchissent de 15 à 25°.' },
  roughness: { label: 'Rugosité', help: 'Variation de l’altitude sur 1 km : un terrain rugueux est accidenté, cratérisé.' },
  elevation: { label: 'Altitude', help: 'Altitude du site au-dessus du niveau de la mer.' },
  ndvi: { label: 'Végétation (NDVI)', help: 'Indice de végétation mesuré par satellite. Au-delà de 0,2, il y a des plantes : le site ne ressemble pas à la Lune.' },
  lst_day: { label: 'Température de surface, jour', help: 'Température du sol le jour, vue par satellite (moyenne annuelle).' },
  lst_night: { label: 'Température de surface, nuit', help: 'Température du sol la nuit. Sur la Lune, les cratères à l’ombre descendent à -240 °C : aucun site terrestre n’en approche.' },
  lst_amplitude: { label: 'Amplitude jour-nuit', help: 'Écart entre le jour et la nuit. Sur la Lune, il atteint environ 300 °C ; sur Terre, les déserts en donnent une petite idée.' },
  t2m_mean: { label: 'Température moyenne de l’air', help: 'Température moyenne de l’air : un site très froid a un sol gelé, comparable au sol glacé lunaire.' },
  t2m_min: { label: 'Température minimale de l’air', help: 'Température la plus basse de l’année : utile pour tester le matériel au froid.' },
  t2m_max: { label: 'Température maximale de l’air', help: 'Température la plus haute de l’année.' },
  wind: { label: 'Vent', help: 'Vitesse moyenne du vent. La Lune n’a pas d’atmosphère, donc pas de vent : un site calme s’en rapproche.' },
  humidity: { label: 'Humidité', help: 'Humidité de l’air. La Lune n’en a pas : un air sec s’en rapproche.' },
  precipitation: { label: 'Précipitations', unit: 'mm/j', help: 'Pluie ou neige par jour. Un sol sec et meuble se rapproche du régolithe lunaire.' },
  solar: { label: 'Ensoleillement', unit: 'kWh/m²/j', help: 'Énergie solaire reçue par jour : utile pour alimenter une base.' },
  latitude_abs: { label: 'Latitude absolue', help: 'Distance à l’équateur. Près des pôles, le Soleil reste bas sur l’horizon, comme au pôle Sud lunaire.' },
  quake_count: { label: 'Séismes (depuis 2000)', help: 'Nombre de séismes de magnitude 2,5 ou plus à moins de 300 km depuis 2000. La Lune est sismiquement très calme.' },
  volcano_distance: { label: 'Distance au volcan', help: 'Distance au volcan récent le plus proche : la roche volcanique (basalte) sert de substitut au sol lunaire.' },
}

export const FR_MOON_NOTES: Record<string, string> = {
  t2m_mean: 'Pas d’air sur la Lune : proxy du sol gelé',
  t2m_min: 'Pas d’air : proxy du froid extrême (29 à 50 K à l’ombre)',
  t2m_max: 'Pas d’air sur la Lune',
  lst_day: 'Crêtes éclairées : pas encore sourcé',
  lst_amplitude: 'Environ 300 K à l’équateur (Diviner)',
  solar: 'Lumière quasi continue sur certaines crêtes polaires',
  quake_count: '28 séismes lunaires peu profonds en 8 ans (Apollo)',
  volcano_distance: 'Pas de volcanisme récent : le basalte est un substitut terrestre',
  elevation: 'Non comparable',
}

export const FR_LIMITS: Record<string, { label: string; earth: string; moon: string; effect: string }> = {
  gravity: {
    label: 'Gravité', earth: '9,81 m/s²', moon: '1,62 m/s²',
    effect: 'Mobilité, ancrage, forage et poussière se comportent autrement : aucun site terrestre ne reproduit la gravité lunaire (environ un sixième).',
  },
  oxygen: {
    label: 'Oxygène et atmosphère', earth: '21 % d’oxygène dans un air à environ 1 bar', moon: 'aucune atmosphère respirable : pas d’oxygène libre, pas de pression',
    effect: 'Sur Terre, moteurs, feu, sons, refroidissement par l’air et respiration fonctionnent ; sur la Lune, tout système doit apporter son oxygène et évacuer sa chaleur par rayonnement.',
  },
  vacuum: {
    label: 'Vide', earth: 'environ 1 bar', moon: 'pression de surface d’environ 3 × 10⁻¹⁵ bar (exosphère)',
    effect: 'Pas de convection, pas de vent, pas d’érosion par l’air : les critères de vent, d’humidité et de précipitations sont des proxys d’un milieu sec et calme.',
  },
  radiation: {
    label: 'Rayonnement', earth: 'atmosphère et magnétosphère protectrices', moon: 'ni atmosphère ni champ magnétique global : surface exposée aux rayons cosmiques et aux particules solaires',
    effect: 'Aucun site terrestre ne reproduit l’environnement radiatif lunaire.',
  },
  cold: {
    label: 'Froid extrême', earth: 'environ -90 °C (≈ 180 K) au plus froid, en Antarctique', moon: '29 à 50 K dans les zones en ombre permanente (Diviner)',
    effect: 'Les critères de température sont des proxys de tendance (froid, écart jour-nuit), jamais des valeurs absolues.',
  },
  regolith: {
    label: 'Régolithe et géologie', earth: 'sols altérés par l’eau, l’air et la vie', moon: 'croûte des hautes terres (anorthosite) au pôle Sud, régolithe non altéré par l’eau ni la vie',
    effect: 'Le basalte terrestre sert de substitut pour la mécanique des roches ; l’anorthosite (Mistastin, Labrador) est le jumeau rocheux le plus proche.',
  },
}

export const FR_SOURCES: Record<string, { name: string; short: string; terms: string }> = {
  coordinates: { name: 'Coordonnées des sites candidats', short: 'Coordonnées du site', terms: 'Liste versionnée dans le dépôt du projet.' },
  'nasa-power': { name: 'NASA POWER (climatologie par point)', short: 'NASA POWER', terms: 'Données NASA, accès libre. Données obtenues du projet POWER du NASA Langley Research Center.' },
  'usgs-comcat': { name: 'Catalogue des séismes de l’USGS (ComCat)', short: 'Catalogue des séismes USGS', terms: 'Domaine public (gouvernement des États-Unis). Séismes de magnitude 2,5 ou plus à moins de 300 km depuis 2000.' },
  'smithsonian-gvp': { name: 'Smithsonian Global Volcanism Program, Volcanoes of the World (Holocène)', short: 'Smithsonian GVP', terms: 'Global Volcanism Program, Smithsonian Institution, base Volcanoes of the World.' },
  'copernicus-dem': { name: 'Copernicus DEM GLO-30', short: 'Copernicus DEM GLO-30 (ESA)', terms: 'Produit à partir de Copernicus WorldDEM-30 © DLR e.V. 2010-2014 et © Airbus Defence and Space GmbH 2014-2018, fourni dans le cadre de COPERNICUS par l’Union européenne et l’ESA. Pente et rugosité calculées sur des fenêtres de 1 km.' },
  modis: { name: 'NASA MODIS MOD11A2 / MYD11A2 (température de surface) et MOD13A1 / MYD13A1 (NDVI), version 6.1', short: 'NASA MODIS', terms: 'Données NASA, accès libre. Moyennes 2024 précalculées.' },
  'lro-lola': { name: 'LRO LOLA, modèle d’élévation polaire LDEM_85S_40M', short: 'LRO LOLA', terms: 'Données NASA PDS, accès libre. Calculé avec la même méthode que pour la Terre.' },
  'lro-diviner': { name: 'LRO Diviner (températures lunaires)', short: 'LRO Diviner', terms: 'Valeurs publiées, citées dans le profil lunaire de référence.' },
  fixtures: { name: 'Données d’exemple', short: 'Données d’exemple (pas pour la démo)', terms: '' },
}
