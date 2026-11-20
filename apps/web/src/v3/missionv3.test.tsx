import { cleanup, fireEvent, render, screen, within } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import coverage from '../test/fixtures/v3/coverage.json'
import scenarios from '../test/fixtures/v3/scenarios.json'
import status from '../test/fixtures/v3/status.json'
import type { CellProps, Coverage, Scenario, Status } from './api'
import { MapLegend, RankTabs, SiteV3Chip, SiteV3Section, V3StatusLine, ZoneRows } from './MissionV3'
import type { SiteV3, V3State } from './useV3'

const scB = (scenarios as unknown as { scenarios: Scenario[] }).scenarios.find((s) => s.id === 'B') as Scenario
const cell = (over: Partial<CellProps> = {}): CellProps => ({
  id: '1', lat: -23, lon: -68, typicality: { median: 0.66, p25: 0.52, p75: 0.82 }, windows: { valid: 24, total: 24 },
  coverage: 'evaluated', confidence: 'high', masked_share: 0, requirements: {}, ...over,
})
const site = (values: Record<string, CellProps> | null): SiteV3 => ({ id: 'atacama', cell: values ? '14415389' : null, values })

describe('v3 mark on a ranked site', () => {
  afterEach(cleanup)

  it('shows the typicality of the cell for the chosen environment', () => {
    render(<SiteV3Chip env="moon-psr" site={site({ 'moon-psr': cell() })} />)
    expect(screen.getByText('v3 0.66')).toBeTruthy()
  })

  it('never shows a value for a masked, unassessed or missing cell', () => {
    render(<SiteV3Chip env="moon-psr" site={site({ 'moon-psr': cell({ coverage: 'ground_hidden' }) })} />)
    expect(screen.queryByText(/0\.66/)).toBeNull()
    cleanup()
    render(<SiteV3Chip env="moon-psr" site={site(null)} />)
    expect(screen.getByText('v3 —').getAttribute('title')).toMatch(/Not assessed/)
  })
})

describe('v3 section of the site card', () => {
  afterEach(cleanup)

  it('gives one row per environment of the scenario, with spread, windows, coverage and confidence', () => {
    const values = Object.fromEntries(scB.assessed_targets.map((t) => [t, cell()]))
    render(<SiteV3Section onMethod={() => undefined} release="r-98f6eee4" scenario={scB} site={site(values)} />)
    const section = screen.getByRole('region', { name: 'Our v3 data at this place' })
    expect(within(section).getAllByRole('row')).toHaveLength(scB.assessed_targets.length + 1)
    expect(within(section).getAllByText('0.52–0.82')).toHaveLength(scB.assessed_targets.length)
    expect(within(section).getByText(/r-98f6eee4/)).toBeTruthy()
  })

  it('says when the place was not assessed', () => {
    render(<SiteV3Section onMethod={() => undefined} release="r-1" scenario={scB} site={site(null)} />)
    expect(screen.getByText(/Not assessed at this place/)).toBeTruthy()
  })
})

describe('tabs, zone rows and status line', () => {
  afterEach(cleanup)

  it('tabs show their counts and switch', () => {
    const onTab = vi.fn()
    render(<RankTabs counts={{ sites: 36, zones: 9961 }} onTab={onTab} tab="sites" />)
    fireEvent.click(screen.getByRole('tab', { name: /Discovered zones · 9,961/ }))
    expect(onTab).toHaveBeenCalledWith('zones')
    expect(screen.getByRole('tab', { name: /Known sites · 36/ }).getAttribute('aria-selected')).toBe('true')
  })

  it('zone rows open a zone and allow picking at most 4 for comparison', () => {
    const items = Array.from({ length: 5 }, (_, i) => ({ id: `z${i}`, lat: i, lon: i, value: 0.9 - i / 10, sub: '3 cells' }))
    const onSelect = vi.fn()
    const onPick = vi.fn()
    render(<ZoneRows items={items} onPick={onPick} onSelect={onSelect} picked={['z0', 'z1', 'z2', 'z3']} selectedId={null} />)
    fireEvent.click(screen.getAllByRole('button')[1])
    expect(onSelect).toHaveBeenCalledWith('z1')
    expect((screen.getAllByRole('checkbox')[4] as HTMLInputElement).disabled).toBe(true)
  })

  it('the status line says not validated and why', () => {
    render(<V3StatusLine v={{ status: status as unknown as Status } as unknown as V3State} />)
    expect(screen.getByRole('status').textContent).toMatch(/Not validated.*Checks not passed: positive controls \(none exist\), masks, self-consistency/)
  })
})

describe('map legend', () => {
  afterEach(cleanup)

  it('gives the scale, every coverage class with its land share, and every layer with the task it waits for', () => {
    render(<MapLegend coverage={(coverage as unknown as Coverage).coverage} overlay />)
    const classes = screen.getByRole('list', { name: 'Coverage overlay' })
    expect(within(classes).getAllByRole('listitem').map((i) => i.querySelector('.legend-label')?.textContent))
      .toEqual(['Screened out', 'No data', 'Ground hidden', 'Partial', 'Low confidence', 'Evaluated'])
    expect(within(classes).getAllByRole('listitem')[2].textContent).toMatch(/5%/)
    const layers = screen.getByRole('list', { name: 'Layers' })
    expect(layers.textContent).toMatch(/Geology · available after T46/)
    expect(layers.textContent).toMatch(/Multidimensional · needs two non-redundant dimensions/)
  })
})
