import type { Feature, GeoJsonObject } from 'geojson'
import type { Layer, PathOptions } from 'leaflet'
import { useCallback, useEffect, useRef, useState } from 'react'
import { CircleMarker, GeoJSON, TileLayer, Tooltip, useMap, useMapEvents } from 'react-leaflet'
import { useAppStore } from '../store'
import { layerUrl, v3, type CellCollection, type CellProps, type Zone } from './api'
import { cellLines, cellState, cividis, PATTERN, type CoverageClass } from './model'
import { V3_TEXTS } from './text'

export const TILE_MAX_ZOOM = 7 // raster tiles exist for zoom 0 to 7 (ADR-004); 5 km cells above
export const MAP_MAX_ZOOM = 11
// An empty tile is answered 204 (no data there): draw nothing instead of a broken image.
const EMPTY_TILE = 'data:image/gif;base64,R0lGODlhAQABAIAAAAAAAP///yH5BAEAAAAALAAAAAABAAEAAAIBRAA7'

/** Cells of the view above zoom 7: value (cividis), confidence outline, and the coverage hatching on top. */
function Cells({ scenario, env, overlay, confidence, onError }: {
  scenario: string
  env: string
  overlay: boolean
  confidence: boolean
  onError: (message: string | null) => void
}) {
  const lang = useAppStore((s) => s.lang)
  const t = V3_TEXTS[lang]
  const [data, setData] = useState<CellCollection | null>(null)
  const ctl = useRef<AbortController | null>(null)
  const map = useMap()
  const [zoom, setZoom] = useState(() => map.getZoom())
  const load = useCallback(() => {
    ctl.current?.abort()
    if (map.getZoom() <= TILE_MAX_ZOOM) {
      onError(null)
      return
    }
    const b = map.getBounds()
    const c = new AbortController()
    ctl.current = c
    v3.cells(scenario, env, [Math.max(-180, b.getWest()), Math.max(-90, b.getSouth()), Math.min(180, b.getEast()), Math.min(90, b.getNorth())], c.signal)
      .then((d) => {
        setData(d)
        onError(null)
      })
      .catch((e: unknown) => {
        if (!c.signal.aborted) {
          setData(null)
          onError(e instanceof Error ? e.message : String(e))
        }
      })
  }, [env, map, onError, scenario])
  useMapEvents({ moveend: () => { setZoom(map.getZoom()); load() } })
  useEffect(() => {
    load()
    return () => ctl.current?.abort()
  }, [load])
  if (!data || zoom <= TILE_MAX_ZOOM) return null
  const geo = data as unknown as GeoJsonObject
  const props = (f?: Feature) => f?.properties as CellProps
  const value = (f?: Feature): PathOptions => {
    const p = props(f)
    const st = cellState(p, t).state
    const fill = p.typicality.median === null || st === 'not_evaluated' || st === 'masked' ? '#2a3044' : cividis(p.typicality.median)
    const outline = !confidence || p.confidence === 'high' ? { stroke: false } : { stroke: true, color: '#eef0f6', weight: p.confidence === 'low' ? 1.2 : 0.6, dashArray: p.confidence === 'low' ? '3 3' : undefined }
    return { className: 'v3-cell', fillColor: fill, fillOpacity: 0.8, ...outline }
  }
  const hatch = (f?: Feature): PathOptions => {
    const pattern = PATTERN[props(f).coverage as CoverageClass] ?? 'pat-none'
    return pattern === 'pat-none' ? { className: 'v3-hatch', stroke: false, fillOpacity: 0 } : { className: 'v3-hatch', stroke: false, fillColor: `url(#${pattern})`, fillOpacity: 1 }
  }
  const tip = (f: Feature, layer: Layer) => {
    const el = document.createElement('div')
    for (const line of cellLines(props(f), t)) {
      const d = document.createElement('div')
      d.textContent = line
      el.appendChild(d)
    }
    layer.bindTooltip(el, { sticky: true, className: 'v3-tip' })
  }
  const key = `${data.release}-${scenario}-${env}-${data.features.length}-${data.features[0]?.properties.id ?? ''}-${lang}`
  return (
    <>
      <GeoJSON data={geo} key={`v-${key}-${confidence}`} onEachFeature={tip} style={value} />
      {overlay && <GeoJSON data={geo} interactive={false} key={`o-${key}`} style={hatch} />}
    </>
  )
}

/** v3 layers inside a mission map: typicality tiles to zoom 7, the coverage overlay, cells above zoom 7. */
export function V3Layers({ release, scenario, env, overlay, confidence, onCellsError }: {
  release: string
  scenario: string
  env: string
  overlay: boolean
  confidence: boolean
  onCellsError: (message: string | null) => void
}) {
  return (
    <>
      <TileLayer
        attribution="EarthMoon v3 · Copernicus DEM GLO-30 · ESA WorldCover"
        errorTileUrl={EMPTY_TILE}
        key={`ty-${scenario}-${env}`}
        maxNativeZoom={TILE_MAX_ZOOM}
        maxZoom={TILE_MAX_ZOOM}
        opacity={0.8}
        url={layerUrl(scenario, env, 'typicality', release)}
      />
      {overlay && <TileLayer errorTileUrl={EMPTY_TILE} key={`co-${scenario}-${env}`} maxNativeZoom={TILE_MAX_ZOOM} maxZoom={TILE_MAX_ZOOM} url={layerUrl(scenario, env, 'coverage', release)} />}
      <Cells confidence={confidence} env={env} onError={onCellsError} overlay={overlay} scenario={scenario} />
    </>
  )
}

/** Candidate zones (or query results) as rings on the map. */
export function ZoneMarkers({ zones, selectedId, onSelect, label }: {
  zones: { id: string; lat: number; lon: number; value: number }[]
  selectedId: string | null
  onSelect: (id: string) => void
  label: (index: number, value: number) => string
}) {
  return (
    <>
      {zones.map((z, i) => (
        <CircleMarker
          center={[z.lat, z.lon]}
          eventHandlers={{ click: () => onSelect(z.id) }}
          key={z.id}
          pathOptions={{ color: z.id === selectedId ? '#ffffff' : '#ffc457', weight: z.id === selectedId ? 3 : 1.6, fillColor: cividis(z.value), fillOpacity: 0.9 }}
          radius={z.id === selectedId ? 9 : 6}
        >
          <Tooltip direction="top" offset={[0, -6]}>{label(i, z.value)}</Tooltip>
        </CircleMarker>
      ))}
    </>
  )
}

/** Flies to a point at the zoom where cells are drawn. */
export function FlyToPoint({ point }: { point: { lat: number; lon: number; key: string } | null }) {
  const map = useMap()
  useEffect(() => {
    if (point) map.flyTo([point.lat, point.lon], Math.max(map.getZoom(), 9), { duration: 0.8 })
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [map, point?.key])
  return null
}

export type ZoneLike = Pick<Zone, 'id' | 'lat' | 'lon'>
