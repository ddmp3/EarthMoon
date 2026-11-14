export const parameterCatalog = [
  { id: 'slope_mean', label: 'Pente moyenne', unit: '°' },
  { id: 'slope_max', label: 'Pente maximale', unit: '°' },
  { id: 'roughness', label: 'Rugosité', unit: 'm' },
  { id: 'elevation', label: 'Altitude', unit: 'm' },
  { id: 'ndvi', label: 'Végétation (NDVI)', unit: '' },
  { id: 'lst_day', label: 'Température de surface, jour', unit: '°C' },
  { id: 'lst_night', label: 'Température de surface, nuit', unit: '°C' },
  { id: 'lst_amplitude', label: 'Amplitude thermique', unit: '°C' },
  { id: 't2m_mean', label: 'Température moyenne de l’air', unit: '°C' },
  { id: 't2m_min', label: 'Température minimale de l’air', unit: '°C' },
  { id: 't2m_max', label: 'Température maximale de l’air', unit: '°C' },
  { id: 'wind', label: 'Vent', unit: 'm/s' },
  { id: 'humidity', label: 'Humidité', unit: '%' },
  { id: 'precipitation', label: 'Précipitations', unit: 'mm/j' },
  { id: 'solar', label: 'Ensoleillement', unit: 'kWh/m²/j' },
  { id: 'latitude_abs', label: 'Latitude absolue', unit: '°' },
  { id: 'quake_count', label: 'Séismes (depuis 2000)', unit: '' },
  { id: 'volcano_distance', label: 'Distance au volcan', unit: 'km' },
] as const

export type ParamId = (typeof parameterCatalog)[number]['id']
export type ModeId = 'robotics' | 'calibration' | 'colony'
export type SiteRole = 'validation' | 'negative' | 'candidate'
export type Verdict = 'match' | 'partial' | 'mismatch' | 'missing'
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

export interface Criterion {
  param: ParamId
  min?: number
  max?: number
  tolerance: number
  weight: number
  group?: string
}

export const calibrationCriteria: Criterion[] = [
  { param: 't2m_mean', max: 0, tolerance: 10, weight: 2, group: 'drill' },
  { param: 'volcano_distance', max: 50, tolerance: 100, weight: 1, group: 'drill' },
  { param: 'wind', max: 3, tolerance: 3, weight: 2, group: 'wind' },
  { param: 'humidity', max: 40, tolerance: 30, weight: 2, group: 'gas' },
  { param: 'precipitation', max: 0.5, tolerance: 1, weight: 1, group: 'gas' },
  { param: 'quake_count', max: 5, tolerance: 20, weight: 3, group: 'seismograph' },
  { param: 'lst_amplitude', min: 25, tolerance: 15, weight: 2, group: 'thermal' },
  { param: 't2m_min', max: -30, tolerance: 20, weight: 1, group: 'thermal' },
]

export interface CriterionScore {
  param: ParamId
  value: number | null
  score: number
  verdict: Verdict
}

export interface SiteResult {
  id: string
  name: string
  lat: number
  lon: number
  role: SiteRole
  total: number
  criteria: CriterionScore[]
  excluded?: 'vegetation'
}

export interface SiteView extends Omit<SiteResult, 'total'> {
  total: number | null
  values?: Partial<Record<ParamId, number | null>>
}

export interface AnalysisResponse {
  mode?: ModeId | 'custom'
  sites: SiteResult[]
}

export interface SiteDetail extends SiteResult {
  values: Partial<Record<ParamId, number | null>>
  sources: unknown
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
