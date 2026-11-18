import { cleanup, render } from '@testing-library/react'
import { afterEach, describe, expect, it } from 'vitest'
import type { SiteResult } from '../api'
import maunaKea from '../test/fixtures/mauna-kea-calibration.json'
import { Radar } from './Radar'

// 7 criteria: 4 measured, 3 missing (wind, specific_humidity, precipitation).
const site = maunaKea as unknown as SiteResult

describe('Radar', () => {
  afterEach(cleanup)

  it('draws a point only for measured criteria', () => {
    const { container } = render(<Radar site={site} />)
    expect(container.querySelectorAll('circle.radar-dot')).toHaveLength(4)
    expect(container.querySelector('polygon.radar-shape')?.getAttribute('points')?.split(' ')).toHaveLength(4)
  })

  it('marks the axes without data instead of placing them at zero', () => {
    const { container } = render(<Radar site={site} />)
    expect(container.querySelectorAll('line.radar-axis-missing')).toHaveLength(3)
    expect(container.querySelectorAll('text.radar-label-missing')).toHaveLength(3)
  })

  it('a complete site keeps one point per axis', () => {
    const full = { ...site, criteria: site.criteria.map((c) => ({ ...c, value: 1, score: 0.5, verdict: 'partial' as const })) }
    const { container } = render(<Radar site={full} />)
    expect(container.querySelectorAll('circle.radar-dot')).toHaveLength(7)
    expect(container.querySelectorAll('line.radar-axis-missing')).toHaveLength(0)
  })
})
