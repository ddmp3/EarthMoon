import { cleanup, fireEvent, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { parameterCatalog } from '../api'
import { Home } from './Home'

describe('Home', () => {
  afterEach(cleanup)

  it('offers the four missions, in order', () => {
    const onPick = vi.fn()
    render(<Home onPick={onPick} siteCount={37} />)
    const cards = screen.getAllByRole('button').filter((b) => b.className.includes('mission-card'))
    expect(cards).toHaveLength(4)
    fireEvent.click(cards[0])
    fireEvent.click(cards[3])
    expect(onPick.mock.calls.map((c) => c[0])).toEqual(['robotics', 'custom'])
  })

  it('shows the number of sites it was given', () => {
    render(<Home onPick={() => {}} siteCount={37} />)
    expect(screen.getByText('37')).toBeTruthy()
  })

  it('counts the parameters from the catalog, not a hard-coded figure', () => {
    render(<Home onPick={() => {}} siteCount={37} />)
    expect(screen.getByText(String(parameterCatalog.length))).toBeTruthy()
  })

  it('offers the discovery map when the page provides it', () => {
    const onDiscover = vi.fn()
    render(<Home onDiscover={onDiscover} onPick={() => {}} siteCount={37} />)
    fireEvent.click(screen.getByRole('button', { name: /Discovery map/ }))
    expect(onDiscover).toHaveBeenCalled()
  })
})
