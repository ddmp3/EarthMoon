import type { CellProps, Coverage, GeologyShares, Status, TileProvenance, Zone } from './api'
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
export function statusLines(s: Status, t: V3Texts): { state: 'validated' | 'not_validated'; validity: string; failing: string | null; freshness: string; impact: string | null } {
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
    impact: impactLine(s, t),
  }
}

/** T52b: what the detected updates would recompute; the refresher never starts it. */
function impactLine(s: Status, t: V3Texts): string | null {
  const imp = (s.freshness as { impact?: { tiles_reassessed?: number; cpu_hours_estimate?: number | null }[] }).impact ?? []
  if (!imp.length) return null
  const tiles = imp.reduce((a, i) => a + (i.tiles_reassessed ?? 0), 0)
  if (imp.some((i) => i.cpu_hours_estimate == null)) return t.impactLineUnmeasured(imp.length, tiles)
  const hours = imp.reduce((a, i) => a + (i.cpu_hours_estimate ?? 0), 0)
  return t.impactLine(imp.length, tiles, hours)
}

/** Figures of the home banner of a body, read from its current release (T45c): cells assessed, targets compared,
 * sources, scenarios with a positive validation. Null until the release is loaded: nothing is typed by hand. */
export function homeFigures(
  v: { release: { processing?: { step: string; cells?: number }[] } | null; scenarios: { assessed_targets: string[] }[]; method: { sources: unknown[] } | null; status: Status | null },
  body: 'moon' | 'mars', lang: 'en' | 'fr',
  labels: { cells: string; targetsMoon: string; targetsMars: string; sources: string; positive: string },
): { value: string; label: string }[] | null {
  const cells = v.release?.processing?.find((p) => p.step === 'cells')?.cells
  if (cells == null || !v.scenarios.length || !v.method || !v.status) return null
  const m = (Math.round(cells / 1e5) / 10).toFixed(1)
  const targets = new Set(v.scenarios.flatMap((s) => s.assessed_targets)).size
  const positive = v.status.validity.checks.find((c) => c.check === 'positives')?.pass === true ? v.scenarios.length : 0
  return [
    { value: `${lang === 'fr' ? m.replace('.', ',') : m} M`, label: labels.cells },
    { value: String(targets), label: body === 'mars' ? labels.targetsMars : labels.targetsMoon },
    { value: String(v.method.sources.length), label: labels.sources },
    { value: String(positive), label: labels.positive },
  ]
}

/** Cells the discovery service serves in one view at most (apps/discovery/core.py CELL_CAP, ADR-004). */
export const CELL_CAP = 5000
const CELL_KM2 = 25.04

/** Expected number of 5 km cells in a view [west, south, east, north] (its area on the sphere / 25.04 km²). */
export function cellsInView(b: [number, number, number, number]): number {
  const R = 6371.0088
  const rad = Math.PI / 180
  const area = R * R * Math.max(0, b[2] - b[0]) * rad * Math.abs(Math.sin(b[3] * rad) - Math.sin(b[1] * rad))
  return area / CELL_KM2
}

/** Source product of a file read by an Earth tile (names as in the catalogue). */
function sourceName(item: string): string {
  if (item.includes('Copernicus_DSM_COG_10')) return 'Copernicus DEM GLO-30'
  if (item.includes('Copernicus_DSM_COG_30')) return 'Copernicus DEM GLO-90'
  if (item.includes('WorldCover')) return 'ESA WorldCover'
  return item.split('/')[0]
}

/** Lines of the provenance of one Earth tile (T52): each source with its latest file date, the computation date,
 * and the release where the tile last changed. */
export function provenanceLines(p: TileProvenance, t: V3Texts): { tile: string; sources: string[]; computed: string; since: string } {
  const latest = new Map<string, string>()
  const computed: string[] = []
  let notRecorded = 0
  for (const s of Object.values(p.scales)) {
    if (s.computed_at) computed.push(s.computed_at)
    else notRecorded += 1
    for (const i of s.inputs) {
      const name = sourceName(i.item)
      const d = i.last_modified ?? ''
      if (d > (latest.get(name) ?? '')) latest.set(name, d)
    }
  }
  computed.sort()
  const parts = [computed.length ? t.provComputed(ddmm(computed[computed.length - 1])) : '', notRecorded ? t.provNotRecorded(notRecorded) : '']
  return {
    tile: t.provTile(p.tile),
    sources: [...latest.entries()].sort(([a], [b]) => a.localeCompare(b)).map(([n, d]) => t.provSource(n, d ? ddmm(d) : '—')),
    computed: parts.filter(Boolean).join('; ').replace(/^./, (c) => c.toUpperCase()),
    since: t.provSince(p.last_changed_in),
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
/** Rows of the zone list: the place name when the release has one (T45c), the coordinates in the details. */
export function zoneItems(zones: Zone[], t: V3Texts, lang: 'en' | 'fr' = 'en') {
  return zones.map((z) => ({
    id: z.id, lat: z.lat, lon: z.lon, value: z.typicality.median, name: z.place?.[lang] ?? null,
    sub: t.cellsArea(z.cells, z.area_km2),
  }))
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

