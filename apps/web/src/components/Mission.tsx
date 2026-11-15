import { useEffect, useRef } from 'react'
import { CircleMarker, MapContainer, TileLayer, Tooltip, useMap } from 'react-leaflet'
import {
  calibrationInstruments,
  paramInfo,
  parameterCatalog,
  siteImage,
  type CalibrationInstrument,
  type SiteResult,
  type VisualManifest,
} from '../api'
import { useT } from '../i18n'
import { useAppStore, type SelectedMode } from '../store'
import { missionImage, scoreTone, siteName } from '../shared'

const TONE_COLOR = { good: '#6fd39a', mid: '#ffc457', low: '#ff7a6b', off: '#6b7388' } as const
// NASA Blue Marble (GIBS) : fond de carte en vraies couleurs, jusqu'au niveau de zoom 8.
const GIBS_TILES =
  'https://gibs.earthdata.nasa.gov/wmts/epsg3857/best/BlueMarble_ShadedRelief_Bathymetry/default/GoogleMapsCompatible_Level8/{z}/{y}/{x}.jpeg'

function FlyTo({ site }: { site: SiteResult | null }) {
  const map = useMap()
  const first = useRef(true)
  useEffect(() => {
    if (!site) return
    const zoom = Math.max(map.getZoom(), 4)
    if (first.current) map.setView([site.lat, site.lon], zoom, { animate: false })
    else map.flyTo([site.lat, site.lon], zoom, { duration: 0.8 })
    first.current = false
  }, [map, site])
  return null
}

function CustomBuilder({ onRun, error }: { onRun: () => void; error: string | null }) {
  const { t } = useT()
  const { criteriaDraft, updateCriterion, addCriterion, removeCriterion } = useAppStore()
  return (
    <section className="builder">
      <div className="section-head">
        <div>
          <h3>{t.customTitle}</h3>
          <p>{t.customLead}</p>
        </div>
      </div>
      <div className="builder-rows">
        {criteriaDraft.map((criterion, index) => (
          <div className="builder-row" key={index}>
            <label>
              <span>{t.parameter}</span>
              <select
                id={`criterion-param-${index}`}
                onChange={(event) => updateCriterion(index, { param: event.target.value as typeof criterion.param })}
                value={criterion.param}
              >
                {parameterCatalog.map((parameter) => (
                  <option
                    disabled={criteriaDraft.some((other, otherIndex) => otherIndex !== index && other.param === parameter.id)}
                    key={parameter.id}
                    value={parameter.id}
                  >
                    {parameter.label}
                  </option>
                ))}
              </select>
            </label>
            {(['min', 'max', 'tolerance', 'weight'] as const).map((field) => (
              <label className="builder-number" key={field}>
                <span>
                  {t[field]}
                  {field !== 'weight' && paramInfo(criterion.param, 'en').unit ? ` (${paramInfo(criterion.param, 'en').unit})` : ''}
                </span>
                <input
                  id={`criterion-${field}-${index}`}
                  inputMode="decimal"
                  onChange={(event) => updateCriterion(index, { [field]: event.target.value })}
                  value={criterion[field]}
                />
              </label>
            ))}
            <button className="ghost" disabled={criteriaDraft.length === 1} onClick={() => removeCriterion(index)} type="button">
              {t.remove}
            </button>
            <small className="builder-help">{paramInfo(criterion.param, 'en').help}</small>
          </div>
        ))}
      </div>
      {error && <p className="note note-error" role="alert">{error}</p>}
      <div className="builder-actions">
        <button className="ghost" disabled={criteriaDraft.length >= parameterCatalog.length} onClick={addCriterion} type="button">
          + {t.addCriterion}
        </button>
        <button className="primary" onClick={onRun} type="button">
          {t.run} →
        </button>
      </div>
    </section>
  )
}

interface Props {
  mode: SelectedMode
  sites: SiteResult[]
  selectedId: string | null
  loading: boolean
  error: string | null
  builderError: string | null
  manifest: VisualManifest | null
  onBack: () => void
  onSelect: (id: string) => void
  onRun: () => void
  children: React.ReactNode
}

/** Mission screen: banner, settings, illustrated ranking, NASA map, then the chosen site's card. */
export function Mission({ mode, sites, selectedId, loading, error, builderError, manifest, onBack, onSelect, onRun, children }: Props) {
  const { t } = useT()
  const { bareSoilOnly, setBareSoilOnly, calibrationInstrument, setCalibrationInstrument } = useAppStore()
  const mission = t.missions[mode]
  const selected = sites.find((site) => site.id === selectedId) ?? null
  const ranked = sites.filter((site) => !site.excluded).length

  return (
    <>
      <section className={`mission-banner mission-banner-${mode}`}>
        <img alt="" src={missionImage(mode)} />
        <div className="mission-banner-shade" />
        <div className="mission-banner-copy">
          <button className="back" onClick={onBack} type="button">
            ← {t.backToMissions}
          </button>
          <h1>{mission.title}</h1>
          <p>{mission.text}</p>
        </div>
        <span className="photo-credit">{mission.credit}</span>
      </section>

      <section className="controls">
        {mode === 'calibration' && (
          <label className="field">
            <span>{t.instrument}</span>
            <select
              id="instrument"
              onChange={(event) => setCalibrationInstrument(event.target.value as CalibrationInstrument | 'all')}
              value={calibrationInstrument}
            >
              <option value="all">{t.allInstruments}</option>
              {calibrationInstruments.map((instrument) => (
                <option key={instrument} value={instrument}>
                  {t.instruments[instrument]}
                </option>
              ))}
            </select>
          </label>
        )}
        <label className="check">
          <input checked={bareSoilOnly} id="bare-soil" onChange={(event) => setBareSoilOnly(event.target.checked)} type="checkbox" />
          <span>
            {t.bareSoil} <small>{t.bareSoilHint}</small>
          </span>
        </label>
      </section>

      {mode === 'custom' && <CustomBuilder error={builderError} onRun={onRun} />}

      {loading && (
        <div className="state" role="status">
          <span className="spinner" />
          <strong>{t.loading}</strong>
          <span>{t.loadingHint}</span>
        </div>
      )}
      {error && !loading && (
        <div className="state state-error" role="alert">
          <strong>{t.errorTitle}</strong>
          <span>{error}</span>
          <button className="primary" onClick={onRun} type="button">
            {t.retry}
          </button>
        </div>
      )}

      {!loading && !error && sites.length > 0 && (
        <>
          <section className="explore">
            <div className="ranking">
              <div className="ranking-head">
                <h3>{t.ranking}</h3>
                <span>
                  {ranked} {t.sitesRanked}
                </span>
              </div>
              <ol>
                {sites.map((site, index) => {
                  const tone = scoreTone(site.total, Boolean(site.excluded))
                  const hasPhoto = Boolean(manifest?.sites[site.id]?.photo)
                  const thumb = manifest?.sites[site.id] ? siteImage(site.id, hasPhoto ? 'earth.jpg' : 'earth-relief.jpg') : null
                  return (
                    <li key={site.id}>
                      <button
                        aria-current={site.id === selectedId}
                        className={`rank-row${site.excluded ? ' is-excluded' : ''}`}
                        onClick={() => onSelect(site.id)}
                        type="button"
                      >
                        <span className="rank-number">{String(index + 1).padStart(2, '0')}</span>
                        {thumb ? <img alt="" loading="lazy" src={thumb} /> : <span className="rank-thumb-empty" />}
                        <span className="rank-copy">
                          <strong>{siteName(site)}</strong>
                          <small>{site.excluded ? t.excluded : t.roles[site.role]}</small>
                        </span>
                        <span className={`rank-score tone-${tone}`}>{site.excluded ? '—' : Math.round(site.total)}</span>
                      </button>
                    </li>
                  )
                })}
              </ol>
            </div>

            <div className="map-wrap">
              <MapContainer center={[25, 10]} maxZoom={8} minZoom={1} scrollWheelZoom={false} worldCopyJump zoom={2}>
                <TileLayer attribution="NASA Blue Marble · NASA GIBS" maxNativeZoom={8} url={GIBS_TILES} />
                <FlyTo site={selected} />
                {[...sites].reverse().map((site) => {
                  const tone = scoreTone(site.total, Boolean(site.excluded))
                  const active = site.id === selectedId
                  return (
                    <CircleMarker
                      center={[site.lat, site.lon]}
                      eventHandlers={{ click: () => onSelect(site.id) }}
                      key={site.id}
                      pathOptions={{
                        color: active ? '#ffffff' : '#05070d',
                        weight: active ? 3 : 1.5,
                        fillColor: TONE_COLOR[tone],
                        fillOpacity: 0.95,
                      }}
                      radius={active ? 11 : 7}
                    >
                      <Tooltip direction="top" offset={[0, -6]}>
                        {siteName(site)} · {site.excluded ? t.excludedShort : Math.round(site.total)}
                      </Tooltip>
                    </CircleMarker>
                  )
                })}
              </MapContainer>
            </div>
          </section>
          {children}
        </>
      )}
    </>
  )
}
