import { useEffect, useRef, useState } from 'react'
import { CircleMarker, MapContainer, TileLayer, Tooltip, useMap } from 'react-leaflet'
import {
  calibrationInstruments,
  deprecation,
  paramInfo,
  parameterCatalog,
  siteImage,
  type CalibrationInstrument,
  type SiteResult,
  type VisualManifest,
} from '../api'
import { StabilityDots } from './Stability'
import { useT } from '../i18n'
import { useAppStore, type SelectedMode } from '../store'
import { MARS_MISSIONS, missionImage, scoreTone, siteName } from '../shared'
import type { QueryResult, Zone } from '../v3/api'
import { FlyToPoint, MAP_MAX_ZOOM, V3Layers, ZoneMarkers, type MapLayer } from '../v3/MapLayers'
import { MapLegend, RankTabs, SiteV3Chip, V3Controls, V3StatusLine, ZoneRows, type Tab } from '../v3/MissionV3'
import { zoneItems } from '../v3/model'
import { CompareZones, DataMethod, Patterns, Provenance, ZoneCard } from '../v3/panels'
import { PlanetPanel } from '../v3/PlanetPanel'
import { CriteriaPanel } from '../v3/Criteria'
import type { CriteriaRun } from '../v3/api'
import { CRITERIA_TEXTS } from '../v3/criteriaText'
import { v3Texts } from '../v3/text'
import type { V3State } from '../v3/useV3'

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
  const { t, lang } = useT()
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
                    {paramInfo(parameter.id, lang).label}
                    {deprecation(parameter.id, lang) ? (lang === 'fr' ? ' (déprécié)' : ' (deprecated)') : ''}
                  </option>
                ))}
              </select>
            </label>
            {(['min', 'max', 'tolerance', 'weight'] as const).map((field) => (
              <label className="builder-number" key={field}>
                <span>
                  {t[field]}
                  {field !== 'weight' && paramInfo(criterion.param, lang).unit ? ` (${paramInfo(criterion.param, lang).unit})` : ''}
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
            <small className="builder-help">{paramInfo(criterion.param, lang).help}</small>
            {deprecation(criterion.param, lang) && (
              <small className="builder-help note-warn" role="note">{deprecation(criterion.param, lang)}</small>
            )}
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
  v3: V3State
  onScenario: (id: string) => void
}

/** Mission screen: banner, settings, illustrated ranking, NASA map, then the chosen site's card. */
export function Mission({ mode, sites, selectedId, loading, error, builderError, manifest, onBack, onSelect, onRun, children, v3, onScenario }: Props) {
  const { t, lang } = useT()
  const { bareSoilOnly, setBareSoilOnly, calibrationInstrument, setCalibrationInstrument } = useAppStore()
  // Mars: the banner follows the terrain picked (its photo, title and text), as each lunar mission has its own (T45c)
  const terrain = mode === 'mars' ? MARS_MISSIONS.find((m) => m.id === v3.env) : undefined
  const mission = terrain ? t.marsMissions[terrain.id] : t.missions[mode]
  const bannerImage = terrain ? `${import.meta.env.BASE_URL}img/${terrain.image}.jpg` : missionImage(mode)
  const bannerClass = terrain ? `mission-photo-${terrain.image}` : `mission-banner-${mode}`
  const selected = sites.find((site) => site.id === selectedId) ?? null
  const ranked = sites.filter((site) => !site.excluded).length
  const vt = v3Texts(lang, mode === 'mars' ? 'mars' : 'moon')
  const [tabChoice, setTab] = useState<Tab>('sites')
  const [overlay, setOverlay] = useState(true)
  const [layerChoice, setLayer] = useState<MapLayer>('typicality')
  const [showMethod, setShowMethod] = useState(false)
  const [zoneId, setZoneId] = useState<string | null>(null)
  const [provenance, setProvenance] = useState(false)
  const [picked, setPicked] = useState<string[]>([])
  const [compare, setCompare] = useState(false)
  const [results, setResults] = useState<QueryResult | null>(null)
  const [crit, setCrit] = useState<CriteriaRun | null>(null)
  // the map waits for the use preset, which chooses the environment: no tiles loaded twice (ADR-006 budget)
  const [presetReady, setPresetReady] = useState(false)
  const [cellsError, setCellsError] = useState<string | null>(null)
  const [cellsTooMany, setCellsTooMany] = useState(false)
  const hasV3 = Boolean(v3.release && v3.scenario && v3.env)
  const layer: MapLayer = layerChoice !== 'typicality' && v3.available.includes(layerChoice) ? layerChoice : 'typicality'
  // free criteria opens on the discovered zones until the v2 criteria are run
  const tab: Tab = tabChoice === 'sites' && sites.length === 0 && hasV3 ? 'zones' : tabChoice
  const zones = v3.zones?.zones ?? []
  const zone: Zone | null = tab === 'zones' ? (zones.find((z) => z.id === zoneId) ?? null) : null
  const pickedZones = zones.filter((z) => picked.includes(z.id))
  const ct = CRITERIA_TEXTS[lang]
  const nPref = crit ? crit.rule.criteria.filter((c) => c.role === 'preferred').length : 0
  // T54: the results of the criteria panel; the old single-criterion search is no longer offered
  const resultItems = crit
    ? crit.cells.map((c) => ({ id: c.id, lat: c.lat, lon: c.lon, value: nPref ? c.preferred_met / nPref : 1, sub: ct.preferredMet(c.preferred_met, nPref) }))
    : (results?.cells ?? []).map((c) => ({ id: c.id, lat: c.lat, lon: c.lon, value: c.typicality, sub: `${vt.confidenceLabel} ${c.confidence ? (vt.confidenceLevel[c.confidence] ?? c.confidence) : '—'}` }))
  const focus = tab === 'zones' && zone ? { lat: zone.lat, lon: zone.lon, key: zone.id }
    : tab === 'results' && zoneId ? (() => { const c = resultItems.find((r) => r.id === zoneId); return c ? { lat: c.lat, lon: c.lon, key: c.id } : null })()
    : null
  const tabCounts: Partial<Record<Tab, number | null>> = sites.length > 0 ? { sites: ranked } : {}
  if (hasV3) tabCounts.zones = v3.zones?.total ?? null
  if (hasV3) tabCounts.results = crit ? crit.counts.candidate : null
  const selectTab = (next: Tab) => {
    setTab(next)
    setZoneId(null)
    setCompare(false)
  }

  return (
    <>
      <section className={`mission-banner ${bannerClass}`}>
        <img alt="" src={bannerImage} />
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
        {mode !== 'mars' && <label className="check">
          <input checked={bareSoilOnly} id="bare-soil" onChange={(event) => setBareSoilOnly(event.target.checked)} type="checkbox" />
          <span>
            {t.bareSoil} <small>{t.bareSoilHint}</small>
          </span>
        </label>}
        {mode !== 'calibration' && (
          <V3Controls layer={layer} onLayer={setLayer} onMethod={() => setShowMethod(true)} onOverlay={setOverlay} overlay={overlay} showEnv={!hasV3} v={v3} />
        )}
      </section>
      <Patterns />
      {mode === 'calibration' ? (
        <p className="v3-statusline">{vt.calibrationNote}</p>
      ) : (
        <V3StatusLine v={v3} />
      )}

      {mode === 'custom' && <CustomBuilder error={builderError} onRun={onRun} />}
      {hasV3 && v3.release && (
        <CriteriaPanel
          mission={mode}
          onPreset={(p) => {
            const target = p.terrain ?? p.targets[0]
            if (!target) { setPresetReady(true); return }
            if (!v3.scenario?.assessed_targets.includes(target) && mode === 'custom') {
              const other = v3.scenarios.find((s) => s.assessed_targets.includes(target))
              if (other) onScenario(other.id)
            }
            v3.setEnv(target)
            setPresetReady(true)
          }}
          onLoadError={() => setPresetReady(true)}
          onResults={(r) => {
            setCrit(r)
            setResults(null)
            setZoneId(null)
          }}
          release={v3.release.release}
          terrain={mode === 'mars' ? v3.env : undefined}
        />
      )}

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

      {showMethod && v3.method && (
        <DataMethod cannotAssess={v3.scenario?.cannot_assess ?? []} coverage={v3.coverage} onClose={() => setShowMethod(false)}
          processing={v3.method.processing} sources={v3.method.sources} t={vt} />
      )}
      {provenance && zone && (
        <Provenance onClose={() => setProvenance(false)} release={v3.release && { release: v3.release.release, run: v3.release.run, protocol: v3.release.protocol, commit: v3.release.commit }}
          status={v3.status} t={vt} zone={zone} />
      )}
      {!loading && !error && (sites.length > 0 || ((mode === 'custom' || mode === 'mars') && hasV3)) && (
        <>
          <section className="explore">
            <div className="ranking">
              <div className="ranking-head">
                <h3>{tab === 'sites' ? t.ranking : tab === 'zones' ? vt.zones : vt.tabResults}</h3>
                <span>
                  {tab === 'sites' ? `${ranked} ${t.sitesRanked}` : tab === 'zones' ? vt.zoneCount(v3.zones?.total ?? 0) : results ? vt.zoneCount(results.matched).replace('zones', vt.cellsWord) : ''}
                </span>
              </div>
              {Object.keys(tabCounts).length > 1 && <RankTabs counts={tabCounts} onTab={selectTab} tab={tab} />}
              {tab === 'zones' && (
                <div className="rank-scroll">
                  <div className="zone-settings">
                    <label className="field">
                      <span>{vt.tau}</span>
                      <select onChange={(e) => v3.setTau(Number(e.target.value))} value={v3.tau}>
                        {(v3.release?.grid.tau ?? [v3.tau]).map((x) => <option key={x} value={x}>{x}</option>)}
                      </select>
                    </label>
                    <label className="field">
                      <span>{vt.minCells}</span>
                      <select onChange={(e) => v3.setMin(Number(e.target.value))} value={v3.minCells}>
                        {(v3.release?.grid.min_cells ?? [v3.minCells]).map((x) => <option key={x} value={x}>{x}</option>)}
                      </select>
                    </label>
                    <button className="ghost" disabled={pickedZones.length < 2} onClick={() => setCompare(true)} type="button">
                      {vt.compare}{pickedZones.length ? ` · ${pickedZones.length}` : ''}
                    </button>
                  </div>
                  <p className="screening-note">{vt.zonesLead}</p>
                  <ZoneRows
                    items={zoneItems(zones, vt, lang)}
                    onPick={(id) => setPicked(picked.includes(id) ? picked.filter((x) => x !== id) : picked.length < 4 ? [...picked, id] : picked)}
                    onSelect={(id) => { setZoneId(id); setCompare(false) }}
                    picked={picked}
                    selectedId={zoneId}
                  />
                </div>
              )}
              {tab === 'results' && (
                <div className="rank-scroll">
                  <ZoneRows items={resultItems} onSelect={setZoneId} selectedId={zoneId} />
                </div>
              )}
              {tab === 'sites' && <p className="screening-note">{t.screeningNote}{hasV3 && <> {vt.v3ChipNote}</>}</p>}
              {tab === 'sites' && (
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
                          <strong>{siteName(site, lang)}</strong>
                          <small>
                            {site.excluded ? t.excluded : t.roles[site.role]}
                            {!site.excluded && <StabilityDots rank={index + 1} site={site} total={ranked} />}
                          </small>
                        </span>
                        <span className="rank-side">
                          <span className={`rank-score tone-${tone}`}>{site.excluded ? '—' : Math.round(site.total)}</span>
                          {hasV3 && <SiteV3Chip env={v3.env} site={v3.sites?.[site.id]} />}
                        </span>
                      </button>
                    </li>
                  )
                })}
              </ol>
              )}
            </div>

            <div className={hasV3 ? 'map-pair' : undefined}>
            <div className="map-block">
            <div className="map-wrap">
              <MapContainer center={[25, 10]} maxZoom={hasV3 ? MAP_MAX_ZOOM : 8} minZoom={1} scrollWheelZoom={false} worldCopyJump zoom={2}>
                <TileLayer attribution="NASA Blue Marble · NASA GIBS" maxNativeZoom={8} url={GIBS_TILES} />
                {hasV3 && v3.release && v3.scenario && presetReady && (
                  <V3Layers confidence env={v3.env} layer={layer} onCellsError={setCellsError} onCellsInfo={setCellsTooMany} overlay={overlay} release={v3.release.release} scenario={v3.scenario.id} />
                )}
                {tab === 'sites' && <FlyTo site={selected} />}
                <FlyToPoint point={focus} />
                {tab === 'zones' && (
                  <ZoneMarkers label={(i, val) => `${vt.zone} ${i + 1} · ${val.toFixed(2)}`} onSelect={(id) => { setZoneId(id); setCompare(false) }} selectedId={zoneId}
                    zones={zones.map((z) => ({ id: z.id, lat: z.lat, lon: z.lon, value: z.typicality.median }))} />
                )}
                {tab === 'results' && (
                  <ZoneMarkers label={(i, val) => `${i + 1} · ${val.toFixed(2)}`} onSelect={setZoneId} selectedId={zoneId}
                    zones={resultItems.map((r) => ({ id: r.id, lat: r.lat, lon: r.lon, value: r.value }))} />
                )}
                {tab === 'sites' && [...sites].reverse().map((site) => {
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
                        {siteName(site, lang)} · {site.excluded ? t.excludedShort : Math.round(site.total)}
                      </Tooltip>
                    </CircleMarker>
                  )
                })}
              </MapContainer>
              {cellsError && <div className="map-note map-note-error" role="alert">{vt.cellsError}: {cellsError}</div>}
              {!cellsError && cellsTooMany && <div className="map-note" role="status">{vt.cellsTooMany}</div>}
            </div>
            {hasV3 && <MapLegend available={v3.available} coverage={v3.coverage} layer={layer} overlay={overlay} />}
            </div>
            {hasV3 && v3.release && v3.scenario && (
              <PlanetPanel body={mode === 'mars' ? 'mars' : 'moon'} env={v3.env} lang={lang}
                onZone={(id) => { setTab('zones'); setZoneId(id) }} release={v3.release.release} scenario={v3.scenario.id}
                t={vt} zoneId={tab === 'zones' ? zoneId : null} zoneName={zone?.place?.[lang] ?? null} />
            )}
            </div>
          </section>
          {tab === 'sites' && children}
          {tab === 'zones' && compare && pickedZones.length >= 2 && (
            <div className="v3-under"><CompareZones onClose={() => setCompare(false)} t={vt} zones={pickedZones} /></div>
          )}
          {tab === 'zones' && zone && !compare && (
            <div className="v3-under">
              <ZoneCard cannotAssess={v3.scenario?.cannot_assess ?? []} onClose={() => setZoneId(null)} onProvenance={() => setProvenance(true)}
                scenario={v3.scenario} status={v3.status} t={vt} zone={zone} />
            </div>
          )}
        </>
      )}
    </>
  )
}
