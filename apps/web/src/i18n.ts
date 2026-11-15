export type Lang = 'en'

/** Textes de l'interface, en anglais. */
const en = {
  brand: 'Cyber&Space Montréal',
  tagline: 'NASA Space Apps Challenge 2026',
  heroEyebrow: 'Earth analogs for the lunar south pole',
  heroTitle: 'Find the Moon on Earth.',
  heroLead:
    'Before a rover, an instrument or a habitat flies to the lunar south pole, it is tested on Earth. Pick a mission: we rank real Earth sites against real lunar data, and show what matches, what does not, and why.',
  heroCredit: 'Earthset from Orion, Artemis II, 6 April 2026 · NASA',
  chooseMission: 'Choose your mission',
  chooseMissionLead: 'Each mission scores the same Earth sites against a different set of lunar conditions.',
  target: 'Earth ↔ Moon',
  marsSoon: 'Mars: next phase',
  launch: 'Launch mission',
  stats: ['Earth sites compared', 'parameters per site', 'open data sources', 'lunar terrain windows measured (LRO LOLA)'],
  backToMissions: 'All missions',
  ranking: 'Ranking',
  sitesRanked: 'sites ranked',
  excluded: 'Excluded: vegetation',
  excludedShort: 'Excluded',
  loading: 'Querying NASA POWER, USGS and Smithsonian…',
  loadingHint: 'The first run takes a few seconds; the next ones are instant.',
  errorTitle: 'The analysis could not run',
  retry: 'Try again',
  roles: { validation: 'Known analog', candidate: 'Understudied site', negative: 'Negative control' },
  verdicts: { match: 'Matches', partial: 'Partly matches', mismatch: 'Does not match', missing: 'No data' },
  score: 'Analog score',
  criteriaEvaluated: 'criteria evaluated',
  seeTheMatch: 'See the match',
  seeTheMatchLead:
    'Same scale, same 40 m grid, same lighting: the Earth site and the patch of lunar south pole whose terrain is closest to it.',
  earth: 'Earth',
  moon: 'Moon',
  satellite: 'Satellite',
  relief: 'Relief',
  highlight: 'Highlight lunar-like slopes',
  highlightHint: (lo: number, hi: number) => `Slopes between ${lo}° and ${hi}°, the typical range at the lunar south pole`,
  lunarTwin: 'Lunar twin',
  twinAt: (lat: number, lon: number) => `${Math.abs(lat).toFixed(2)}°S, ${Math.abs(lon).toFixed(1)}°${lon < 0 ? 'W' : 'E'}`,
  terrainShare: 'Terrain in the lunar slope range',
  noPhoto: 'No sharp satellite image for this site: relief shown instead.',
  scaleBar: '2 km',
  scorecard: 'Analog scorecard',
  scorecardLead: 'One table: what was measured on Earth, the lunar reference, how well they match, and where each number comes from.',
  colParameter: 'Parameter',
  colEarth: 'Earth site',
  colMoon: 'Lunar south pole',
  colMatch: 'Match',
  colVerdict: 'Verdict',
  colSource: 'Source',
  noLunarRef: 'no sourced value',
  limitsTitle: 'Cannot be reproduced on Earth',
  limitsVerdict: 'Not reproducible',
  radarTitle: 'Match profile',
  radarLead: 'Each axis is one criterion. The outer ring is a perfect match with the lunar target.',
  sourcesTitle: 'Data sources',
  imagesTitle: 'Image credits',
  imagesText:
    'Mission photographs: NASA (Apollo 14, 15 and 17; Artemis II; Clementine mosaic NASA/JPL/USGS). Site imagery: Sentinel-2 cloudless 2016 by EOX IT Services GmbH (contains modified Copernicus Sentinel data 2016), CC BY 4.0; Landsat WELD, NASA GIBS. Relief: Copernicus DEM GLO-30 and LRO LOLA. Base map: NASA Blue Marble, NASA GIBS.',
  footer: 'A NASA Space Apps Challenge 2026 project · Parts of this project were built with AI assistance (Claude, Microsoft Copilot).',
  bareSoil: 'Exclude vegetated sites',
  bareSoilHint: 'Bare ground filter (NDVI ≤ 0.2)',
  instrument: 'Instrument',
  allInstruments: 'All instruments',
  instruments: { drill: 'Drill', wind: 'Wind', gas: 'Gas', seismograph: 'Seismometer', thermal: 'Thermal' },
  customTitle: 'Your criteria',
  customLead: 'Pick parameters, set the target range, the tolerance and the weight.',
  parameter: 'Parameter',
  min: 'Min',
  max: 'Max',
  tolerance: 'Tolerance',
  weight: 'Weight',
  addCriterion: 'Add a criterion',
  remove: 'Remove',
  run: 'Run analysis',
  customErrors: {
    duplicate: 'A parameter can only be used once.',
    range: 'Each criterion needs a minimum, a maximum, or both.',
    number: 'Ranges, tolerance and weight must be numbers; tolerance and weight above zero.',
  },
  missions: {
    robotics: {
      title: 'Rover mobility',
      text: 'Where to test a rover on slopes and rough ground like the lunar south pole.',
      tags: ['Slope', 'Roughness', 'Dry soil', 'Cold'],
      credit: 'Apollo 15 Lunar Roving Vehicle, 1971 · NASA',
    },
    calibration: {
      title: 'Instrument calibration',
      text: 'Where to calibrate drills, seismometers and sensors in dry, calm, cold conditions.',
      tags: ['Seismic quiet', 'Dry air', 'No wind', 'Frozen ground'],
      credit: 'Apollo 14 passive seismic experiment, 1971 · NASA',
    },
    colony: {
      title: 'Self-sufficient base',
      text: 'Where Earth comes closest to what a lunar base needs: ice, polar light, flat stable ground.',
      tags: ['Frozen ground', 'Polar light', 'Flat terrain', 'Stability'],
      credit: 'Apollo 17 landing site, 1972 · NASA',
    },
    custom: {
      title: 'Free criteria',
      text: 'Build your own mission: choose the parameters, their ranges and their weights.',
      tags: ['18 parameters', 'Your ranges', 'Your weights'],
      credit: 'Lunar south pole, Clementine mosaic · NASA/JPL/USGS',
    },
  },
}

export type Texts = typeof en

/** Interface en anglais uniquement (exigence de la soumission Space Apps). */
export function useT(): { t: Texts; lang: Lang } {
  return { t: en, lang: "en" }
}

export function formatNumber(value: number, _lang: Lang = "en", digits = 2): string {
  return value.toLocaleString("en-CA", { maximumFractionDigits: digits })
}
