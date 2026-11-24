import { useEffect, useMemo, useState } from 'react'
import { v3 as v3api, type AnalogPoint, type AnalogZone } from './api'
import { PlanetGlobe, type GlobePoint } from './PlanetGlobe'
import type { V3Texts } from './text'

type Loader = Pick<typeof v3api, 'analogTarget' | 'analogZone' | 'analogPoint'>

/**
 * The planet beside the Earth map (T45c part 2). An Earth zone selected on the map lights the windows of the same
 * slope on the globe; a point clicked on the globe lists the Earth zones of the same slope, and picking one selects it
 * on the map. Coordinates stay in the details; names come first.
 */
export function PlanetPanel({ body, scenario, env, release, zoneId, zoneName, onZone, lang, t, load = v3api }: {
  body: 'moon' | 'mars'
  scenario: string
  env: string
  release: string
  zoneId: string | null
  zoneName: string | null
  onZone: (id: string) => void
  lang: 'en' | 'fr'
  t: V3Texts
  load?: Loader
}) {
  // every result is kept with the target it belongs to, so a change of target never shows stale windows
  const key = `${release}|${scenario}|${env}`
  const [target, setTarget] = useState<{ key: string; windows: GlobePoint[] | null } | null>(null)
  const [link, setLink] = useState<{ id: string; data: AnalogZone | null } | null>(null)
  const [pointAt, setPoint] = useState<{ key: string; data: AnalogPoint } | null>(null)

  useEffect(() => {
    let live = true
    load.analogTarget(scenario, env, release)
      .then((r) => live && setTarget({ key, windows: r.windows.lat.map((lat, k) => ({ lat, lon: r.windows.lon[k], name: r.windows.name[k] })) }))
      .catch(() => live && setTarget({ key, windows: null }))
    return () => {
      live = false
    }
  }, [key, scenario, env, release, load])
  const loaded = target?.key === key ? target : null
  const windows = useMemo(() => loaded?.windows ?? [], [loaded])
  const targetMissing = loaded !== null && loaded.windows === null
  const point = pointAt?.key === key ? pointAt.data : null

  useEffect(() => {
    if (!zoneId) return
    let live = true
    load.analogZone(zoneId, release)
      .then((r) => live && setLink({ id: zoneId, data: r }))
      .catch(() => live && setLink({ id: zoneId, data: null }))
    return () => {
      live = false
    }
  }, [zoneId, release, load])

  const current = zoneId && link?.id === zoneId ? link : null
  const highlight = useMemo(() => current?.data?.windows ?? [], [current])
  const focus = useMemo(() => {
    const h = current?.data?.windows?.[0] ?? windows[0]
    return h ? { lat: h.lat, lon: h.lon } : null
  }, [current, windows])
  const bodyName = t.bodyLabel

  const pick = (lat: number, lon: number) => {
    load.analogPoint(scenario, env, lat, lon, release).then((data) => setPoint({ key, data })).catch(() => setPoint(null))
  }

  if (targetMissing) return null
  const pct = (p: number) => Math.round(p * 100)
  return (
    <section aria-label={t.globeTitle(bodyName)} className="planet-panel">
      <h3>{t.globeTitle(bodyName)}</h3>
      <PlanetGlobe body={body} focus={focus} highlight={highlight} label={t.globeLabel(bodyName)} noWebgl={t.noWebgl} onPick={pick} windows={windows} zoomIn={t.zoomIn} zoomOut={t.zoomOut} />
      <p className="planet-hint">{t.globeHint}</p>
      {zoneId && current && (
        <p className="planet-caption" role="status">
          {current.data && current.data.zone.slope_median != null
            ? (current.data.windows.length
              ? t.sameSlope(current.data.windows.length, zoneName ?? zoneId, current.data.zone.slope_median.toFixed(1), pct(current.data.percentile))
              : t.sameSlopeNone)
            : t.noLink}
        </p>
      )}
      {point && (
        <div className="planet-point" role="status">
          <p>{t.pointCaption(point.window.name, point.window.slope.toFixed(1), pct(point.percentile))}</p>
          {point.zones.length ? (
            <>
              <h4>{t.pointZones}</h4>
              <ul>
                {point.zones.map((z) => (
                  <li key={z.id}>
                    <button className="planet-zone" onClick={() => onZone(z.id)} type="button">
                      <strong>{z.place?.[lang] ?? `${z.lat.toFixed(2)}, ${z.lon.toFixed(2)}`}</strong>
                      <small>{`${z.lat.toFixed(2)}, ${z.lon.toFixed(2)}`}{z.typicality != null ? ` · ${z.typicality.toFixed(2)}` : ''}</small>
                    </button>
                  </li>
                ))}
              </ul>
            </>
          ) : <p>{t.pointNoZone}</p>}
        </div>
      )}
      <p className="planet-rule">{t.globeRule}</p>
      <p className="planet-credit">{t.globeCredit(bodyName)} {t.osm}</p>
    </section>
  )
}
