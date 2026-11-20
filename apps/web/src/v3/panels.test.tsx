import { cleanup, fireEvent, render, screen, within } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import coverage from '../test/fixtures/v3/coverage.json'
import method from '../test/fixtures/v3/method.json'
import scenarios from '../test/fixtures/v3/scenarios.json'
import status from '../test/fixtures/v3/status.json'
import zones from '../test/fixtures/v3/zones.json'
import type { Coverage, MethodSource, Scenario, Status, Zone } from './api'
import { CompareZones, CoverageLegend, DataMethod, LayerPanel, StatusBar, ZoneCard, ZoneList } from './panels'
import { V3_TEXTS } from './text'

const t = V3_TEXTS.en
const zs = (zones as unknown as { zones: Zone[] }).zones
const scB = (scenarios as unknown as { scenarios: Scenario[] }).scenarios.find((s) => s.id === 'B') as Scenario
const cov = (coverage as unknown as Coverage).coverage

describe('coverage legend', () => {
  afterEach(cleanup)

  it('labels every class in text with its land share, and switches the overlay off and on', () => {
    const onToggle = vi.fn()
    const onInfo = vi.fn()
    render(<CoverageLegend coverage={cov} on onInfo={onInfo} onToggle={onToggle} t={t} />)
    const list = screen.getByRole('list', { name: 'Coverage overlay' })
    const items = within(list).getAllByRole('listitem')
    expect(items.map((i) => i.querySelector('.legend-label')?.textContent)).toEqual(['Screened out', 'No data', 'Ground hidden', 'Partial', 'Low confidence', 'Evaluated'])
    expect(items[2].textContent).toMatch(/5% of land/)
    for (const i of items) expect(i.querySelector('svg rect:last-child')?.getAttribute('fill')).toMatch(/^url\(#pat-|^none$/)
    const toggle = screen.getByRole('switch', { name: 'Coverage overlay' })
    expect(toggle.getAttribute('aria-checked')).toBe('true')
    fireEvent.click(toggle)
    expect(onToggle).toHaveBeenCalledWith(false)
    fireEvent.click(screen.getByRole('button', { name: 'Data and method' }))
    expect(onInfo).toHaveBeenCalled()
  })
})

describe('layer panel', () => {
  afterEach(cleanup)

  it('offers topography and shows the later dimensions disabled with their reason', () => {
    render(<LayerPanel confidence onConfidence={() => undefined} t={t} />)
    const topo = screen.getByRole('radio', { name: /Topography/ }) as HTMLInputElement
    expect(topo.checked).toBe(true)
    const geo = screen.getByRole('radio', { name: /Geology/ }) as HTMLInputElement
    expect(geo.disabled).toBe(true)
    expect(screen.getByText('available after T46')).toBeTruthy()
    expect(screen.getByText('needs two non-redundant dimensions')).toBeTruthy()
  })
})

describe('zone card', () => {
  afterEach(cleanup)

  it('gives the value with its spread, the missing dimensions by name, requirements, confidence and the limits', () => {
    render(<ZoneCard cannotAssess={scB.cannot_assess} onClose={() => undefined} onProvenance={() => undefined} scenario={scB} status={status as unknown as Status} t={t} zone={zs[0]} />)
    const card = screen.getByRole('region', { name: /Zone 1/ })
    expect(within(card).getByRole('status').textContent).toMatch(/Not validated/)
    expect(within(card).getByText('0.88')).toBeTruthy()
    expect(within(card).getByText('0.87–0.91')).toBeTruthy()
    expect(within(card).getByText('not evaluated (T46)')).toBeTruthy()
    expect(within(card).getByText(/Apollo|LRV|climb/i)).toBeTruthy()
    expect(within(card).getByText('100% of cells high')).toBeTruthy()
    expect(within(card).getByText(/Monte Carlo not run/)).toBeTruthy()
    expect(within(card).getByText('Earth cannot reproduce')).toBeTruthy()
    for (const line of scB.cannot_assess) expect(within(card).getByText(line)).toBeTruthy()
  })
})

describe('zone list and comparison', () => {
  afterEach(cleanup)

  it('lists the zones in rank order and allows comparing 2 to 4 of them only', () => {
    const onOpen = vi.fn()
    const onCompare = vi.fn()
    render(<ZoneList onCompare={onCompare} onOpen={onOpen} t={t} total={zs.length} zones={zs} />)
    const compare = screen.getByRole('button', { name: 'Compare' }) as HTMLButtonElement
    expect(compare.disabled).toBe(true)
    const boxes = screen.getAllByRole('checkbox') as HTMLInputElement[]
    fireEvent.click(boxes[0])
    expect(compare.disabled).toBe(true)
    fireEvent.click(boxes[1])
    expect(compare.disabled).toBe(false)
    fireEvent.click(boxes[2])
    fireEvent.click(boxes[3])
    expect(boxes[4].disabled).toBe(true)
    fireEvent.click(compare)
    expect(onCompare).toHaveBeenCalledWith(zs.slice(0, 4).map((z) => z.id))
    fireEvent.click(screen.getByRole('button', { name: /^1\./ }))
    expect(onOpen).toHaveBeenCalledWith(zs[0].id)
  })

  it('draws one strip per zone with its median and interquartile range', () => {
    render(<CompareZones onClose={() => undefined} t={t} zones={zs.slice(0, 3)} />)
    const table = screen.getByRole('table', { name: 'Zone comparison' })
    expect(within(table).getAllByRole('columnheader')).toHaveLength(4)
    const strips = table.querySelectorAll('svg[data-strip]')
    expect(strips).toHaveLength(3)
    expect(strips[0].getAttribute('aria-label')).toMatch(/median 0\.88, IQR 0\.87–0\.91/)
    expect(within(table).getAllByText('not evaluated (T46)')).toHaveLength(3)
  })
})

describe('data and method panel', () => {
  afterEach(cleanup)

  it('says what we cover, lists every source with its status, the processing chain, and the limits', () => {
    const m = method as unknown as { sources: MethodSource[]; processing: Record<string, unknown>[] }
    render(<DataMethod cannotAssess={scB.cannot_assess} coverage={cov} onClose={() => undefined} processing={m.processing} sources={m.sources} t={t} />)
    const dialog = screen.getByRole('dialog', { name: 'Data and method' })
    for (const h of ['What we cover', 'Sources used', 'How we processed it', 'What it cannot say']) {
      expect(within(dialog).getByRole('heading', { name: h })).toBeTruthy()
    }
    expect(within(dialog).getAllByRole('listitem', { name: /source/ })).toHaveLength(m.sources.length)
    expect(within(dialog).getAllByText(/verified 2026-11-1\d/).length).toBeGreaterThan(0)
    expect(within(dialog).getByText(/partly verified/)).toBeTruthy()
    expect(within(dialog).getAllByRole('listitem', { name: /step/ })).toHaveLength(m.processing.length)
  })
})

describe('status bar', () => {
  afterEach(cleanup)

  it('shows validity and freshness in text', () => {
    render(<StatusBar status={status as unknown as Status} t={t} />)
    const bar = screen.getByRole('status')
    expect(bar.textContent).toMatch(/Not validated/)
    expect(bar.textContent).toMatch(/Checks not passed: positive controls \(none exist\), masks, self-consistency/)
    expect(bar.textContent).toMatch(/no automatic check yet/)
  })
})
