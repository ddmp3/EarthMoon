/**
 * Orthographic globe (T45c part 2), drawn on a 2D canvas without any 3D library (ADR-006 budget). A view is the
 * point at the centre of the disc (lat0, lon0). Longitudes are east, in degrees; `lon0Tex` is the east longitude at the
 * left edge of the equirectangular texture.
 */
export const TEXTURE_LON0 = { moon: -180, mars: 0 } as const

const D = Math.PI / 180

/** Screen position of a point on the unit disc (x right, y up), or null when it is on the far side. */
export function project(lat: number, lon: number, lat0: number, lon0: number): { x: number; y: number } | null {
  const p = lat * D, l = (lon - lon0) * D, p0 = lat0 * D
  const cosc = Math.sin(p0) * Math.sin(p) + Math.cos(p0) * Math.cos(p) * Math.cos(l)
  if (cosc < 0) return null
  return { x: Math.cos(p) * Math.sin(l), y: Math.cos(p0) * Math.sin(p) - Math.sin(p0) * Math.cos(p) * Math.cos(l) }
}

/** Point of the globe under a position of the unit disc (x right, y up), or null outside the disc. */
export function unproject(x: number, y: number, lat0: number, lon0: number): { lat: number; lon: number } | null {
  const rho2 = x * x + y * y
  if (rho2 > 1) return null
  const z = Math.sqrt(1 - rho2)
  const p0 = lat0 * D
  const lat = Math.asin(Math.max(-1, Math.min(1, z * Math.sin(p0) + y * Math.cos(p0)))) / D
  let lon = lon0 + Math.atan2(x, z * Math.cos(p0) - y * Math.sin(p0)) / D
  lon = ((((lon + 180) % 360) + 360) % 360) - 180
  return { lat, lon }
}

/** Zoom that fits points spread around a centre: 1 for half a globe or more, up to `max` for a small cluster. */
export function fitZoom(points: { lat: number; lon: number }[], lat0: number, lon0: number, max = 6): number {
  let spread = 0
  for (const p of points) {
    const c = Math.sin(lat0 * D) * Math.sin(p.lat * D) + Math.cos(lat0 * D) * Math.cos(p.lat * D) * Math.cos((p.lon - lon0) * D)
    spread = Math.max(spread, Math.acos(Math.max(-1, Math.min(1, c))))
  }
  if (spread >= Math.PI / 2 || spread === 0) return 1
  return Math.max(1, Math.min(max, 0.85 / Math.sin(spread)))
}

/** Texture column and row (0 to 1) of a point, for an equirectangular texture whose left edge is `lon0Tex`. */
export function texel(lat: number, lon: number, lon0Tex: number): { u: number; v: number } {
  return { u: ((((lon - lon0Tex) % 360) + 360) % 360) / 360, v: Math.min(0.999999, Math.max(0, (90 - lat) / 180)) }
}
