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
  geology?: GeologyShares | null
  context?: CellContext | null
}

/** T47: Earth context of a cell (models, never a similarity with the Moon). */
export interface CellContext {
  class: string
  frozen_e4: string | null
  magt_c: number | null
  magt_sd_c: number | null
  permafrost_prob: number | null
  aridity_index: number | null
  aridity_class: string | null
}

/** T46: share of the 9 samples of a cell (or mean over a zone) in each geology state, for the target's group. */
export interface GeologyShares {
  group: string
  source: string
  match: number | null
  partial: number | null
  no_match: number | null
  unresolved: number | null
  no_map: number | null
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

export interface QueryResult {
  release: string
  env: string
  matched: number
  area_km2: number
  cells: { id: string; lat: number; lon: number; typicality: number; confidence: string | null }[]
}

export function apiUrl(): string {
  return (import.meta.env.VITE_API_URL || 'http://localhost:3001').replace(/\/+$/, '')
}

// The documents of a release never change once published (ADR-004): read once per page, not once per screen.
const cache = new Map<string, Promise<unknown>>()

function get<T>(path: string, signal?: AbortSignal): Promise<T> {
  if (signal) return fetchJson<T>(path, signal)          // cells of a view: never cached, cancellable
  if (!cache.has(path)) {
    const p = fetchJson<T>(path)
    cache.set(path, p)
    p.catch(() => cache.delete(path))                     // a failure is retried next time
  }
  return cache.get(path) as Promise<T>
}

async function fetchJson<T>(path: string, signal?: AbortSignal): Promise<T> {
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

const q = (params: Record<string, string | number | undefined>) =>
  new URLSearchParams(Object.entries(params).filter(([, v]) => v !== undefined).map(([k, v]) => [k, String(v)])).toString()
const withRelease = (path: string, release?: string) => (release ? `${path}${path.includes('?') ? '&' : '?'}${q({ release })}` : path)

/** Every document call takes the release to read (the lunar default when absent; a Mars mission passes its own). */
/** T52: provenance of one 1° Earth tile (sources with version and date, computation date, code). */
export interface TileProvenance {
  release: string
  tile: string
  last_changed_in: string
  data_date: string | null
  scales: Record<string, { computed_at: string | null; computed_at_note?: string; code: string; inputs: { item: string; etag?: string | null; last_modified?: string | null }[] }>
}

export const v3 = {
  releases: () => get<ReleaseIndex>('releases'),
  release: (id: string) => get<{ release: string; run: string; geology?: unknown; context?: unknown; grid: { tau: number[]; min_cells: number[]; nominal: { tau: number; min_cells: number } } }>(`releases/${encodeURIComponent(id)}`),
  scenarios: (release?: string) => get<{ release: string; scenarios: Scenario[] }>(withRelease('scenarios', release)),
  coverage: (scenario: string, env: string, release?: string) => get<Coverage>(`coverage?${q({ scenario, env, release })}`),
  zones: (scenario: string, env: string, tau: number, minCells: number, limit = 50, release?: string) =>
    get<ZonePage>(`zones?${q({ scenario, env, tau, min_cells: minCells, limit, release })}`),
  zone: (id: string, release?: string) => get<ZoneDetail>(withRelease(`zones/${encodeURIComponent(id)}`, release)),
  method: (release?: string) => get<{ release: string; sources: MethodSource[]; processing: Record<string, unknown>[] }>(withRelease('method', release)),
  status: (release?: string) => get<Status>(withRelease('status', release)),
  tileProvenance: (tile: string, release?: string) => get<TileProvenance>(withRelease(`tiles/${encodeURIComponent(tile)}/provenance`, release)),
  sites: (scenario: string, release?: string) =>
    get<{ release: string; scenario: string; points: { id: string; cell: string | null; values: Record<string, CellProps> | null; reason?: string }[] }>(`sites?${q({ scenario, release })}`),
  query: async (body: Record<string, unknown>, release?: string) => {
    const response = await fetch(`${apiUrl()}/api/v3/${withRelease('query', release)}`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) })
    const data = (await response.json().catch(() => ({}))) as Record<string, unknown>
    if (!response.ok) throw new Error(typeof data.error === 'string' ? data.error : `HTTP ${response.status}`)
    return data as unknown as QueryResult
  },
  cells: (scenario: string, env: string, bbox: [number, number, number, number], signal?: AbortSignal, release?: string) =>
    get<CellCollection>(`cells?${q({ scenario, env, bbox: bbox.map((v) => v.toFixed(4)).join(','), release })}`, signal),
}

/** Address of a raster tile layer (zoom 0 to 7), in Leaflet's {z}/{x}/{y} template form. */
export function layerUrl(scenario: string, env: string, parameter: 'typicality' | 'coverage' | 'geology' | 'frozen' | 'aridity', release: string): string {
  return `${apiUrl()}/api/v3/layers/${encodeURIComponent(scenario)}/${encodeURIComponent(env)}/${parameter}/{z}/{x}/{y}.png?release=${encodeURIComponent(release)}`
}
