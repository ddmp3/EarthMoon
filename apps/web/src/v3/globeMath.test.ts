import { describe, expect, it } from 'vitest'
import { TEXTURE_LON0, fitZoom, project, texel, unproject } from './globeMath'

describe('orthographic globe (T45c part 2)', () => {
  it('projects a visible point and reads it back', () => {
    for (const [lat0, lon0] of [[0, 0], [-85, 130], [45, -60]]) {
      for (const [lat, lon] of [[lat0, lon0], [lat0 + 10 > 90 ? lat0 - 10 : lat0 + 10, lon0 + 15]]) {
        const p = project(lat, lon, lat0, lon0)
        expect(p).not.toBeNull()
        const back = unproject(p!.x, p!.y, lat0, lon0)!
        expect(back.lat).toBeCloseTo(lat, 6)
        expect(((back.lon - lon + 540) % 360) - 180).toBeCloseTo(0, 6)
      }
    }
  })

  it('hides the far side and stays outside the disc', () => {
    expect(project(0, 180, 0, 0)).toBeNull()
    expect(project(0, 0, 0, 0)).toEqual({ x: 0, y: 0 })
    expect(unproject(0.8, 0.8, 0, 0)).toBeNull()
  })

  it('zooms on a polar cluster and not on points spread over the globe', () => {
    const polar = [{ lat: -86, lon: 0 }, { lat: -87, lon: 120 }, { lat: -89.5, lon: 240 }]
    expect(fitZoom(polar, -90, 0)).toBeGreaterThan(5)
    expect(fitZoom([{ lat: 40, lon: 0 }, { lat: -40, lon: 120 }], 0, 0)).toBe(1)
  })

  it('maps longitudes onto each texture convention', () => {
    expect(texel(0, -180, TEXTURE_LON0.moon)).toEqual({ u: 0, v: 0.5 })
    expect(texel(90, 0, TEXTURE_LON0.mars)).toEqual({ u: 0, v: 0 })
    expect(texel(-30, -90, TEXTURE_LON0.mars).u).toBeCloseTo(0.75, 9)
  })
})
