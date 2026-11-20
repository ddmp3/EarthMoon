import { describe, expect, it } from 'vitest'
import { deprecation, moonNote, paramInfo, parameterCatalog } from './api'
import { FR_PARAMS } from './content-fr'

describe('parameter catalog', () => {
  it('every parameter of the catalog has a French label and help text', () => {
    const missing = parameterCatalog.filter((p) => !FR_PARAMS[p.id]?.label || !FR_PARAMS[p.id]?.help).map((p) => p.id)
    expect(missing).toEqual([])
  })

  it('paramInfo returns the label in the requested language', () => {
    expect(paramInfo('slope_mean', 'en').label).toBe('Mean slope')
    expect(paramInfo('slope_mean', 'fr').label).toBe('Pente moyenne')
  })

  // The contract side is checked at compile time in api.ts (catalogCoversContract).
  it('every catalog parameter has a real label in both languages, not its raw id', () => {
    const raw = parameterCatalog.filter((p) => paramInfo(p.id, 'en').label === p.id || paramInfo(p.id, 'fr').label === p.id).map((p) => p.id)
    expect(raw).toEqual([])
  })

  it('flags the deprecated parameters with the reason and the replacement, in both languages (T45)', () => {
    for (const id of ['humidity', 'quake_count', 'volcano_distance'] as const) {
      expect(deprecation(id, 'en'), id).toMatch(/^Deprecated: /)
      expect(deprecation(id, 'fr'), id).toMatch(/^Déprécié : /)
    }
    expect(deprecation('slope_mean', 'en')).toBeNull()
  })

  it('the lunar note of earthquakes carries no unsourced figure (T13, REFERENCES section 8)', () => {
    for (const lang of ['en', 'fr'] as const) expect(moonNote('quake_count', lang) ?? '').not.toMatch(/\d/)
  })
})
