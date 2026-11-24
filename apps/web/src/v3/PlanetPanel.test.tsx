import { cleanup, fireEvent, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { PlanetPanel } from './PlanetPanel'
import { V3_TEXTS } from './text'

vi.mock('./PlanetGlobe', () => ({
  PlanetGlobe: ({ onPick, highlight }: { onPick: (lat: number, lon: number) => void; highlight: unknown[] }) => (
    <button data-highlight={highlight.length} onClick={() => onPick(-89.5, 130)} type="button">globe</button>
  ),
}))

const load = {
  analogTarget: vi.fn(async () => ({ release: 'r', env: 'moon-psr', body: 'moon', n_windows: 3, rule: '', sources: {},
    windows: { lat: [-89.6, -88, -86], lon: [129.8, 10, 200], slope: [10, 2, 10.2], name: ['Shackleton', 'x', 'Haworth'] } })),
  analogZone: vi.fn(async () => ({ release: 'r', env: 'moon-psr', percentile: 0.505, n_windows: 3, rule: '', sources: {},
    zone: { id: 'B.moon-psr.t0.5.m3.1', slope_median: 10.1 },
    windows: [{ lat: -89.6, lon: 129.8, slope: 10, name: 'Shackleton' }, { lat: -86, lon: 200, slope: 10.2, name: 'Haworth' }] })),
  analogPoint: vi.fn(async () => ({ release: 'r', env: 'moon-psr', percentile: 0.5, rule: '',
    window: { lat: -89.6, lon: 129.8, slope: 10, name: 'Shackleton' },
    zones: [{ id: 'B.moon-psr.t0.5.m3.1', lat: 11, lon: 20, typicality: 0.89, slope_median: 10.1, place: { en: 'Itabirito, Minas Gerais, Brazil', fr: 'Itabirito, Minas Gerais, Brésil' } }] })),
}

describe('planet panel beside the Earth map (T45c part 2)', () => {
  afterEach(cleanup)

  it('a selected Earth zone lights the windows of the same slope and says how many', async () => {
    render(<PlanetPanel body="moon" env="moon-psr" lang="en" load={load} onZone={vi.fn()} release="r" scenario="B"
      t={V3_TEXTS.en} zoneId="B.moon-psr.t0.5.m3.1" zoneName="Itabirito, Minas Gerais, Brazil" />)
    expect(await screen.findByText(/2 windows have the same slope as Itabirito, Minas Gerais, Brazil \(median 10.1°, percentile 51/)).toBeTruthy()
    expect(screen.getByRole('button', { name: 'globe' }).getAttribute('data-highlight')).toBe('2')
  })

  it('a point on the globe lists the Earth zones of the same slope by name, and picking one selects it', async () => {
    const onZone = vi.fn()
    render(<PlanetPanel body="moon" env="moon-psr" lang="fr" load={load} onZone={onZone} release="r" scenario="B"
      t={V3_TEXTS.fr} zoneId={null} zoneName={null} />)
    fireEvent.click(screen.getByRole('button', { name: 'globe' }))
    const zone = await screen.findByRole('button', { name: /Itabirito, Minas Gerais, Brésil/ })
    expect(screen.getByText(/Shackleton : pente 10,0°, centile 50 de la cible/)).toBeTruthy()
    fireEvent.click(zone)
    expect(onZone).toHaveBeenCalledWith('B.moon-psr.t0.5.m3.1')
  })

  it('shows nothing when the release has no planetary windows for the target', async () => {
    const none = { ...load, analogTarget: vi.fn(async () => { throw new Error('404') }) }
    const { container } = render(<PlanetPanel body="moon" env="moon-pits" lang="en" load={none} onZone={vi.fn()} release="r"
      scenario="A" t={V3_TEXTS.en} zoneId={null} zoneName={null} />)
    await new Promise((r) => setTimeout(r, 0))
    expect(container.querySelector('.planet-panel')).toBeNull()
  })
})
