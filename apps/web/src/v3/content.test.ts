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

describe('French versions of the Mars release texts (T48)', () => {
  it('cover scenario D, its requirements, limits, steps and coverage classes', async () => {
    const { coverageMeaning, limitText, requirementText, scenarioText, stepText } = await import('./content')
    const ms = (await import('../test/fixtures/v3-mars/scenarios.json')).default as unknown as { scenarios: Scenario[] }
    const mm = (await import('../test/fixtures/v3-mars/method.json')).default as unknown as { processing: { step: string; what?: string }[] }
    const mc = (await import('../test/fixtures/v3-mars/coverage.json')).default as unknown as { scenarios: Record<string, Record<string, { classes: Record<string, { meaning: string }> }>> }
    for (const s of ms.scenarios) {
      expect(scenarioText(s.id, 'fr', { name: s.name as string, objective: s.objective as string }).name).not.toBe(s.name)
      for (const r of s.requirements) expect(requirementText(r.id, 'fr', r as { what: string; value: string }).what, r.id).not.toBe(r.what)
      for (const c of s.cannot_assess) expect(limitText(c, 'fr'), c).not.toBe(c)
      for (const why of Object.values(s.not_comparable)) expect(limitText(why, 'fr'), why).not.toBe(why)
    }
    for (const p of mm.processing) if (p.what) expect(stepText(p.step, 'fr', p.what), p.step).not.toBe(p.what)
    for (const target of Object.values(mc.scenarios.D)) {
      for (const [k, v] of Object.entries(target.classes)) expect(coverageMeaning(k, 'fr', v.meaning), k).not.toBe(v.meaning)
    }
  })
})
