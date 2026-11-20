import { cleanup, render, screen, within } from '@testing-library/react'
import { afterEach, describe, expect, it } from 'vitest'
import coverage from '../test/fixtures/v3/coverage.json'
import method from '../test/fixtures/v3/method.json'
import scenarios from '../test/fixtures/v3/scenarios.json'
import status from '../test/fixtures/v3/status.json'
import zones from '../test/fixtures/v3/zones.json'
import type { Coverage, MethodSource, Scenario, Status, Zone } from './api'
import { CompareZones, DataMethod, StatusBar, ZoneCard } from './panels'
import { V3_TEXTS } from './text'

const t = V3_TEXTS.en
const zs = (zones as unknown as { zones: Zone[] }).zones
const scB = (scenarios as unknown as { scenarios: Scenario[] }).scenarios.find((s) => s.id === 'B') as Scenario
const cov = (coverage as unknown as Coverage).coverage

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

describe('comparison', () => {
  afterEach(cleanup)

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
