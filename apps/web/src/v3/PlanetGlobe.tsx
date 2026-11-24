import { useCallback, useEffect, useRef, useState } from 'react'
import { TEXTURE_LON0, project, texel, unproject } from './globeMath'

export type GlobePoint = { lat: number; lon: number; name: string }

/**
 * The Moon or Mars in 3D beside the Earth map (T45c part 2): an orthographic globe drawn on a 2D canvas from the
 * planet texture, with no 3D library (ADR-006 JavaScript budget). Drag to turn, buttons to zoom, click to pick a point.
 * The target's windows are faint dots; the windows of the same slope as the selected Earth zone are bright.
 */
export function PlanetGlobe({ body, windows, highlight, focus, onPick, label, noWebgl, zoomIn, zoomOut }: {
  body: 'moon' | 'mars'
  windows: GlobePoint[]
  highlight: GlobePoint[]
  focus: { lat: number; lon: number } | null
  onPick: (lat: number, lon: number) => void
  label: string
  noWebgl: string
  zoomIn: string
  zoomOut: string
}) {
  const canvas = useRef<HTMLCanvasElement | null>(null)
  const tex = useRef<{ data: Uint8ClampedArray; w: number; h: number } | null>(null)
  const view = useRef({ lat0: 0, lon0: 0, zoom: 1 })
  const drag = useRef<{ x: number; y: number; lat0: number; lon0: number; moved: boolean } | null>(null)
  const frame = useRef(0)
  const points = useRef<{ all: GlobePoint[]; hi: GlobePoint[] }>({ all: [], hi: [] })
  const [failed, setFailed] = useState(false)
  const lon0Tex = TEXTURE_LON0[body]
  const accent = body === 'mars' ? '#7fd4ff' : '#ffc457'

  const draw = useCallback(() => {
    cancelAnimationFrame(frame.current)
    frame.current = requestAnimationFrame(() => {
      const c = canvas.current
      const ctx = c?.getContext('2d')
      if (!c || !ctx) return
      const W = c.width
      const { lat0, lon0, zoom } = view.current
      const R = (W / 2) * 0.94 * zoom
      const img = ctx.createImageData(W, W)
      const t = tex.current
      for (let py = 0; py < W; py++) {
        const y = (W / 2 - py - 0.5) / R
        for (let px = 0; px < W; px++) {
          const x = (px + 0.5 - W / 2) / R
          const g = unproject(x, y, lat0, lon0)
          if (!g) continue
          const shade = 0.45 + 0.55 * Math.sqrt(Math.max(0, 1 - x * x - y * y))
          const o = (py * W + px) * 4
          if (t) {
            const { u, v } = texel(g.lat, g.lon, lon0Tex)
            const k = (Math.floor(v * t.h) * t.w + Math.floor(u * t.w)) * 4
            img.data[o] = t.data[k] * shade
            img.data[o + 1] = t.data[k + 1] * shade
            img.data[o + 2] = t.data[k + 2] * shade
          } else {
            img.data[o] = 90 * shade
            img.data[o + 1] = 90 * shade
            img.data[o + 2] = 90 * shade
          }
          img.data[o + 3] = 255
        }
      }
      ctx.putImageData(img, 0, 0)
      const dot = (p: GlobePoint, r: number, fill: string, stroke?: string) => {
        const s = project(p.lat, p.lon, lat0, lon0)
        if (!s) return
        ctx.beginPath()
        ctx.arc(W / 2 + s.x * R, W / 2 - s.y * R, r, 0, 2 * Math.PI)
        ctx.fillStyle = fill
        ctx.fill()
        if (stroke) {
          ctx.lineWidth = 1
          ctx.strokeStyle = stroke
          ctx.stroke()
        }
      }
      const dpr = W / (c.clientWidth || W)
      points.current.all.forEach((p) => dot(p, 1.4 * dpr, 'rgba(255,255,255,0.45)'))
      points.current.hi.forEach((p) => dot(p, 3.2 * dpr, accent, 'rgba(0,0,0,0.7)'))
    })
  }, [lon0Tex, accent])

  // texture, and the canvas size following its box
  useEffect(() => {
    let live = true
    const c = canvas.current
    if (!c || !c.getContext('2d')) {
      setFailed(true)
      return
    }
    const img = new Image()
    img.onload = () => {
      if (!live) return
      const off = document.createElement('canvas')
      off.width = img.naturalWidth
      off.height = img.naturalHeight
      const octx = off.getContext('2d')
      if (!octx) return
      octx.drawImage(img, 0, 0)
      tex.current = { data: octx.getImageData(0, 0, off.width, off.height).data, w: off.width, h: off.height }
      draw()
    }
    img.src = `${import.meta.env.BASE_URL}img/planet-${body}.jpg`
    const fit = () => {
      const px = Math.round((c.clientWidth || 360) * Math.min(window.devicePixelRatio || 1, 1.5))
      if (c.width !== px) {
        c.width = px
        c.height = px
      }
      draw()
    }
    fit()
    const ro = typeof ResizeObserver !== 'undefined' ? new ResizeObserver(fit) : null
    ro?.observe(c)
    return () => {
      live = false
      ro?.disconnect()
      cancelAnimationFrame(frame.current)
    }
  }, [body, draw])

  useEffect(() => {
    points.current = { all: windows, hi: highlight }
    draw()
  }, [windows, highlight, draw])

  useEffect(() => {
    if (!focus) return
    view.current = { ...view.current, lat0: focus.lat, lon0: focus.lon }
    draw()
  }, [focus, draw])

  const disc = (e: React.PointerEvent<HTMLCanvasElement>) => {
    const r = e.currentTarget.getBoundingClientRect()
    const R = (r.width / 2) * 0.94 * view.current.zoom
    return { x: (e.clientX - r.left - r.width / 2) / R, y: (r.height / 2 - (e.clientY - r.top)) / R, R }
  }
  const onDown = (e: React.PointerEvent<HTMLCanvasElement>) => {
    e.currentTarget.setPointerCapture?.(e.pointerId)
    drag.current = { x: e.clientX, y: e.clientY, lat0: view.current.lat0, lon0: view.current.lon0, moved: false }
  }
  const onMove = (e: React.PointerEvent<HTMLCanvasElement>) => {
    const d = drag.current
    if (!d) return
    const dx = e.clientX - d.x
    const dy = e.clientY - d.y
    if (Math.hypot(dx, dy) > 4) d.moved = true
    if (!d.moved) return
    const R = disc(e).R
    view.current.lon0 = d.lon0 - (dx / R) * 57.2958
    view.current.lat0 = Math.max(-90, Math.min(90, d.lat0 + (dy / R) * 57.2958))
    draw()
  }
  const onUp = (e: React.PointerEvent<HTMLCanvasElement>) => {
    const d = drag.current
    drag.current = null
    if (!d || d.moved) return
    const p = disc(e)
    const g = unproject(p.x, p.y, view.current.lat0, view.current.lon0)
    if (g) onPick(g.lat, g.lon)
  }
  const zoom = (f: number) => {
    view.current.zoom = Math.max(1, Math.min(6, view.current.zoom * f))
    draw()
  }

  return (
    <div className="planet-globe">
      <canvas aria-label={label} className="planet-globe-canvas" onPointerDown={onDown} onPointerMove={onMove}
        onPointerUp={onUp} ref={canvas} role="img" />
      <div className="planet-zoom">
        <button aria-label={zoomIn} onClick={() => zoom(1.5)} type="button">+</button>
        <button aria-label={zoomOut} onClick={() => zoom(1 / 1.5)} type="button">−</button>
      </div>
      {failed && <p className="note">{noWebgl}</p>}
    </div>
  )
}
