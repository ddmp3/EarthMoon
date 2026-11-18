import { cleanup, render, screen, within } from '@testing-library/react'
import { afterEach, describe, expect, it } from 'vitest'
import type { SiteResult } from '../api'
import maunaKea from '../test/fixtures/mauna-kea-calibration.json'
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
