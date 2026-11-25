import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { afterEach, describe, expect, it } from 'vitest'
import type { CriteriaCatalogue, CriteriaPreset, CriteriaRun, Criterion } from './api'
import { CriteriaPanel } from './Criteria'
import { failedRequired, orderPresets } from './criteriaModel'
import { CRITERIA_TEXTS } from './criteriaText'

const b = (en: string, fr = en) => ({ en, fr })
const preset = (id: string, mission: string, terrain: string | null, criteria: Criterion[]): CriteriaPreset => ({
  id, body: 'mars', mission, terrain, targets: [terrain ?? 'mars-volcanic-plains'], title: b(`Title ${id}`), use: b(`Use ${id}`),
  imitates: b('the plains'), criteria, known_sites: { features: [{ body: 'mars', feature: 'basalt' }] },
})
const volcanic: Criterion[] = [
  { variable: 'volcanic_rock', op: '>', value: 0, role: 'required', why: b('The feature first.'), source: 'R66', source_text: b('catalogue') },
  { variable: 'aridity', op: '<', value: 0.2, role: 'preferred', why: b('Dry ground.'), source: 'R65' },
]
const ice: Criterion[] = [{ variable: 'permafrost', op: '>=', value: 0.5, role: 'required', why: b('Frozen ground.'), source: 'R32' }]
const catalogue: CriteriaCatalogue = {
  release: 'r-1', body: 'mars', method: b('Required criteria are gates.'),
  variables: [
    { id: 'volcanic_rock', label: b('Volcanic rock mapped'), unit: 'share', range: [0, 1], source: b('Macrostrat'), scale: b('5 km'), help: b('any volcanic rock') },
    { id: 'aridity', label: b('Aridity index'), unit: 'index', range: [0, 5], source: b('Global AI'), scale: b('1 km'), help: b('below 0.2 arid') },
    { id: 'permafrost', label: b('Permafrost probability'), unit: 'probability', range: [0, 1], source: b('Obu'), scale: b('1 km'), help: b('north only') },
  ],
  presets: [preset('mars-ground-ice', 'mars', 'mars-ice-rich-midlatitudes', ice), preset('mars-volcanic-geology', 'mars', 'mars-volcanic-plains', volcanic)],
}
const result = (custom: boolean, criteria: Criterion[]): CriteriaRun => ({
  release: 'r-1', body: 'mars', preset: 'mars-volcanic-geology', custom, label: custom ? 'custom, not validated' : 'preset',
  rule: { criteria: criteria.map((c) => ({ ...c, text: c.expression ?? `${c.variable} ${c.op} ${c.value}` })) },
  counts: { candidate: 1200, 'to check': 30, excluded: 5000 }, assessed: 6230, land_share: 0.1926, area_km2: 30048,
  cells: [{ id: '1', lat: 19.4, lon: -155.3, states: ['met', 'met'], preferred_met: 1, confidence: 'high' }],
  known_sites: { features: [{ body: 'mars', feature: 'basalt' }], recovered: 1, with_data: 2, unknown: 1, false_alarms: 0, negatives: 18,
    source: 'catalogue R66', chapters: [
      { chapter: 14, name: 'Kilauea', state: 'candidate', sites: [{ name: 'Kilauea', chapter: 14, chapter_name: 'Kilauea', lat: 19.4, lon: -155.3, cell: '1', state: 'candidate', states: ['met', 'met'] }] },
      { chapter: 18, name: 'Mt. Etna', state: 'excluded', sites: [{ name: 'Mt. Etna', chapter: 18, chapter_name: 'Mt. Etna', lat: 37.7, lon: 15, cell: '2', state: 'excluded', states: ['failed', 'met'] }] },
      { chapter: 15, name: 'Lonar Crater', state: 'to check', sites: [{ name: 'Lonar Crater', chapter: 15, chapter_name: 'Lonar Crater', lat: 19.9, lon: 76.5, cell: null, state: 'to check', states: ['unknown', 'unknown'] }] },
    ] },
})

describe('criteria panel (T54)', () => {
  afterEach(cleanup)

  it('opens on the preset of the terrain, shows each criterion with why and source, and runs it at once', async () => {
    const sent: { preset?: string; criteria?: Criterion[] }[] = []
    render(<CriteriaPanel load={async () => catalogue} mission="mars" release="r-1"
      run={async (body) => { sent.push(body); return result(false, body.criteria ?? []) }} terrain="mars-volcanic-plains" />)
    await screen.findByText('Selection criteria')
    expect((screen.getByLabelText('Use') as HTMLSelectElement).value).toBe('mars-volcanic-geology')
    expect(screen.getByText(/The feature first\./).textContent).toMatch(/Source : catalogue/)
    await waitFor(() => expect(sent).toHaveLength(1))
    expect(sent[0]).toEqual({ preset: 'mars-volcanic-geology', criteria: volcanic.map(({ variable, op, value, role }) => ({ variable, op, value, role })), limit: 200 })
    expect(await screen.findByText('Preset')).toBeTruthy()
    expect(screen.getByText(/1 of 2 sites with data recovered/)).toBeTruthy()
    expect(screen.getByText(/0 of 18 random places pass/)).toBeTruthy()
    expect(screen.getByText('volcanic_rock > 0')).toBeTruthy()            // why Etna was not recovered
  })

  it('an edited threshold or an added equation is sent as is, and the result says custom, not validated', async () => {
    const sent: { criteria?: Criterion[] }[] = []
    render(<CriteriaPanel load={async () => catalogue} mission="mars" release="r-1"
      run={async (body) => { sent.push(body); return result(sent.length > 1, body.criteria ?? []) }} terrain="mars-volcanic-plains" />)
    await waitFor(() => expect(sent).toHaveLength(1))
    fireEvent.change(document.getElementById('criterion-value-1') as HTMLInputElement, { target: { value: '0.05' } })
    fireEvent.change(document.getElementById('criteria-equation') as HTMLInputElement, { target: { value: 'volcanic_rock > 0.5 or aridity < 0.03' } })
    fireEvent.click(document.getElementById('criteria-add-equation') as HTMLButtonElement)
    fireEvent.click(document.getElementById('criteria-run') as HTMLButtonElement)
    await waitFor(() => expect(sent).toHaveLength(2))
    expect(sent[1].criteria?.[1]).toEqual({ variable: 'aridity', op: '<', value: 0.05, role: 'preferred' })
    expect(sent[1].criteria?.[2]).toEqual({ expression: 'volcanic_rock > 0.5 or aridity < 0.03', role: 'required' })
    expect(await screen.findByText('Custom, not validated')).toBeTruthy()
  })

  it('a refused rule shows the reason from the server', async () => {
    let n = 0
    render(<CriteriaPanel load={async () => catalogue} mission="mars" release="r-1"
      run={async (body) => { n += 1; if (n > 1) throw new Error("unknown variable 'foo'"); return result(false, body.criteria ?? []) }} terrain="mars-volcanic-plains" />)
    await waitFor(() => expect(n).toBe(1))
    fireEvent.click(document.getElementById('criteria-run') as HTMLButtonElement)
    expect((await screen.findByRole('alert')).textContent).toMatch(/unknown variable 'foo'/)
  })
})

describe('criteria helpers', () => {
  it('a mission opens on its terrain preset first, then its own presets', () => {
    expect(orderPresets(catalogue.presets, 'mars', 'mars-volcanic-plains').map((p) => p.id)).toEqual(['mars-volcanic-geology', 'mars-ground-ice'])
  })

  it('a site was not recovered because of its failed required criteria only', () => {
    expect(failedRequired(volcanic, ['failed', 'failed'])).toEqual([0])
  })

  it('French mirrors every English text', () => {
    expect(Object.keys(CRITERIA_TEXTS.fr).sort()).toEqual(Object.keys(CRITERIA_TEXTS.en).sort())
  })
})
