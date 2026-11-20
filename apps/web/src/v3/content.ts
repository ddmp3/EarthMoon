import type { Lang } from '../i18n'

/**
 * French versions of the texts the API v3 serves in English (scenarios, requirements, limits, processing steps,
 * coverage classes). Keyed by id, or by the English text for lists without ids. A text without a translation is shown
 * in English, never hidden (a test checks that every text of a release is covered).
 */
const SCENARIO_FR: Record<string, { name: string; objective: string }> = {
  A: {
    name: 'Base lunaire permanente',
    objective:
      'Trouver des lieux terrestres où étudier le terrain, les matériaux et le comportement thermique d’une zone de base au pôle Sud lunaire, pour répéter la caractérisation du site, la construction sur pente et la mobilité autour d’une base.',
  },
  B: {
    name: 'Exploration robotique lunaire',
    objective:
      'Trouver des terrains terrestres dont la distribution des pentes ressemble à celle d’un environnement lunaire cible, pour tester la mobilité, la navigation et la planification de trajets des rovers.',
  },
}

const REQUIREMENT_FR: Record<string, { what: string; value: string }> = {
  base_slope: { what: 'Pente de l’emprise de la base', value: '5° au plus de préférence, inadaptée au-delà de 10°' },
  base_site_beyond_slope: { what: 'Portance, densité de blocs, risques à l’atterrissage', value: 'non fixé' },
  target_environment: {
    what: 'Environnements couverts par la zone de base',
    value: 'hauts plateaux éclairés pour la base ; zones éclairées en permanence pour l’énergie ; régions ombragées et fosses comme cibles proches',
  },
  climbing_limit_lrv: { what: 'Pente pour laquelle un rover lunaire habité a été conçu', value: '20 à 23° en conditions favorables, 25° au maximum (LRV Apollo)' },
  climbing_limit_viper: { what: 'Pente limite d’un rover robotique polaire', value: '15° (VIPER), non indiqué dans les résumés NTRS lus' },
  traversable_share: { what: 'Part d’une fenêtre qui doit rester sous la limite de pente', value: 'la moitié de la fenêtre' },
}

const LIMIT_FR: Record<string, string> = {
  'Lunar gravity, vacuum and radiation.': 'Gravité lunaire, vide et rayonnement.',
  'Illumination by a Sun grazing the horizon; permanently shadowed cryogenic surfaces.':
    'Éclairage par un Soleil rasant l’horizon ; surfaces cryogéniques en ombre permanente.',
  'Regolith mechanics (no layer in the catalogues; E9).': 'Mécanique du régolithe (aucune couche dans les catalogues ; E9).',
  'Volatile resources (lunar indicators have no Earth equivalent).': 'Ressources volatiles (les indicateurs lunaires n’ont pas d’équivalent terrestre).',
  'Mass wasting under lunar gravity (only slope is compared).': 'Mouvements de terrain sous gravité lunaire (seule la pente est comparée).',
  'Obstacles below the DEM pixel (rocks, small craters, the slope under a wheel).':
    'Obstacles plus petits que le pixel du MNT (rochers, petits cratères, la pente sous une roue).',
  'Traction and sinkage in regolith under lunar gravity.': 'Traction et enfoncement dans le régolithe sous gravité lunaire.',
  'Thermal limits of the lunar night and of shadowed regions.': 'Limites thermiques de la nuit lunaire et des régions ombragées.',
  'Communication and navigation conditions (no GNSS on the Moon).': 'Conditions de communication et de navigation (pas de GNSS sur la Lune).',
  'Roughness, until the T41 effective resolution test (context only).': 'Rugosité, en attendant le test de résolution effective de T41 (contexte seulement).',
}

const STEP_FR: Record<string, string> = {
  screening: 'Des fenêtres de 90 m (Copernicus GLO-90) choisissent les tuiles de 1° affinées pour chaque cible',
  windows: 'Fenêtres de 1 km au pixel lunaire de chaque cible (Copernicus GLO-30)',
  masks: 'Les fenêtres au sol caché sont exclues (WorldCover 2021 ; affleurements rocheux au sud de 60°S)',
  typicality: 'Percentile bilatéral de la pente moyenne de chaque fenêtre parmi les fenêtres lunaires',
  cells: 'Cellules HEALPix (NSIDE 1303, 25,04 km²), une grille mondiale à aire égale',
  requirements: 'Exigences de chaque scénario, cellule par cellule',
  zones: 'Cellules candidates voisines de confiance haute (voisines HEALPix)',
  validation: 'Protocole de validation',
}

const STEP_EN: Record<string, string> = { requirements: 'Requirements of each scenario, cell by cell', validation: 'Validation protocol' }

const COVERAGE_FR: Record<string, string> = {
  screened_out: 'non affinée au pixel lunaire : aucune fenêtre de 90 m proche de cette cible (règle T22)',
  no_data: 'pas d’altitude valide, ou occupation du sol inconnue pour la moitié des fenêtres (hors WorldCover)',
  ground_hidden: 'la moitié des fenêtres ou plus cachées par forêt, cultures, bâti, eau, zones humides, mangroves, neige ou glace',
  partial: 'moins de la moitié des fenêtres de la cellule sont valides pour cette cible',
  low_confidence: 'confiance non haute : moins de 20 fenêtres valides, ou 10 % ou plus masquées ou de couverture inconnue',
  evaluated: 'confiance haute : au moins 20 fenêtres valides et moins de 10 % masquées ou de couverture inconnue',
}

export function scenarioText(id: string, lang: Lang, en: { name: string; objective: string }) {
  return lang === 'fr' && SCENARIO_FR[id] ? SCENARIO_FR[id] : en
}
export function requirementText(id: string, lang: Lang, en: { what: string; value: string }) {
  return lang === 'fr' && REQUIREMENT_FR[id] ? REQUIREMENT_FR[id] : en
}
export function limitText(en: string, lang: Lang): string {
  return lang === 'fr' ? (LIMIT_FR[en] ?? en) : en
}
export function stepText(step: string, lang: Lang, en: string | null | undefined): string {
  return lang === 'fr' ? (STEP_FR[step] ?? en ?? step) : (en ?? STEP_EN[step] ?? step)
}
export function coverageMeaning(cls: string, lang: Lang, en: string): string {
  return lang === 'fr' ? (COVERAGE_FR[cls] ?? en) : en
}
export const TRANSLATED = { SCENARIO_FR, REQUIREMENT_FR, LIMIT_FR, STEP_FR, COVERAGE_FR }
