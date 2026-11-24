import { cleanup, fireEvent, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { Home } from './Home'

const cards = () => screen.getAllByRole('button').filter((b) => b.className.includes('mission-card'))

describe('Home of the Moon', () => {
  afterEach(cleanup)

  it('offers the four lunar missions, in order, and no Mars card (Mars is the other mode of the site)', () => {
    const onPick = vi.fn()
    render(<Home body="moon" figures={null} onPick={onPick} onPickMars={vi.fn()} />)
    expect(cards()).toHaveLength(4)
    fireEvent.click(cards()[0])
    fireEvent.click(cards()[3])
    expect(onPick.mock.calls.map((c) => c[0])).toEqual(['robotics', 'custom'])
    expect(screen.getByRole('heading', { level: 1 }).textContent).toBe('Find the Moon on Earth.')
  })

  it('shows the figures it is given, read from the release, and none before it is loaded', () => {
    const { unmount } = render(<Home body="moon" figures={[{ value: '6.3 M', label: 'Earth cells of 5 km assessed' }]} onPick={vi.fn()} onPickMars={vi.fn()} />)
    expect(screen.getByText('6.3 M')).toBeTruthy()
    unmount()
    const { container } = render(<Home body="moon" figures={null} onPick={vi.fn()} onPickMars={vi.fn()} />)
    expect(container.querySelector('.figures')).toBeNull()
  })
})

describe('Home of Mars (T45c)', () => {
  afterEach(cleanup)

  it('has its own photo, title and one card per Martian terrain', () => {
    const { container } = render(<Home body="mars" figures={null} onPick={vi.fn()} onPickMars={vi.fn()} />)
    expect(screen.getByRole('heading', { level: 1 }).textContent).toBe('Find Mars on Earth.')
    expect(container.querySelector('.hero-image')?.getAttribute('src')).toMatch(/mars-hero\.jpg$/)
    expect(cards().map((c) => c.querySelector('strong')?.textContent)).toEqual(
      ['Ice-rich mid-latitudes', 'North polar terrain', 'South polar terrain', 'Volcanic plains'])
  })

  it('opens the Mars mission on the terrain picked; the volcanic plains wait for their data', () => {
    const onPickMars = vi.fn()
    render(<Home body="mars" figures={null} onPick={vi.fn()} onPickMars={onPickMars} />)
    fireEvent.click(cards()[1])
    expect(onPickMars).toHaveBeenCalledWith('mars-north-polar')
    expect((cards()[3] as HTMLButtonElement).disabled).toBe(true)
  })
})
