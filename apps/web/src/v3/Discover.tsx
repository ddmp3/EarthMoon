import type { Feature, GeoJsonObject } from 'geojson'
import type { Layer, PathOptions } from 'leaflet'
import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { CircleMarker, GeoJSON, MapContainer, TileLayer, Tooltip, useMap, useMapEvents } from 'react-leaflet'
import { useAppStore } from '../store'
import { layerUrl, v3, type CellCollection, type CellProps, type Coverage, type MethodSource, type Scenario, type Status, type Zone } from './api'
import { cellLines, cellState, cividis, PATTERN, type CoverageClass } from './model'
import { CompareZones, CoverageLegend, DataMethod, LayerPanel, Patterns, Provenance, StatusBar, ValueLegend, ZoneCard, ZoneList } from './panels'
import { targetName, V3_TEXTS } from './text'
import './v3.css'

const GIBS_TILES =
  'https://gibs.earthdata.nasa.gov/wmts/epsg3857/best/BlueMarble_ShadedRelief_Bathymetry/default/GoogleMapsCompatible_Level8/{z}/{y}/{x}.jpeg'
const TILE_MAX_ZOOM = 7 // raster tiles exist for zoom 0 to 7 (ADR-004); cells above
const MAX_ZOOM = 11

type ReleaseDoc = Awaited<ReturnType<typeof v3.release>> & { protocol?: string; commit?: string }

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
    return { fillColor: fill, fillOpacity: 0.8, ...outline }
  }
  const hatch = (f?: Feature): PathOptions => {
    const cls = props(f).coverage as CoverageClass
    const pattern = PATTERN[cls] ?? 'pat-none'
    return pattern === 'pat-none' ? { stroke: false, fillOpacity: 0 } : { stroke: false, fillColor: `url(#${pattern})`, fillOpacity: 1 }
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

function FlyTo({ zone }: { zone: Zone | null }) {
  const map = useMap()
  useEffect(() => {
    if (zone) map.flyTo([zone.lat, zone.lon], Math.max(map.getZoom(), 9), { duration: 0.8 })
  }, [map, zone])
  return null
}

function ZoomNote({ text }: { text: string }) {
  const [zoom, setZoom] = useState<number>(2)
  useMapEvents({ zoomend: (e) => setZoom(e.target.getZoom()) })
  return zoom <= TILE_MAX_ZOOM ? <div className="v3-map-note">{text}</div> : null
}

export function Discover({ onBack }: { onBack: () => void }) {
  const lang = useAppStore((s) => s.lang)
  const t = V3_TEXTS[lang]
  const [error, setError] = useState<string | null>(null)
  const [release, setRelease] = useState<ReleaseDoc | null>(null)
  const [scenarios, setScenarios] = useState<Scenario[]>([])
  const [status, setStatus] = useState<Status | null>(null)
  const [method, setMethod] = useState<{ sources: MethodSource[]; processing: Record<string, unknown>[] } | null>(null)
  const [scenarioId, setScenarioId] = useState('B')
  const [envChoice, setEnv] = useState('')
  const [tau, setTau] = useState(0.5)
  const [minCells, setMinCells] = useState(3)
  const [coverageAt, setCoverage] = useState<{ key: string; coverage: Coverage['coverage'] | null } | null>(null)
  const [zonesAt, setZones] = useState<{ key: string; total: number; zones: Zone[] } | null>(null)
  const [overlay, setOverlay] = useState(true)
  const [confidence, setConfidence] = useState(true)
  const [open, setOpen] = useState<Zone | null>(null)
  const [compareAt, setCompare] = useState<{ key: string; zones: Zone[] } | null>(null)
  const [showMethod, setShowMethod] = useState(false)
  const [showProv, setShowProv] = useState(false)
  const [cellsError, setCellsError] = useState<string | null>(null)

  useEffect(() => {
    let alive = true
    v3.releases()
      .then(async (idx) => {
        const [rel, sc, st, me] = await Promise.all([v3.release(idx.current), v3.scenarios(), v3.status(), v3.method()])
        if (!alive) return
        const info = idx.releases.find((r) => r.id === idx.current)
        setRelease({ ...rel, protocol: info?.protocol, commit: info?.commit })
        setTau(rel.grid.nominal.tau)
        setMinCells(rel.grid.nominal.min_cells)
        setScenarios(sc.scenarios)
        setStatus(st)
        setMethod(me)
      })
      .catch((e: unknown) => alive && setError(e instanceof Error ? e.message : String(e)))
    return () => {
      alive = false
    }
  }, [])

  const scenario = useMemo(() => scenarios.find((s) => s.id === scenarioId) ?? null, [scenarios, scenarioId])
  // the environment shown: the chosen one if this scenario assesses it, else its first assessed target
  const env = scenario?.assessed_targets.includes(envChoice) ? envChoice : (scenario?.assessed_targets[0] ?? '')
  const covKey = `${scenario?.id}|${env}`
  const zonesKey = `${covKey}|${tau}|${minCells}`
  const coverage = coverageAt?.key === covKey ? coverageAt.coverage : null
  const zones = zonesAt?.key === zonesKey ? zonesAt : null
  const compare = compareAt?.key === zonesKey ? compareAt.zones : null

  useEffect(() => {
    if (!scenario || !env) return
    let alive = true
    v3.coverage(scenario.id, env)
      .then((c) => alive && setCoverage({ key: covKey, coverage: c.coverage }))
      .catch(() => alive && setCoverage({ key: covKey, coverage: null }))
    return () => {
      alive = false
    }
  }, [scenario, env, covKey])

  useEffect(() => {
    if (!scenario || !env) return
    let alive = true
    v3.zones(scenario.id, env, tau, minCells, 50)
      .then((p) => alive && setZones({ key: zonesKey, total: p.total, zones: p.zones }))
      .catch((e: unknown) => alive && setError(e instanceof Error ? e.message : String(e)))
    return () => {
      alive = false
    }
  }, [scenario, env, tau, minCells, zonesKey])

  const openZone = (id: string) => {
    const z = zones?.zones.find((x) => x.id === id) ?? null
    setOpen(z)
    setCompare(null)
  }
  const cannot = scenario?.cannot_assess ?? []
  const onCellsError = useCallback((m: string | null) => setCellsError(m), [])

  if (error) {
    return (
      <section className="v3-page">
        <button className="back" onClick={onBack} type="button">← {t.back}</button>
        <div className="error-box" role="alert">
          <strong>{t.error}</strong>
          <p>{/503/.test(error) ? t.noRelease : error}</p>
        </div>
      </section>
    )
  }

  return (
    <section className="v3-page" aria-labelledby="v3-title">
      <Patterns />
      <div className="v3-head">
        <button className="back" onClick={onBack} type="button">← {t.back}</button>
        <h1 id="v3-title">{t.title}</h1>
        <p className="lead">{t.lead}</p>
        <div className="v3-selectors">
          <label>
            <span>{t.scenario}</span>
            <select onChange={(e) => setScenarioId(e.target.value)} value={scenarioId}>
              {scenarios.map((s) => <option key={s.id} value={s.id}>{s.id} · {s.name}</option>)}
            </select>
          </label>
          <label>
            <span>{t.environment}</span>
            <select onChange={(e) => setEnv(e.target.value)} value={env}>
              {scenario?.targets.map((id) => (
                <option disabled={!scenario.assessed_targets.includes(id)} key={id} value={id}>
                  {targetName(t, id)}{scenario.assessed_targets.includes(id) ? '' : ` (${t.notComparable})`}
                </option>
              ))}
            </select>
          </label>
        </div>
        <StatusBar status={status} t={t} />
      </div>

      <div className="v3-body">
        <aside className="v3-side">
          <LayerPanel confidence={confidence} onConfidence={setConfidence} t={t} />
          <CoverageLegend coverage={coverage} on={overlay} onInfo={() => setShowMethod(true)} onToggle={setOverlay} t={t} />
          <ValueLegend t={t} />
          <section className="v3-block" aria-labelledby="v3-zones-title">
            <h3 id="v3-zones-title">{t.zones}</h3>
            <p className="note">{t.zonesLead}</p>
            <div className="v3-selectors v3-small">
              <label>
                <span>{t.tau}</span>
                <select onChange={(e) => setTau(Number(e.target.value))} value={tau}>
                  {(release?.grid.tau ?? [tau]).map((v) => <option key={v} value={v}>{v}</option>)}
                </select>
              </label>
              <label>
                <span>{t.minCells}</span>
                <select onChange={(e) => setMinCells(Number(e.target.value))} value={minCells}>
                  {(release?.grid.min_cells ?? [minCells]).map((v) => <option key={v} value={v}>{v}</option>)}
                </select>
              </label>
            </div>
            {zones ? (
              <ZoneList
                onCompare={(ids) => setCompare({ key: zonesKey, zones: ids.map((id) => zones.zones.find((z) => z.id === id)).filter((z): z is Zone => !!z) })}
                onOpen={openZone}
                t={t}
                total={zones.total}
                zones={zones.zones}
              />
            ) : (
              <p className="note">{t.loading}</p>
            )}
          </section>
        </aside>

        <div className="v3-main">
          <div className="v3-map">
            {release && scenario && env && (
              <MapContainer center={[20, 10]} maxZoom={MAX_ZOOM} minZoom={1} scrollWheelZoom worldCopyJump zoom={2}>
                <TileLayer attribution="NASA Blue Marble · NASA GIBS" maxNativeZoom={8} url={GIBS_TILES} />
                <TileLayer
                  attribution="EarthMoon v3 · Copernicus DEM GLO-30 · ESA WorldCover"
                  key={`ty-${scenario.id}-${env}`}
                  maxNativeZoom={TILE_MAX_ZOOM}
                  maxZoom={TILE_MAX_ZOOM}
                  opacity={0.85}
                  url={layerUrl(scenario.id, env, 'typicality', release.release)}
                />
                {overlay && (
                  <TileLayer key={`co-${scenario.id}-${env}`} maxNativeZoom={TILE_MAX_ZOOM} maxZoom={TILE_MAX_ZOOM} url={layerUrl(scenario.id, env, 'coverage', release.release)} />
                )}
                <Cells confidence={confidence} env={env} onError={onCellsError} overlay={overlay} scenario={scenario.id} />
                {zones?.zones.map((z) => (
                  <CircleMarker
                    center={[z.lat, z.lon]}
                    eventHandlers={{ click: () => openZone(z.id) }}
                    key={z.id}
                    pathOptions={{ color: '#ffc457', weight: 1.5, fillOpacity: 0 }}
                    radius={5}
                  >
                    <Tooltip>{t.zone} {z.rank} · {z.typicality.median.toFixed(2)}</Tooltip>
                  </CircleMarker>
                ))}
                <FlyTo zone={open} />
                <ZoomNote text={t.zoomForCells} />
              </MapContainer>
            )}
            {cellsError && <div className="v3-map-note v3-map-error" role="alert">{t.cellsError}: {cellsError}</div>}
          </div>
          {compare && compare.length >= 2 && <CompareZones onClose={() => setCompare(null)} t={t} zones={compare} />}
          {open && (
            <ZoneCard cannotAssess={cannot} status={status} onClose={() => setOpen(null)} onProvenance={() => setShowProv(true)} scenario={scenario} t={t} zone={open} />
          )}
        </div>
      </div>

      <div className="v3-cannot-bar">
        <strong>{t.cannotReproduce}:</strong> {cannot.join(' ')}
      </div>

      {showMethod && method && (
        <DataMethod cannotAssess={cannot} coverage={coverage} onClose={() => setShowMethod(false)} processing={method.processing} sources={method.sources} t={t} />
      )}
      {showProv && open && <Provenance onClose={() => setShowProv(false)} status={status} release={release && { release: release.release, run: release.run, protocol: release.protocol, commit: release.commit }} t={t} zone={open} />}
    </section>
  )
}
