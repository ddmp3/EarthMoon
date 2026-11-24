import { describe, expect, it } from 'vitest'
import { parameterCatalog } from '../api'
import { paramInfo } from '../api'
import coverage from '../test/fixtures/v3/coverage.json'
import scenarios from '../test/fixtures/v3/scenarios.json'
import status from '../test/fixtures/v3/status.json'
import type { CellProps, Coverage, Scenario, Status } from './api'
import { cellState, COVERAGE_ORDER, layerList, legendRows, provenanceLines, statusLines, zoneDimensions } from './model'
import { V3_TEXTS } from './text'

const en = V3_TEXTS.en
const fr = V3_TEXTS.fr

function keys(o: unknown, prefix = ''): string[] {
  if (o === null || typeof o !== 'object') return [prefix]
  return Object.entries(o as Record<string, unknown>).flatMap(([k, v]) => (typeof v === 'function' ? [`${prefix}${k}()`] : keys(v, `${prefix}${k}.`)))
}

const cell = (over: Partial<CellProps>): CellProps => ({
  id: '1', lat: 1, lon: 2, typicality: { median: 0.7, p25: 0.6, p75: 0.8 }, windows: { valid: 24, total: 25 },
  coverage: 'evaluated', confidence: 'high', masked_share: 0, requirements: {}, ...over,
})

describe('map states', () => {
  it('maps each overlay class to one of the four states, with a text equivalent', () => {
    expect(cellState(cell({ coverage: 'evaluated' }), en)).toEqual({ state: 'evaluated', text: 'Evaluated' })
    expect(cellState(cell({ coverage: 'low_confidence', confidence: 'low' }), en).state).toBe('evaluated')
    expect(cellState(cell({ coverage: 'partial' }), en)).toEqual({ state: 'partial', text: 'Partial: fewer than half the windows valid' })
    expect(cellState(cell({ coverage: 'screened_out' }), en).state).toBe('not_evaluated')
    expect(cellState(cell({ coverage: 'no_data' }), en).state).toBe('not_evaluated')
    expect(cellState(cell({ coverage: 'ground_hidden' }), en)).toEqual({ state: 'masked', text: 'Masked: ground hidden' })
  })

  it('a cell without a typicality is never shown as evaluated', () => {
    expect(cellState(cell({ coverage: 'evaluated', typicality: { median: null, p25: null, p75: null } }), en).state).toBe('not_evaluated')
  })
})

describe('coverage legend', () => {
  it('lists the six classes in the overlay order, with their land share and a pattern', () => {
    const rows = legendRows((coverage as unknown as Coverage).coverage, en)
    expect(rows.map((r) => r.id)).toEqual(COVERAGE_ORDER)
    expect(rows.map((r) => r.label)).toEqual(['Screened out', 'No data', 'Ground hidden', 'Partial', 'Low confidence', 'Evaluated'])
    const total = rows.reduce((s, r) => s + (r.share ?? 0), 0)
    expect(total).toBeGreaterThan(0.99)
    expect(total).toBeLessThan(1.01)
    expect(new Set(rows.map((r) => r.pattern)).size).toBe(6)
    for (const r of rows) expect(r.meaning.length).toBeGreaterThan(10)
  })
})

describe('layers', () => {
  it('lists every dimension; the ones waiting for a later task stay visible, disabled, with the reason', () => {
    const layers = layerList(en)
    expect(layers.map((l) => l.id)).toEqual(['topography', 'geology', 'frozen', 'aridity', 'thermal', 'operational', 'multi'])
    expect(layers.filter((l) => l.enabled).map((l) => l.id)).toEqual(['topography'])
    expect(layers.find((l) => l.id === 'geology')?.reason).toBe('available after T46')
    expect(layers.find((l) => l.id === 'multi')?.reason).toBe('needs two non-redundant dimensions')
  })
})

describe('zone dimensions', () => {
  it('gives topography with its spread and lists the dimensions not evaluated by name', () => {
    const rows = zoneDimensions({ median: 0.81, p25: 0.66, p75: 0.9 }, 214, en)
    expect(rows[0]).toMatchObject({ name: 'Topography (slope)', median: 0.81, p25: 0.66, p75: 0.9, n: 214, source: 'Copernicus DEM GLO-30' })
    expect(rows.slice(1).map((r) => [r.name, r.missing])).toEqual([
      ['Geology', 'not evaluated (T46)'],
      ['Surface thermal cycling', 'waits for MODIS (NASA Earthdata account, data improvement D1)'],
    ])
  })
})

describe('validity and freshness (ADR-009)', () => {
  it('says not validated and names the checks that did not pass', () => {
    const lines = statusLines(status as unknown as Status, en)
    expect(lines.validity).toMatch(/^Not validated · validation-protocol-v3 · release r-7a96120e/)
    expect(lines.failing).toBe('Checks not passed: positive controls (none exist), masks, self-consistency')
    expect(lines.freshness).toMatch(/sources, no automatic check yet/)
    expect(lines.state).toBe('not_validated')
  })

  it('has a text for every freshness state, in both languages', () => {
    for (const s of ['up_to_date', 'first_check', 'update_detected', 'update_in_progress', 'update_held', 'check_failed', 'check_overdue', 'not_checkable', 'newer_release']) {
      expect(en.freshness[s], s).toBeTruthy()
      expect(fr.freshness[s], s).toBeTruthy()
    }
  })

  it('says validated when every check passed', () => {
    const ok = structuredClone(status) as unknown as Status
    ok.validity.state = 'validated'
    ok.validity.checks = ok.validity.checks.map((c) => ({ ...c, pass: true }))
    const lines = statusLines(ok, en)
    expect(lines.validity).toMatch(/^Validated · /)
    expect(lines.failing).toBeNull()
  })
})

describe('texts', () => {
  it('French has exactly the English keys', () => {
    expect(keys(fr).sort()).toEqual(keys(en).sort())
  })

  it('every scenario target has a name in both languages', () => {
    for (const s of (scenarios as unknown as { scenarios: Scenario[] }).scenarios) {
      for (const t of s.targets) {
        expect(en.targetName[t], t).toBeTruthy()
        expect(fr.targetName[t], t).toBeTruthy()
      }
    }
  })

  it('every parameter id has a label', () => {
    for (const p of parameterCatalog) {
      expect(paramInfo(p.id, 'en').label).not.toBe(p.id)
      expect(paramInfo(p.id, 'fr').label).not.toBe(p.id)
    }
  })
})

describe('colour scale', () => {
  it('uses the cividis stops of data/ui/cividis.json at 0, 0.5 and 1, and clamps', async () => {
    const { cividis } = await import('./model')
    expect(cividis(0)).toBe('rgb(0, 34, 78)')
    expect(cividis(0.5)).toBe('rgb(125, 124, 120)')
    expect(cividis(1)).toBe('rgb(254, 232, 56)')
    expect(cividis(2)).toBe(cividis(1))
  })
})

describe('cell hover', () => {
  it('gives place, value with spread and windows, missing geology by name, state, masks, confidence and coverage', async () => {
    const { cellLines } = await import('./model')
    const lines = cellLines(cell({ lat: 41.73, lon: -121.51, typicality: { median: 0.64, p25: 0.48, p75: 0.77 }, windows: { valid: 24, total: 25 }, confidence: 'medium', masked_share: 0.04 }), en)
    expect(lines).toEqual([
      'Cell 41.73N 121.51W  (5 km, equal-area)',
      'Topography (slope) 0.64  IQR 0.48–0.77  n=24/25',
      'Geology: not evaluated (T46)',
      'State: Evaluated',
      'Masked share: 4%   Confidence: medium',
      'Coverage: Evaluated',
    ])
    expect(cellLines(cell({ typicality: { median: null, p25: null, p75: null }, coverage: 'no_data' }), en)[1]).toBe('Topography (slope): Not evaluated')
  })
})

describe('release documents are read once per page', () => {
  it('a second call for the same document does not fetch again; cells are never cached', async () => {
    const { v3 } = await import('./api')
    const calls: string[] = []
    const real = globalThis.fetch
    globalThis.fetch = (async (url: string) => {
      calls.push(String(url))
      return new Response(JSON.stringify({ release: 'r-1', scenarios: [] }), { status: 200 })
    }) as typeof fetch
    try {
      await v3.scenarios()
      await v3.scenarios()
      expect(calls.filter((u) => u.endsWith('/api/v3/scenarios'))).toHaveLength(1)
      const c = new AbortController()
      await v3.cells('B', 'moon-psr', [0, 0, 1, 1], c.signal)
      await v3.cells('B', 'moon-psr', [0, 0, 1, 1], c.signal)
      expect(calls.filter((u) => u.includes('/api/v3/cells'))).toHaveLength(2)
    } finally {
      globalThis.fetch = real
    }
  })
})


describe('geology (T46)', () => {
  it('turns on the geology layer when the release carries it', async () => {
    const { layerList } = await import('./model')
    expect(layerList(en, ['topography', 'geology']).filter((l) => l.enabled).map((l) => l.id)).toEqual(['topography', 'geology'])
    expect(layerList(en).find((l) => l.id === 'geology')?.reason).toBe('available after T46')
  })

  it('reports a zone as shares of geology states, and as not evaluated without geology', async () => {
    const { zoneDimensions } = await import('./model')
    const g = { group: 'highland', source: 'Macrostrat', match: 0.75, partial: 0.25, no_match: 0, unresolved: 0, no_map: 0 }
    expect(zoneDimensions({ median: 0.8, p25: 0.7, p75: 0.9 }, 100, en, g)[1]).toMatchObject({
      name: 'Geology', missing: null, text: '75% match · 25% partial · 0% no match · 0% unresolved or no map' })
    expect(zoneDimensions({ median: 0.8, p25: 0.7, p75: 0.9 }, 100, en, null)[1].missing).toBe('not evaluated (T46)')
  })

  it('the hover text of a cell gives its geology', async () => {
    const { cellLines } = await import('./model')
    const lines = cellLines(cell({ geology: { group: 'mare', source: 'Macrostrat', match: 1, partial: 0, no_match: 0, unresolved: 0, no_map: 0 } }), en)
    expect(lines[2]).toBe('Geology: 100% match · 0% partial · 0% no match · 0% unresolved or no map')
  })
})

describe('geology class of a cell on the map', () => {
  it('follows the majority of the samples, like the tiles', async () => {
    const { geologyClass } = await import('./model')
    const g = (match: number, partial: number, no_match: number) => cell({ geology: { group: 'mare', source: 'x', match, partial, no_match, unresolved: 0, no_map: 0 } })
    expect([g(0.6, 0, 0.4), g(0.3, 0.3, 0.4), g(0, 0, 0.8), g(0.1, 0.1, 0.2), cell({})].map(geologyClass)).toEqual([1, 2, 3, 4, 0])
  })
})

describe('Earth context of a zone (T47, E18)', () => {
  it('gives frozen ground and aridity as shares, labelled, and thermal cycling as waiting for its data', async () => {
    const { zoneDimensions } = await import('./model')
    const ctx = { frozen_e4: { met: 0.5, partial: 0.5, failed: 0, 'not covered': 0 }, magt_c_median: -6.2,
      aridity: { 'hyper-arid': 0, arid: 0.75, 'semi-arid': 0.25, 'dry sub-humid': 0, humid: 0, 'no data': 0 } }
    const rows = zoneDimensions({ median: 0.8, p25: 0.7, p75: 0.9 }, 100, en, null, ctx)
    expect(rows.map((r) => r.name)).toEqual(['Topography (slope)', 'Geology', 'Frozen ground (Earth context, model)',
      'Aridity (Earth context, model)', 'Surface thermal cycling'])
    expect(rows[2].text).toBe('E4 met 50% · partial 50% · not met 0% · not covered 0% · ground -6.2 °C')
    expect(rows[3].text).toBe('arid 75% · semi-arid 25%')
    expect(rows[4].missing).toMatch(/Earthdata/)
  })
})

describe('tile provenance for researchers (T52)', () => {
  const prov = {
    release: 'r-2', methodology_version: 'v3', tile: '10,20', last_changed_in: 'r-1', data_date: '2022-05-09',
    scales: {
      'glo90-90m': { computed_at: null, computed_at_note: 'not recorded (computed before T52)', code: 'c', inputs: [
        { item: 'Copernicus_DSM_COG_30_N10_00_E020_00_DEM/x.tif', last_modified: '2022-05-09T14:10:02.000Z' },
        { item: 'v200/2021/map/ESA_WorldCover_10m_2021_v200_N09E018_Map.tif', last_modified: '2022-10-01T00:00:00.000Z' }] },
      'glo30-40m': { computed_at: '2026-12-01T10:00:00Z', code: 'c', inputs: [
        { item: 'Copernicus_DSM_COG_10_N10_00_E020_00_DEM/x.tif', last_modified: '2022-05-09T14:10:02.000Z' }] },
    },
  }

  it('names each source with its file date, the computation date and the release where the tile last changed', () => {
    const l = provenanceLines(prov as never, en)
    expect(l.tile).toBe('Tile 10,20 (1°)')
    expect(l.sources).toEqual(['Copernicus DEM GLO-30: file dated 09/05/2022', 'Copernicus DEM GLO-90: file dated 09/05/2022',
      'ESA WorldCover: file dated 01/10/2022'])
    expect(l.computed).toBe('Computed on 01/12/2026; computation date not recorded for 1 scale (before automatic refresh)')
    expect(l.since).toBe('Unchanged since release r-1')
  })

  it('says it in French too', () => {
    const l = provenanceLines(prov as never, fr)
    expect(l.since).toBe('Inchangée depuis la version r-1')
    expect(l.sources[0]).toBe('Copernicus DEM GLO-30 : fichier daté du 09/05/2022')
  })
})

describe('pre-analysis of detected updates (T52b)', () => {
  it('says what an update would recompute, that it was not started, in both languages', () => {
    const s = structuredClone(status) as unknown as Status
    s.freshness = { ...s.freshness, refresher: true, impact: [
      { source: 'copernicus-dem-glo90', kind: 'earth_tiles', tiles_changed: ['10,20'], tiles_reassessed: 9, releases: [],
        cpu_hours_estimate: 0.0123, basis: 'calibration', recompute_started: false }] } as never
    expect(statusLines(s, en).impact).toBe('1 update detected, not recomputed: 9 tiles to reassess, about 0.01 CPU hours (estimate)')
    expect(statusLines(s, fr).impact).toBe('1 mise à jour détectée, non recalculée : 9 tuiles à réévaluer, environ 0,01 heure CPU (estimation)')
    expect(statusLines(status as unknown as Status, en).impact).toBeNull()
  })
})

describe('pre-analysis without a measured time', () => {
  it('says the CPU time was not measured instead of a made-up figure', () => {
    const s = structuredClone(status) as unknown as Status
    s.freshness = { ...s.freshness, impact: [{ source: 'obu-permafrost-2018', kind: 'earth_context', tiles_changed: [], tiles_reassessed: 0,
      releases: [], cpu_hours_estimate: null, basis: 'not measured', recompute_started: false }] } as never
    expect(statusLines(s, en).impact).toBe('1 update detected, not recomputed: 0 tile to reassess, CPU time not measured')
  })
})
