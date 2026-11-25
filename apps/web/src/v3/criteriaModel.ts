import type { CriteriaPreset, Criterion } from './api'

/** The presets of a mission first: the precalibrated use of the mission, then the other uses of the same body. */
export function orderPresets(presets: CriteriaPreset[], mission: string, terrain?: string): CriteriaPreset[] {
  const rank = (p: CriteriaPreset) => (terrain && p.terrain === terrain ? 0 : p.mission === mission ? 1 : 2)
  return [...presets].sort((a, b) => rank(a) - rank(b))
}

/** Why a known site was not recovered: the required criteria that failed at its best point. */
export function failedRequired(rule: Criterion[], states: string[]): number[] {
  return rule.flatMap((c, i) => (c.role === 'required' && states[i] === 'failed' ? [i] : []))
}

/** What is sent to the service: the condition and the role only (why and source stay with the preset). */
export const strip = (c: Criterion): Criterion =>
  c.expression !== undefined ? { expression: c.expression, role: c.role } : { variable: c.variable, op: c.op, value: c.value, role: c.role }

export const sameRule = (a: Criterion[], b: Criterion[]) => JSON.stringify(a.map(strip)) === JSON.stringify(b.map(strip))
