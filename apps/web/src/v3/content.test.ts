import { describe, expect, it } from 'vitest'
import coverage from '../test/fixtures/v3/coverage.json'
import method from '../test/fixtures/v3/method.json'
import scenarios from '../test/fixtures/v3/scenarios.json'
import type { Scenario } from './api'
import { TRANSLATED } from './content'

// The fixture release is written by the real exporter from the repository's scenarios: same texts as a real release.
const sc = (scenarios as unknown as { scenarios: Scenario[] }).scenarios

describe('French versions of the texts served by the API', () => {
  it('cover every scenario, requirement and limit of the release', () => {
    for (const s of sc) {
      expect(TRANSLATED.SCENARIO_FR[s.id], s.id).toBeTruthy()
      for (const r of s.requirements) expect(TRANSLATED.REQUIREMENT_FR[r.id], r.id).toBeTruthy()
      for (const c of s.cannot_assess) expect(TRANSLATED.LIMIT_FR[c], c).toBeTruthy()
    }
  })

  it('cover every processing step and coverage class', () => {
    for (const p of (method as unknown as { processing: { step: string }[] }).processing) expect(TRANSLATED.STEP_FR[p.step], p.step).toBeTruthy()
    for (const k of Object.keys((coverage as unknown as { coverage: { classes: Record<string, unknown> } }).coverage.classes)) {
      expect(TRANSLATED.COVERAGE_FR[k], k).toBeTruthy()
    }
  })
})
