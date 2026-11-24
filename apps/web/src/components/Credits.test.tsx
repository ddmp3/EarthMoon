import { describe, expect, it } from 'vitest'
import { TEXTS } from '../i18n'
import { pageCredits } from '../credits'

const en = TEXTS.en

describe('credits of the images of the current page (T45c)', () => {
  it('the Moon home credits its banner and its four mission photos, nothing of Mars', () => {
    const c = pageCredits(en, 'moon', null, null)
    expect(c).toHaveLength(5)
    expect(c[0]).toMatch(/Artemis II/)
    expect(c.join(' ')).not.toMatch(/PIA13163|Mars/)
  })

  it('the Mars home credits the north polar cap and its terrain photos', () => {
    const c = pageCredits(en, 'mars', null, null)
    expect(c[0]).toMatch(/PIA13163/)
    expect(c.join(' ')).toMatch(/PIA00300/)
    expect(c.join(' ')).not.toMatch(/Artemis/)
  })

  it('a Mars mission credits its own terrain photo, the map, MOLA and the globe, never the lunar photos', () => {
    const c = pageCredits(en, 'mars', 'mars', 'mars-south-polar').join(' ')
    expect(c).toMatch(/PIA02393/)
    expect(c).toMatch(/MOLA/)
    expect(c).not.toMatch(/Apollo|Artemis|Sentinel-2/)
  })

  it('a lunar mission credits its banner, the site imagery and the lunar globe', () => {
    const c = pageCredits(en, 'moon', 'robotics', 'moon-psr').join(' ')
    expect(c).toMatch(/Apollo 15/)
    expect(c).toMatch(/Sentinel-2/)
    expect(c).toMatch(/LROC/)
  })
})
