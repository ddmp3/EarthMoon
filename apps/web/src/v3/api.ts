import type { components } from '../api-schema'

// Types generated from apps/api/openapi.yaml (run `npm run generate:api` after every contract change).
type Schemas = components['schemas']
export type Zone = Schemas['Zone']
export type ZonePage = Schemas['ZonePage']
export type ZoneDetail = Schemas['ZoneDetail']
export type Coverage = Schemas['Coverage']
export type CoverageClassDoc = Schemas['CoverageClass']
export type Status = Schemas['Status']
export type Method = Schemas['Method']
export type ReleaseIndex = Schemas['ReleaseIndex']

/** A scenario as release.py writes it (the contract types it as an open V3 document). */
export interface Requirement {
  id: string
  what: string
  value: string
  expert_decision?: string
  eliminating: boolean
  rule: { param: string; at_most?: number; at_least?: number; scale?: string } | null
}
export interface Scenario {
  id: string
  name: string
  objective: string
  targets: string[]
  assessed_targets: string[]
  not_comparable: Record<string, string>
  similarity: { parameter: string; status: string; why: string }[]
  requirements: Requirement[]
  cannot_assess: string[]
}

/** A source of the Data and method panel (a catalogue entry, or one flagged "not in catalogue"). */
export interface MethodSource {
  id: string
  status: string
  verified_on?: string | null
  product?: string
  producer?: string
  url?: string
  coverage?: string
  resolution_spatial?: string
  uncertainty?: string
  limitations?: string
  licence?: string | null
  attribution?: string
}

/** One cell of the discovery service (GET /api/v3/cells), a GeoJSON feature. */
export interface CellProps {
  id: string
  lat: number
  lon: number
  typicality: { median: number | null; p25: number | null; p75: number | null }
  windows: { valid: number | null; total: number | null }
  coverage: string
  confidence: string | null
  masked_share: number | null
  requirements: Record<string, string | null>
}
export interface CellFeature {
  type: 'Feature'
  geometry: { type: 'Polygon'; coordinates: number[][][] }
  properties: CellProps
}
export interface CellCollection {
  release: string
  methodology_version: string
  env: string
  features: CellFeature[]
}

export function apiUrl(): string {
  return (import.meta.env.VITE_API_URL || 'http://localhost:3001').replace(/\/+$/, '')
}

async function get<T>(path: string, signal?: AbortSignal): Promise<T> {
  const response = await fetch(`${apiUrl()}/api/v3/${path}`, signal ? { signal } : undefined)
  if (!response.ok) {
    let detail = ''
    try {
      detail = ((await response.json()) as { error?: string }).error ?? ''
    } catch {
      // non-JSON body: keep the HTTP status
    }
    throw new Error(`HTTP ${response.status}${detail ? ` · ${detail}` : ''}`)
  }
  return (await response.json()) as T
}

const q = (params: Record<string, string | number>) => new URLSearchParams(Object.entries(params).map(([k, v]) => [k, String(v)])).toString()

export const v3 = {
  releases: () => get<ReleaseIndex>('releases'),
  release: (id: string) => get<{ release: string; run: string; grid: { tau: number[]; min_cells: number[]; nominal: { tau: number; min_cells: number } } }>(`releases/${encodeURIComponent(id)}`),
  scenarios: () => get<{ release: string; scenarios: Scenario[] }>('scenarios'),
  coverage: (scenario: string, env: string) => get<Coverage>(`coverage?${q({ scenario, env })}`),
  zones: (scenario: string, env: string, tau: number, minCells: number, limit = 50) =>
    get<ZonePage>(`zones?${q({ scenario, env, tau, min_cells: minCells, limit })}`),
  zone: (id: string) => get<ZoneDetail>(`zones/${encodeURIComponent(id)}`),
  method: () => get<{ release: string; sources: MethodSource[]; processing: Record<string, unknown>[] }>('method'),
  status: () => get<Status>('status'),
  cells: (scenario: string, env: string, bbox: [number, number, number, number], signal?: AbortSignal) =>
    get<CellCollection>(`cells?${q({ scenario, env, bbox: bbox.map((v) => v.toFixed(4)).join(',') })}`, signal),
}

/** Address of a raster tile layer (zoom 0 to 7), in Leaflet's {z}/{x}/{y} template form. */
export function layerUrl(scenario: string, env: string, parameter: 'typicality' | 'coverage', release: string): string {
  return `${apiUrl()}/api/v3/layers/${encodeURIComponent(scenario)}/${encodeURIComponent(env)}/${parameter}/{z}/{x}/{y}.png?release=${encodeURIComponent(release)}`
}
