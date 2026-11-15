import type { components } from './api-schema'

// `help` : texte d'aide grand public (ce que mesure le paramètre, et ce qu'il représente pour la Lune).
export const parameterCatalog = [
  { id: 'slope_mean', label: 'Pente moyenne', unit: '°', help: 'Inclinaison moyenne du terrain sur 1 km. Au pôle Sud lunaire, la moitié des zones de 1 km ont une pente moyenne entre 5 et 13° (LOLA).' },
  { id: 'slope_max', label: 'Pente maximale', unit: '°', help: 'Pente la plus forte sur 1 km : elle dit si un rover peut passer. Les rovers lunaires franchissent de 15 à 25°.' },
  { id: 'roughness', label: 'Rugosité', unit: 'm', help: 'Variation de l’altitude sur 1 km : un terrain rugueux est accidenté, cratérisé.' },
  { id: 'elevation', label: 'Altitude', unit: 'm', help: 'Altitude du site au-dessus du niveau de la mer.' },
  { id: 'ndvi', label: 'Végétation (NDVI)', unit: '', help: 'Indice de végétation mesuré par satellite. Au-delà de 0,2, il y a des plantes : le site ne ressemble pas à la Lune.' },
  { id: 'lst_day', label: 'Température de surface, jour', unit: '°C', help: 'Température du sol le jour, vue par satellite (moyenne annuelle).' },
  { id: 'lst_night', label: 'Température de surface, nuit', unit: '°C', help: 'Température du sol la nuit. Sur la Lune, les cratères à l’ombre descendent à -240 °C : aucun site terrestre n’en approche.' },
  { id: 'lst_amplitude', label: 'Amplitude thermique', unit: '°C', help: 'Écart entre le jour et la nuit. Sur la Lune, il atteint environ 300 °C ; sur Terre, les déserts en donnent une petite idée.' },
  { id: 't2m_mean', label: 'Température moyenne de l’air', unit: '°C', help: 'Température moyenne de l’air : un site très froid a un sol gelé, comparable au sol glacé lunaire.' },
  { id: 't2m_min', label: 'Température minimale de l’air', unit: '°C', help: 'Température la plus basse de l’année : utile pour tester le matériel au froid.' },
  { id: 't2m_max', label: 'Température maximale de l’air', unit: '°C', help: 'Température la plus haute de l’année.' },
  { id: 'wind', label: 'Vent', unit: 'm/s', help: 'Vitesse moyenne du vent. La Lune n’a pas d’atmosphère, donc pas de vent : un site calme s’en rapproche.' },
  { id: 'humidity', label: 'Humidité', unit: '%', help: 'Humidité de l’air. La Lune n’en a pas : un air sec s’en rapproche.' },
  { id: 'precipitation', label: 'Précipitations', unit: 'mm/j', help: 'Pluie ou neige par jour. Un sol sec et meuble se rapproche du régolithe lunaire.' },
  { id: 'solar', label: 'Ensoleillement', unit: 'kWh/m²/j', help: 'Énergie solaire reçue par jour : utile pour alimenter une base.' },
  { id: 'latitude_abs', label: 'Latitude absolue', unit: '°', help: 'Distance à l’équateur. Près des pôles, le Soleil reste bas sur l’horizon, comme au pôle Sud lunaire.' },
  { id: 'quake_count', label: 'Séismes (depuis 2000)', unit: '', help: 'Nombre de séismes de magnitude 2,5 ou plus à moins de 300 km depuis 2000. La Lune est sismiquement très calme.' },
  { id: 'volcano_distance', label: 'Distance au volcan', unit: 'km', help: 'Distance au volcan récent le plus proche : la roche volcanique (basalte) sert de substitut au sol lunaire.' },
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

export type CalibrationInstrument =
  | 'drill'
  | 'wind'
  | 'gas'
  | 'seismograph'
  | 'thermal'

export const calibrationInstruments: {
  id: CalibrationInstrument
  label: string
}[] = [
  { id: 'drill', label: 'Forage' },
  { id: 'wind', label: 'Vent' },
  { id: 'gas', label: 'Gaz' },
  { id: 'seismograph', label: 'Sismographe' },
  { id: 'thermal', label: 'Thermique' },
]

export interface SiteView extends Omit<SiteResult, 'total'> {
  total: number | null
  values?: Partial<Record<ParamId, number | null>>
}

export interface FixtureSite {
  id: string
  name: string
  lat: number
  lon: number
  terrain: string
  role: SiteRole
  values: Partial<Record<ParamId, number | null>>
}

function getApiUrl() {
  return (import.meta.env.VITE_API_URL || 'http://localhost:3001').replace(
    /\/+$/,
    '',
  )
}

async function requestJson<T>(url: string, init?: RequestInit): Promise<T> {
  const response = await fetch(url, init)
  if (!response.ok) {
    const details = await response.text()
    throw new Error(
      `L’API a répondu ${response.status}${details ? ` : ${details}` : ''}`,
    )
  }
  return (await response.json()) as T
}

export async function analyzeSites(
  request:
    | { mode: ModeId; bareSoilOnly?: boolean }
    | { criteria: Criterion[]; bareSoilOnly?: boolean },
): Promise<AnalysisResponse> {
  return requestJson<AnalysisResponse>(`${getApiUrl()}/api/analyze`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(request),
  })
}

export async function getSiteDetails(
  siteId: string,
  signal: AbortSignal,
): Promise<SiteDetail> {
  return requestJson<SiteDetail>(
    `${getApiUrl()}/api/sites/${encodeURIComponent(siteId)}`,
    { signal },
  )
}

/** Critères d'un mode prédéfini, tels que l'API les applique (source unique : apps/api/src/scoring/modes.ts). */
export async function getModeCriteria(mode: ModeId): Promise<Criterion[]> {
  const { modes } = await requestJson<{ modes: Mode[] }>(`${getApiUrl()}/api/modes`)
  const found = modes.find((m) => m.id === mode)
  if (!found) throw new Error(`L’API ne connaît pas le mode « ${mode} ».`)
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
}

export async function getEarthLimits(): Promise<EarthLimit[]> {
  const reference = await requestJson<{ earth_limits?: EarthLimit[] }>(`${getApiUrl()}/api/reference/moon`)
  return Array.isArray(reference.earth_limits) ? reference.earth_limits : []
}
