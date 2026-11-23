import type { CellProps, Coverage, GeologyShares, Status, Zone } from './api'
import type { V3Texts } from './text'

/** Overlay classes in the order release.py assigns them (the first that applies wins). */
export const COVERAGE_ORDER = ['screened_out', 'no_data', 'ground_hidden', 'partial', 'low_confidence', 'evaluated'] as const
export type CoverageClass = (typeof COVERAGE_ORDER)[number]

/** SVG pattern of each overlay class (defined once in Patterns.tsx). States differ by pattern, not only colour. */
export const PATTERN: Record<CoverageClass, string> = {
  screened_out: 'pat-dots',
  no_data: 'pat-dense',
  ground_hidden: 'pat-hidden',
  partial: 'pat-light',
  low_confidence: 'pat-outline',
  evaluated: 'pat-none',
}

export type MapState = 'evaluated' | 'partial' | 'not_evaluated' | 'masked'

/** The four map states of the spec (T26), from a cell's overlay class. */
export function cellState(c: CellProps, t: V3Texts): { state: MapState; text: string } {
  let state: MapState
  if (c.coverage === 'ground_hidden') state = 'masked'
  else if (c.coverage === 'screened_out' || c.coverage === 'no_data' || c.typicality.median === null) state = 'not_evaluated'
  else if (c.coverage === 'partial') state = 'partial'
  else state = 'evaluated'
  return { state, text: t.states[state] }
}

export interface LegendRow {
  id: CoverageClass
  label: string
  meaning: string
  share: number | null
  km2: number
  pattern: string
}

export function legendRows(cov: Coverage['coverage'], t: V3Texts): LegendRow[] {
  return COVERAGE_ORDER.map((id) => {
    const c = cov.classes[id]
    return { id, label: t.coverageClass[id], meaning: c?.meaning ?? '', share: c?.share ?? null, km2: c?.km2 ?? 0, pattern: PATTERN[id] }
  })
}

export interface Layer {
  id: 'topography' | 'geology' | 'frozen' | 'aridity' | 'thermal' | 'operational' | 'multi'
  label: string
  enabled: boolean
  reason: string | null
}

/** Every dimension is listed; one that waits for a later task is disabled with its reason, never hidden.
 *  `available`: the dimensions the release carries (topography always; geology once T46 is in the release). */
export function layerList(t: V3Texts, available: string[] = ['topography']): Layer[] {
  return (['topography', 'geology', 'frozen', 'aridity', 'thermal', 'operational', 'multi'] as const).map((id) => {
    const on = id === 'topography' || available.includes(id)
    return { id, label: t.layer[id], enabled: on, reason: on ? null : t.layerWait[id] }
  })
}

export interface DimensionRow {
  name: string
  median: number | null
  p25: number | null
  p75: number | null
  n: number | null
  source: string | null
  missing: string | null
  /** a dimension reported as shares of states rather than a value with its spread (geology) */
  text?: string
}

/** Rows of the zone card: topography with its spread, then the dimensions not evaluated yet, by name. */
export function geologyText(g: GeologyShares | null | undefined, t: V3Texts): string | null {
  if (!g || g.match === null) return null
  return t.geoSummary(g.match ?? 0, g.partial ?? 0, g.no_match ?? 0, (g.unresolved ?? 0) + (g.no_map ?? 0))
}

export interface ZoneContext {
  frozen_e4: Record<string, number>
  magt_c_median: number | null
  aridity: Record<string, number>
}

export function contextRows(ctx: ZoneContext | null | undefined, t: V3Texts): DimensionRow[] {
  if (!ctx) {
    return [{ name: t.layer.thermal, median: null, p25: null, p75: null, n: null, source: null, missing: t.layerWait.thermal }]
  }
  const f = ctx.frozen_e4
  const ar = Object.entries(ctx.aridity).filter(([, v]) => v > 0).sort((a, b) => b[1] - a[1])
    .map(([k, v]) => `${t.aridityName[k] ?? k} ${Math.round(v * 100)}%`).join(' · ')
  return [
    { name: t.layer.frozen, median: null, p25: null, p75: null, n: null, source: 'Obu et al. 2018', missing: null,
      text: t.frozenSummary(f.met ?? 0, f.partial ?? 0, f.failed ?? 0, f['not covered'] ?? 0, ctx.magt_c_median) },
    { name: t.layer.aridity, median: null, p25: null, p75: null, n: null, source: 'Global Aridity Index v3.1', missing: null, text: ar || '—' },
    { name: t.layer.thermal, median: null, p25: null, p75: null, n: null, source: null, missing: t.layerWait.thermal },
  ]
}

export function zoneDimensions(spread: { median: number; p25: number; p75: number }, windows: number, t: V3Texts,
  geology: GeologyShares | null = null, context: ZoneContext | null = null): DimensionRow[] {
  const geo = geologyText(geology, t)
  return [
    { name: t.layer.topography, ...spread, n: windows, source: t.demSource, missing: null },
    geo
      ? { name: t.layer.geology, median: null, p25: null, p75: null, n: null, source: t.geoSource, missing: null, text: geo }
      : { name: t.layer.geology, median: null, p25: null, p75: null, n: null, source: null, missing: t.geologyMissing },
    ...contextRows(context, t),
  ]
}

const ddmm = (iso: string) => {
  const m = /^(\d{4})-(\d{2})-(\d{2})/.exec(iso)
  return m ? `${m[3]}/${m[2]}/${m[1]}` : iso
}

/** Text of the validity and freshness indicators (ADR-009). */
export function statusLines(s: Status, t: V3Texts): { state: 'validated' | 'not_validated'; validity: string; failing: string | null; freshness: string } {
  const v = s.validity
  const fmt = v.state === 'validated' ? t.validity.validated : t.validity.not_validated
  const failed = v.checks.filter((c) => c.pass !== true).map((c) => t.checkName[c.check] ?? c.check)
  const sources = s.freshness.sources
  const states = new Set(sources.map((x) => x.state))
  const freshness = !s.freshness.refresher && states.size <= 1 && (states.has('not_checkable') || states.size === 0)
    ? t.freshnessManual(sources.length)
    : [...states].map((st) => `${t.freshness[st] ?? st}: ${sources.filter((x) => x.state === st).length}`).join(' · ')
  return {
    state: v.state,
    validity: fmt(v.protocol, v.release, ddmm(v.published)),
    failing: failed.length ? t.validity.failing(failed.join(', ')) : null,
    freshness,
  }
}

/** Equirectangular → Web Mercator tile of zoom z that holds a point (for e2e and links). */
export function tileOf(lat: number, lon: number, z: number): { x: number; y: number } {
  const n = 2 ** z
  const r = (lat * Math.PI) / 180
  return { x: Math.floor(((lon + 180) / 360) * n), y: Math.floor(((1 - Math.log(Math.tan(r) + 1 / Math.cos(r)) / Math.PI) / 2) * n) }
}

/** Cividis (matplotlib 3.10.8, data/ui/cividis.json), 11 stops, linear between them: the colour of a typicality. */
const CIVIDIS: [number, number, number][] = [
  [0, 34, 78], [12, 52, 112], [53, 69, 108], [79, 87, 108], [102, 105, 112], [125, 124, 120],
  [148, 142, 119], [173, 162, 114], [200, 184, 102], [229, 207, 82], [254, 232, 56],
]

export function cividis(v: number): string {
  const x = Math.min(1, Math.max(0, v)) * 10
  const i = Math.min(9, Math.floor(x))
  const f = x - i
  const [a, b] = [CIVIDIS[i], CIVIDIS[i + 1]]
  const c = a.map((u, k) => Math.round(u + (b[k] - u) * f))
  return `rgb(${c[0]}, ${c[1]}, ${c[2]})`
}

/** Hover text of a cell (map spec "Hover on a cell"): every line is text, a missing value is said by name. */
export function cellLines(c: CellProps, t: V3Texts): string[] {
  const ns = `${Math.abs(c.lat).toFixed(2)}${c.lat >= 0 ? 'N' : 'S'} ${Math.abs(c.lon).toFixed(2)}${c.lon >= 0 ? 'E' : 'W'}`
  const s = cellState(c, t)
  const m = c.typicality
  const n = c.windows.valid !== null && c.windows.total !== null ? `n=${c.windows.valid}/${c.windows.total}` : ''
  const topo = m.median === null
    ? `${t.layer.topography}: ${t.states.not_evaluated}`
    : `${t.layer.topography} ${m.median.toFixed(2)}  ${t.iqr} ${m.p25?.toFixed(2) ?? '—'}–${m.p75?.toFixed(2) ?? '—'}  ${n}`.trim()
  const cov = (t.coverageClass as Record<string, string>)[c.coverage] ?? c.coverage
  return [
    `${t.cell} ${ns}  (${t.cellSize})`,
    topo,
    `${t.layer.geology}: ${geologyText(c.geology, t) ?? t.geologyMissing}`,
    `${t.state}: ${s.text}`,
    `${t.maskedLabel}: ${c.masked_share === null ? '—' : `${Math.round(c.masked_share * 100)}%`}   ${t.confidenceLabel}: ${c.confidence ?? '—'}`,
    `${t.coverageLabel}: ${cov}`,
  ]
}

/** Rows of the zone list (same rows as the ranked sites). */
export function zoneItems(zones: Zone[], t: V3Texts) {
  return zones.map((z) => ({ id: z.id, lat: z.lat, lon: z.lon, value: z.typicality.median, sub: t.cellsArea(z.cells, z.area_km2) }))
}

/** Geology class of a cell for the map, as the tiles draw it (tools/discovery/tiles.geology_class). */
export function geologyClass(c: CellProps): number {
  const g = c.geology
  if (!g || g.match === null) return 0
  if ((g.match ?? 0) >= 0.5) return 1
  if ((g.match ?? 0) + (g.partial ?? 0) >= 0.5) return 2
  if ((g.no_match ?? 0) >= 0.5) return 3
  return 4
}

