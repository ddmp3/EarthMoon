import { cleanup, render, screen, within } from '@testing-library/react'
import { afterEach, describe, expect, it } from 'vitest'
import type { SiteResult } from '../api'
import maunaKea from '../test/fixtures/mauna-kea-calibration.json'
import { Assessment } from './Stability'
import { SiteDetail } from './SiteDetail'

// Real API response (methodology v2, calibration mode, 17 Nov 2026): wind, specific humidity and
// precipitation are missing because the reanalysis cell is more than 1 km below the site.
const site = maunaKea as unknown as SiteResult

function renderSite() {
  render(
    <SiteDetail detail={null} detailError={null} limits={[]} manifest={null} rank={33} rankedTotal={36} site={site} sources={[]} visual={undefined} />,
  )
}

function row(label: string): HTMLElement {
  const header = screen.getByRole('rowheader', { name: new RegExp(`^${label}`) })
  return header.closest('tr') as HTMLElement
}

describe('SiteDetail scorecard', () => {
  afterEach(cleanup)

  it('shows a missing value as missing, never as a 0% match', () => {
    renderSite()
    const wind = row('Wind')
    expect(within(wind).getByText('No data')).toBeTruthy()
    expect(within(wind).queryByText('0%')).toBeNull()
    expect(wind.querySelector('.match-bar-missing')).not.toBeNull()
  })

  it('shows the match of a measured value', () => {
    renderSite()
    expect(within(row('Day-night swing')).getByText('100%')).toBeTruthy()
  })

  it('a measured value that does not match still shows 0%', () => {
    renderSite()
    expect(within(row('Mean air temperature')).getByText('0%')).toBeTruthy()
  })

  it('counts only evaluated criteria', () => {
    renderSite()
    expect(screen.getByText(/4\/7/)).toBeTruthy()
  })
})

describe('Assessment block (T45: confidence, coverage, requirements, explanation)', () => {
  afterEach(cleanup)

  it('shows confidence, coverage with the total range, and the requirements state', () => {
    render(<Assessment explanation={null} site={site} />)
    const block = screen.getByRole('region', { name: 'Assessment' })
    expect(within(block).getByText('Low confidence')).toBeTruthy()
    expect(within(block).getByText(/Data cover 60% of the criteria weight: .* between 10 and 50/)).toBeTruthy()
    expect(within(block).getByText('Hard requirements met')).toBeTruthy()
    expect(within(block).getByText(/Wind/)).toBeTruthy()
  })

  it('lists failed requirements and the explanation when the API gives them', () => {
    const failed = { ...site, requirements: 'failed' as const, failedRequirements: ['slope_mean' as const] }
    const explanation = {
      strengths: [{ param: 'lst_amplitude' as const, contribution: 12, loss: 0 }],
      weaknesses: [{ param: 't2m_mean' as const, contribution: 0, loss: 10 }],
      decisive: ['slope_mean' as const], missing: ['wind' as const], flagged: [], expertShare: 0.25,
    }
    render(<Assessment explanation={explanation} site={failed} />)
    const block = screen.getByRole('region', { name: 'Assessment' })
    expect(within(block).getByText('Hard requirements failed')).toBeTruthy()
    expect(within(block).getAllByText(/Mean slope/).length).toBeGreaterThan(0)
    expect(within(block).getByText(/Day-night swing/)).toBeTruthy()
    expect(within(block).getByText(/Mean air temperature/)).toBeTruthy()
    expect(within(block).getByText('25% of the total rests on expert judgements rather than measurements.')).toBeTruthy()
  })
})
