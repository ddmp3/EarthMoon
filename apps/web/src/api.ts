import type { components } from './api-schema'
import type { Lang } from './i18n'

// label / help : français ; labelEn / helpEn : anglais. Texte d'aide grand public (ce que mesure le paramètre,
// et ce qu'il représente pour la Lune).
export const parameterCatalog = [
  { id: 'slope_mean', unit: '°', label: 'Pente moyenne', labelEn: 'Mean slope',
    help: 'Inclinaison moyenne du terrain sur 1 km. Au pôle Sud lunaire, la moitié des zones de 1 km ont une pente moyenne entre 5 et 13° (LOLA).',
    helpEn: 'Average tilt of the ground over 1 km. At the lunar south pole, half of the 1 km areas have a mean slope between 5 and 13° (LOLA).' },
  { id: 'slope_max', unit: '°', label: 'Pente maximale', labelEn: 'Maximum slope',
    help: 'Pente la plus forte sur 1 km : elle dit si un rover peut passer. Les rovers lunaires franchissent de 15 à 25°.',
    helpEn: 'Steepest slope over 1 km: it tells whether a rover can get through. Lunar rovers handle 15 to 25°.' },
  { id: 'roughness', unit: 'm', label: 'Rugosité', labelEn: 'Roughness',
    help: 'Variation de l’altitude sur 1 km : un terrain rugueux est accidenté, cratérisé.',
    helpEn: 'How much elevation varies over 1 km: rough ground is broken and cratered.' },
  { id: 'elevation', unit: 'm', label: 'Altitude', labelEn: 'Elevation',
    help: 'Altitude du site au-dessus du niveau de la mer.', helpEn: 'Height of the site above sea level.' },
  { id: 'ndvi', unit: '', label: 'Végétation (NDVI)', labelEn: 'Vegetation (NDVI)',
    help: 'Indice de végétation mesuré par satellite. Au-delà de 0,2, il y a des plantes : le site ne ressemble pas à la Lune.',
    helpEn: 'Vegetation index measured from orbit. Above 0.2 there are plants: the site does not look like the Moon.' },
  { id: 'lst_day', unit: '°C', label: 'Température de surface, jour', labelEn: 'Surface temperature, day',
    help: 'Température du sol le jour, vue par satellite (moyenne annuelle).',
    helpEn: 'Ground temperature during the day, seen from orbit (annual mean).' },
  { id: 'lst_night', unit: '°C', label: 'Température de surface, nuit', labelEn: 'Surface temperature, night',
    help: 'Température du sol la nuit. Sur la Lune, les cratères à l’ombre descendent à -240 °C : aucun site terrestre n’en approche.',
    helpEn: 'Ground temperature at night. On the Moon, shadowed craters drop to -240 °C: no Earth site comes close.' },
  { id: 'lst_amplitude', unit: '°C', label: 'Amplitude thermique', labelEn: 'Day-night swing',
    help: 'Écart entre le jour et la nuit. Sur la Lune, il atteint environ 300 °C ; sur Terre, les déserts en donnent une petite idée.',
    helpEn: 'Gap between day and night. On the Moon it reaches about 300 °C; on Earth, deserts give a small taste of it.' },
  { id: 't2m_mean', unit: '°C', label: 'Température moyenne de l’air', labelEn: 'Mean air temperature',
    help: 'Température moyenne de l’air : un site très froid a un sol gelé, comparable au sol glacé lunaire.',
    helpEn: 'Average air temperature: a very cold site has frozen ground, comparable to icy lunar soil.' },
  { id: 't2m_min', unit: '°C', label: 'Température minimale de l’air', labelEn: 'Minimum air temperature',
    help: 'Température la plus basse de l’année : utile pour tester le matériel au froid.',
    helpEn: 'Coldest temperature of the year: useful to cold-test hardware.' },
  { id: 't2m_max', unit: '°C', label: 'Température maximale de l’air', labelEn: 'Maximum air temperature',
    help: 'Température la plus haute de l’année.', helpEn: 'Warmest temperature of the year.' },
  { id: 'wind', unit: 'm/s', label: 'Vent', labelEn: 'Wind',
    help: 'Vitesse moyenne du vent. La Lune n’a pas d’atmosphère, donc pas de vent : un site calme s’en rapproche.',
    helpEn: 'Average wind speed. The Moon has no atmosphere, so no wind: a calm site is closer to it.' },
  { id: 'humidity', unit: '%', label: 'Humidité', labelEn: 'Humidity',
    help: 'Humidité de l’air. La Lune n’en a pas : un air sec s’en rapproche.',
    helpEn: 'Moisture in the air. The Moon has none: dry air is closer to it.' },
  { id: 'precipitation', unit: 'mm/j', unitEn: 'mm/day', label: 'Précipitations', labelEn: 'Precipitation',
    help: 'Pluie ou neige par jour. Un sol sec et meuble se rapproche du régolithe lunaire.',
    helpEn: 'Rain or snow per day. Dry, loose ground is closer to lunar regolith.' },
  { id: 'solar', unit: 'kWh/m²/j', unitEn: 'kWh/m²/day', label: 'Ensoleillement', labelEn: 'Solar energy',
    help: 'Énergie solaire reçue par jour : utile pour alimenter une base.',
    helpEn: 'Solar energy received per day: useful to power a base.' },
  { id: 'latitude_abs', unit: '°', label: 'Latitude absolue', labelEn: 'Absolute latitude',
    help: 'Distance à l’équateur. Près des pôles, le Soleil reste bas sur l’horizon, comme au pôle Sud lunaire.',
    helpEn: 'Distance from the equator. Near the poles the Sun stays low on the horizon, as at the lunar south pole.' },
  { id: 'quake_count', unit: '', label: 'Séismes (depuis 2000)', labelEn: 'Earthquakes (since 2000)',
    help: 'Nombre de séismes de magnitude 2,5 ou plus à moins de 300 km depuis 2000. La Lune est sismiquement très calme.',
    helpEn: 'Number of magnitude 2.5+ earthquakes within 300 km since 2000. The Moon is seismically very quiet.' },
  { id: 'volcano_distance', unit: 'km', label: 'Distance au volcan', labelEn: 'Distance to a volcano',
    help: 'Distance au volcan récent le plus proche : la roche volcanique (basalte) sert de substitut au sol lunaire.',
    helpEn: 'Distance to the nearest recent volcano: volcanic rock (basalt) stands in for lunar ground.' },
] as const

// Types générés depuis apps/api/openapi.yaml : `npm run generate:api` après chaque changement du contrat.
type Schemas = components['schemas']

export type ParamId = Schemas['ParamId']
export type ModeId = Schemas['ModeId']
export type SiteRole = Schemas['AnalyzedSite']['role']
export type Verdict = Schemas['Verdict']
export type Criterion = Schemas['Criterion']
export type CriterionScore = Schemas['CriterionScore']
export type SiteResult = Schemas['AnalyzedSite']
export type AnalysisResponse = Schemas['AnalyzeResponse']
export type SiteDetail = Schemas['SiteDetail']
export type MoonValue = Schemas['MoonValue']
export type DataSource = Schemas['DataSource']
export type Mode = Schemas['Mode']

// Le catalogue affiché doit couvrir exactement les ParamId du contrat.
const catalogCoversContract: ParamId extends (typeof parameterCatalog)[number]['id'] ? true : false = true
void catalogCoversContract

/** Ce que vaut le paramètre sur la Lune quand le profil n'a pas d'intervalle chiffré (proxy ou contexte sourcé). */
export const MOON_NOTES: Partial<Record<ParamId, string>> = {
  t2m_mean: 'No air on the Moon: proxy for frozen ground',
  t2m_min: 'No air: proxy for extreme cold (29–50 K in shadow)',
  t2m_max: 'No air on the Moon',
  lst_day: 'Sunlit ridges: not sourced yet',
  lst_amplitude: 'About 300 K at the equator (Diviner)',
  solar: 'Near-continuous sunlight on some polar ridges',
  quake_count: '28 shallow moonquakes in 8 years (Apollo)',
  volcano_distance: 'No recent volcanism: basalt is an Earth stand-in',
  elevation: 'Not comparable',
}

/** Libellé, unité et aide d'un paramètre (interface en anglais). */
export function paramInfo(id: string, _lang: Lang = 'en'): { label: string; unit: string; help: string } {
  const p = parameterCatalog.find((item) => item.id === id)
  if (!p) return { label: id, unit: '', help: '' }
  return { label: p.labelEn, unit: 'unitEn' in p ? p.unitEn : p.unit, help: p.helpEn }
}

export type CalibrationInstrument = 'drill' | 'wind' | 'gas' | 'seismograph' | 'thermal'
export const calibrationInstruments: CalibrationInstrument[] = ['drill', 'wind', 'gas', 'seismograph', 'thermal']

function getApiUrl() {
  return (import.meta.env.VITE_API_URL || 'http://localhost:3001').replace(/\/+$/, '')
}

async function requestJson<T>(url: string, init?: RequestInit): Promise<T> {
  const response = await fetch(url, init)
  if (!response.ok) {
    let detail = ''
    try {
      detail = ((await response.json()) as { error?: string }).error ?? ''
    } catch {
      // corps non JSON : on garde le code HTTP
    }
    throw new Error(`HTTP ${response.status}${detail ? ` · ${detail}` : ''}`)
  }
  return (await response.json()) as T
}

export async function analyzeSites(
  request: { mode: ModeId; bareSoilOnly?: boolean } | { criteria: Criterion[]; bareSoilOnly?: boolean },
): Promise<AnalysisResponse> {
  return requestJson<AnalysisResponse>(`${getApiUrl()}/api/analyze`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(request),
  })
}

export async function getSiteDetails(siteId: string, signal: AbortSignal): Promise<SiteDetail> {
  return requestJson<SiteDetail>(`${getApiUrl()}/api/sites/${encodeURIComponent(siteId)}`, { signal })
}

/** Critères d'un mode prédéfini, tels que l'API les applique (source unique : apps/api/src/scoring/modes.ts). */
export async function getModeCriteria(mode: ModeId): Promise<Criterion[]> {
  const { modes } = await requestJson<{ modes: Mode[] }>(`${getApiUrl()}/api/modes`)
  const found = modes.find((m) => m.id === mode)
  if (!found) throw new Error(`Unknown mode: ${mode}`)
  return found.criteria
}

export async function getSources(): Promise<DataSource[]> {
  return (await requestJson<{ sources: DataSource[] }>(`${getApiUrl()}/api/sources`)).sources
}

/** Limites de la Terre comme analogue (data/reference/moon-south-pole.json, champ earth_limits). */
export interface EarthLimit {
  id: string
  label: string
  moon: string
  earth: string
  effect: string
  source: string
  en?: { label: string; moon: string; earth: string; effect: string }
}

export async function getEarthLimits(): Promise<EarthLimit[]> {
  const reference = await requestJson<{ earth_limits?: EarthLimit[] }>(`${getApiUrl()}/api/reference/moon`)
  return Array.isArray(reference.earth_limits) ? reference.earth_limits : []
}

/** Images précalculées de chaque site et de son jumeau lunaire (tools/precompute/site_visuals.py). */
export interface SiteVisual {
  photo?: { source: string; credit: string }
  earth: { slope_mean: number; slope_max: number | null; roughness: number; match_share: number }
  twin: { lat: number; lon: number; slope_mean: number; slope_max: number; roughness: number; distance: number; match_share: number }
}

export interface VisualManifest {
  extent_km: number
  pixel_m: number
  slope_band_deg: [number, number]
  moon_source: string
  earth_relief_source: string
  sites: Record<string, SiteVisual>
}

export async function getVisualManifest(): Promise<VisualManifest> {
  return requestJson<VisualManifest>(`${import.meta.env.BASE_URL}sites/manifest.json`)
}

export function siteImage(siteId: string, file: 'earth.jpg' | 'earth-relief.jpg' | 'earth-match.png' | 'moon-relief.jpg' | 'moon-match.png'): string {
  return `${import.meta.env.BASE_URL}sites/${siteId}/${file}`
}
