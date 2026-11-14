import { useEffect, useMemo, useState } from 'react'
import { latLngBounds } from 'leaflet'
import { CircleMarker, MapContainer, Popup, TileLayer, useMap } from 'react-leaflet'
import fixtureJson from '../../../data/fixtures/site-values.json'
import './App.css'
import {
  analyzeSites,
  calibrationCriteria,
  calibrationInstruments,
  getSiteDetails,
  parameterCatalog,
  type CalibrationInstrument,
  type Criterion,
  type FixtureSite,
  type ModeId,
  type ParamId,
  type SiteDetail,
  type SiteResult,
  type SiteView,
} from './api'
import { useAppStore } from './store'

const modes: {
  id: ModeId | 'custom'
  number: string
  title: string
  description: string
}[] = [
  {
    id: 'robotics',
    number: '01',
    title: 'Validation robotique',
    description: 'Trouver un terrain pour tester la mobilité d’un rover.',
  },
  {
    id: 'calibration',
    number: '02',
    title: 'Calibration d’instruments',
    description: 'Comparer des conditions pour calibrer des instruments.',
  },
  {
    id: 'colony',
    number: '03',
    title: 'Colonie autosuffisante',
    description: 'Explorer les conditions utiles à une base lunaire.',
  },
  {
    id: 'custom',
    number: '04',
    title: 'Critères libres',
    description: 'Composer une analyse avec vos propres critères.',
  },
]

const fixtureSites = (fixtureJson as { sites: FixtureSite[] }).sites

type SiteDetailLoadState =
  | { siteId: string; detail: SiteDetail }
  | { siteId: string; error: string }

function MapResizeHandler() {
  const map = useMap()

  useEffect(() => {
    const timer = window.setTimeout(() => map.invalidateSize(), 100)
    return () => window.clearTimeout(timer)
  }, [map])

  return null
}

function FitMapToSites({ sites }: { sites: SiteView[] }) {
  const map = useMap()

  useEffect(() => {
    if (sites.length === 0) return
    const bounds = latLngBounds(sites.map((site) => [site.lat, site.lon]))
    map.fitBounds(bounds, { padding: [28, 28], maxZoom: 5 })
  }, [map, sites])

  return null
}

function scoreColor(
  total: number | null,
  role: SiteResult['role'],
  excluded = false,
) {
  if (excluded) return '#a0a5b3'
  if (total !== null) {
    if (total >= 70) return '#9cf26b'
    if (total >= 40) return '#f4c95d'
    return '#fa786e'
  }
  if (role === 'negative') return '#fa786e'
  if (role === 'candidate') return '#f4c95d'
  return '#7b91ff'
}

function formatValue(value: number | null | undefined, unit = '') {
  if (value === null || value === undefined) return 'Indisponible'
  const formatted = value.toLocaleString('fr-CA', { maximumFractionDigits: 2 })
  return unit ? `${formatted} ${unit}` : formatted
}

function roleLabel(role: SiteResult['role']) {
  if (role === 'negative') return 'Témoin négatif'
  if (role === 'candidate') return 'Site candidat'
  return 'Analogue connu'
}

function verdictLabel(verdict: SiteResult['criteria'][number]['verdict']) {
  if (verdict === 'match') return 'Correspond'
  if (verdict === 'partial') return 'Correspond partiellement'
  if (verdict === 'mismatch') return 'Ne correspond pas'
  return 'Donnée manquante'
}

function toFixtureResult(site: FixtureSite): SiteView {
  return {
    id: site.id,
    name: site.name,
    lat: site.lat,
    lon: site.lon,
    role: site.role,
    total: null,
    criteria: [],
    ...(typeof site.values.ndvi === 'number' && site.values.ndvi > 0.1
      ? { excluded: 'vegetation' as const }
      : {}),
    values: site.values,
  }
}

function App() {
  const selectedMode = useAppStore((state) => state.selectedMode)
  const criteriaDraft = useAppStore((state) => state.criteriaDraft)
  const bareSoilOnly = useAppStore((state) => state.bareSoilOnly)
  const calibrationInstrument = useAppStore((state) => state.calibrationInstrument)
  const setSelectedMode = useAppStore((state) => state.setSelectedMode)
  const setBareSoilOnly = useAppStore((state) => state.setBareSoilOnly)
  const setCalibrationInstrument = useAppStore((state) => state.setCalibrationInstrument)
  const updateCriterion = useAppStore((state) => state.updateCriterion)
  const addCriterion = useAppStore((state) => state.addCriterion)
  const removeCriterion = useAppStore((state) => state.removeCriterion)
  const [sites, setSites] = useState<SiteView[]>([])
  const [selectedSiteId, setSelectedSiteId] = useState<string | null>(null)
  const [isPreview, setIsPreview] = useState(false)
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [siteDetailState, setSiteDetailState] = useState<SiteDetailLoadState | null>(null)

  const selectedSite = sites.find((site) => site.id === selectedSiteId) ?? null
  const selectedModeDetails = modes.find((mode) => mode.id === selectedMode)
  const selectedSiteDetailState =
    siteDetailState?.siteId === selectedSiteId ? siteDetailState : null
  const siteDetail =
    selectedSiteDetailState && 'detail' in selectedSiteDetailState
      ? selectedSiteDetailState.detail
      : null
  const detailError =
    selectedSiteDetailState && 'error' in selectedSiteDetailState
      ? selectedSiteDetailState.error
      : null
  const detailLoading =
    !isPreview && selectedSiteId !== null && selectedSiteDetailState === null

  const rankedSites = useMemo(
    () =>
      [...sites].sort((a, b) => {
        if (a.excluded && !b.excluded) return 1
        if (!a.excluded && b.excluded) return -1
        if (a.total === null && b.total === null) return 0
        if (a.total === null) return 1
        if (b.total === null) return -1
        return b.total - a.total
      }),
    [sites],
  )

  useEffect(() => {
    if (isPreview || !selectedSiteId) return

    const controller = new AbortController()

    getSiteDetails(selectedSiteId, controller.signal)
      .then((detail) => setSiteDetailState({ siteId: selectedSiteId, detail }))
      .catch((detailRequestError: unknown) => {
        if (!controller.signal.aborted) {
          setSiteDetailState({
            siteId: selectedSiteId,
            error:
              detailRequestError instanceof Error
                ? detailRequestError.message
                : 'Impossible de charger la fiche du site.',
          })
        }
      })

    return () => controller.abort()
  }, [isPreview, selectedSiteId])

  function buildCustomCriteria(): Criterion[] {
    const seenParams = new Set<ParamId>()
    return criteriaDraft.map((draft, index) => {
      if (seenParams.has(draft.param)) {
        throw new Error(`Le paramètre « ${draft.param} » est sélectionné plusieurs fois.`)
      }
      seenParams.add(draft.param)

      const min = draft.min.trim() === '' ? undefined : Number(draft.min)
      const max = draft.max.trim() === '' ? undefined : Number(draft.max)
      const tolerance = Number(draft.tolerance)
      const weight = Number(draft.weight)

      if (
        (min !== undefined && !Number.isFinite(min)) ||
        (max !== undefined && !Number.isFinite(max)) ||
        !Number.isFinite(tolerance) ||
        !Number.isFinite(weight)
      ) {
        throw new Error(`Vérifiez les valeurs du critère ${index + 1}.`)
      }
      if (min === undefined && max === undefined) {
        throw new Error(`Ajoutez une borne minimale ou maximale au critère ${index + 1}.`)
      }
      if (min !== undefined && max !== undefined && min > max) {
        throw new Error(`La borne minimale dépasse la borne maximale au critère ${index + 1}.`)
      }
      if (tolerance < 0 || weight <= 0) {
        throw new Error(`La tolérance doit être positive et le poids supérieur à 0 (critère ${index + 1}).`)
      }

      return { param: draft.param, min, max, tolerance, weight }
    })
  }

  async function handleAnalyze() {
    setError(null)
    setSites([])
    setSelectedSiteId(null)
    setSiteDetailState(null)
    setIsPreview(false)
    setIsLoading(true)

    try {
      const request =
        selectedMode === 'custom'
          ? { criteria: buildCustomCriteria(), bareSoilOnly }
          : selectedMode === 'calibration' && calibrationInstrument !== 'all'
            ? {
              criteria: calibrationCriteria
                .filter((criterion) => criterion.group === calibrationInstrument)
                .map(({ group: _group, ...criterion }) => criterion),
                bareSoilOnly,
              }
            : { mode: selectedMode, bareSoilOnly }
      const response = await analyzeSites(request)
      setSites(response.sites)
      setSelectedSiteId(response.sites[0]?.id ?? null)
    } catch (analysisError) {
      setError(
        analysisError instanceof Error
          ? analysisError.message
          : 'Une erreur inconnue est survenue pendant l’analyse.',
      )
    } finally {
      setIsLoading(false)
    }
  }

  function showFixturePreview(
    bareSoilFilter = bareSoilOnly,
  ) {
    const previewSites = fixtureSites.map((site) => {
      const result = toFixtureResult(site)
      if (!bareSoilFilter) return { ...result, excluded: undefined }
      return result
    })
    setSites(previewSites)
    setSelectedSiteId(previewSites[0]?.id ?? null)
    setIsPreview(true)
    setError(null)
  }

  function handleBareSoilToggle(enabled: boolean) {
    setBareSoilOnly(enabled)
    if (isPreview) {
      showFixturePreview(enabled)
      return
    }

    setSites([])
    setSelectedSiteId(null)
    setSiteDetailState(null)
    setError(null)
  }

  function handleCalibrationInstrumentChange(
    instrument: CalibrationInstrument | 'all',
  ) {
    setCalibrationInstrument(instrument)
    setSites([])
    setSelectedSiteId(null)
    setSiteDetailState(null)
    setIsPreview(false)
    setError(null)
  }

  return (
    <main className="app-shell">
      <header className="topbar">
        <a className="brand" href="/" aria-label="Cyber&Space Montréal, accueil">
          <span className="brand-mark" aria-hidden="true">C</span>
          <span>
            <strong>CYBER&SPACE</strong>
            <small>MONTRÉAL · SPACE APPS 2026</small>
          </span>
        </a>
        <div className="topbar-status">
          <span className="status-dot" />
          <span>EXPLORATION TERRE ↔ LUNE</span>
        </div>
      </header>

      <section className="intro">
        <div className="eyebrow"><span>MISSION 01</span> ANALOGUES TERRESTRES</div>
        <h1>La Lune commence <span>ici, sur Terre.</span></h1>
        <p>
          Comparez des environnements terrestres aux conditions du pôle Sud lunaire
          et trouvez les meilleurs terrains d’essai pour les futures missions.
        </p>
      </section>

      <section className="workspace">
        <aside className="control-panel">
          <div className="panel-heading">
            <div>
              <span className="section-index">01 / ANALYSE</span>
              <h2>Choisir une mission</h2>
            </div>
            <span className="step-count">1—2</span>
          </div>

          <div className="mode-list" role="group" aria-label="Mode d’analyse">
            {modes.map((mode) => (
              <button
                className={`mode-option ${selectedMode === mode.id ? 'is-selected' : ''}`}
                disabled={isLoading}
                key={mode.id}
                onClick={() => {
                  setSelectedMode(mode.id)
                  setSites([])
                  setSelectedSiteId(null)
                  setSiteDetailState(null)
                  setIsPreview(false)
                  setError(null)
                }}
                aria-pressed={selectedMode === mode.id}
                type="button"
              >
                <span className="mode-number">{mode.number}</span>
                <span className="mode-copy">
                  <strong>{mode.title}</strong>
                  <small>{mode.description}</small>
                </span>
                <span className="radio-indicator" />
              </button>
            ))}
          </div>

          {selectedMode === 'calibration' && (
            <label className="filter-control">
              <span>Filtrer par instrument</span>
              <select
                onChange={(event) =>
                  handleCalibrationInstrumentChange(
                    calibrationInstruments.find(
                      (instrument) => instrument.id === event.target.value,
                    )?.id ?? 'all',
                  )
                }
                value={calibrationInstrument}
              >
                <option value="all">Tous les instruments</option>
                {calibrationInstruments.map((instrument) => (
                  <option key={instrument.id} value={instrument.id}>
                    {instrument.label}
                  </option>
                ))}
              </select>
              <small>Le score sera calculé sur les critères de l’instrument choisi.</small>
            </label>
          )}

          <label className="bare-soil-toggle">
            <input
              checked={bareSoilOnly}
              onChange={(event) => handleBareSoilToggle(event.target.checked)}
              type="checkbox"
            />
            <span>
              <strong>Exclure les sites végétalisés</strong>
              <small>
                Filtre sol nu (NDVI ≤ 0,1). Désactivez-le pour inclure ces sites.
              </small>
            </span>
          </label>

          {selectedMode === 'custom' && (
            <div className="criteria-editor">
              <div className="criteria-title">
                <strong>Vos critères</strong>
                <button
                  className="text-button"
                  disabled={criteriaDraft.length >= parameterCatalog.length}
                  onClick={addCriterion}
                  type="button"
                >
                  + Ajouter
                </button>
              </div>
              {criteriaDraft.map((criterion, index) => (
                <div className="criterion-row" key={`criterion-${index}`}>
                  <label>
                    <span>Paramètre</span>
                    <select
                      value={criterion.param}
                      onChange={(event) =>
                        updateCriterion(index, {
                          param: parameterCatalog.find(
                            (parameter) => parameter.id === event.target.value,
                          )?.id ?? criterion.param,
                        })
                      }
                    >
                      {parameterCatalog.map((parameter) => (
                        <option
                          disabled={criteriaDraft.some(
                            (other, otherIndex) =>
                              otherIndex !== index && other.param === parameter.id,
                          )}
                          key={parameter.id}
                          value={parameter.id}
                        >
                          {parameter.label}
                        </option>
                      ))}
                    </select>
                  </label>
                  <div className="criterion-inputs">
                    <label>
                      <span>Min.</span>
                      <input
                        inputMode="decimal"
                        onChange={(event) =>
                          updateCriterion(index, { min: event.target.value })
                        }
                        placeholder="—"
                        value={criterion.min}
                      />
                    </label>
                    <label>
                      <span>Max.</span>
                      <input
                        inputMode="decimal"
                        onChange={(event) =>
                          updateCriterion(index, { max: event.target.value })
                        }
                        placeholder="—"
                        value={criterion.max}
                      />
                    </label>
                    <label>
                      <span>Tolérance</span>
                      <input
                        inputMode="decimal"
                        onChange={(event) =>
                          updateCriterion(index, { tolerance: event.target.value })
                        }
                        value={criterion.tolerance}
                      />
                    </label>
                    <label>
                      <span>Poids</span>
                      <input
                        inputMode="decimal"
                        onChange={(event) =>
                          updateCriterion(index, { weight: event.target.value })
                        }
                        value={criterion.weight}
                      />
                    </label>
                  </div>
                  {criteriaDraft.length > 1 && (
                    <button
                      className="remove-criterion"
                      onClick={() =>
                        removeCriterion(index)
                      }
                      type="button"
                      aria-label={`Supprimer le critère ${index + 1}`}
                    >
                      ×
                    </button>
                  )}
                </div>
              ))}
            </div>
          )}

          <div className="actions">
            <button
              className="primary-button"
              disabled={isLoading}
              onClick={handleAnalyze}
              type="button"
            >
              {isLoading ? 'Analyse en cours…' : 'Lancer l’analyse'}
              {!isLoading && <span aria-hidden="true">↗</span>}
            </button>
            <button
              className="preview-button"
              disabled={isLoading}
              onClick={() => showFixturePreview()}
              type="button"
            >
              Charger l’aperçu local <span>↗</span>
            </button>
          </div>
          {error && <div className="error-message" role="alert">{error}</div>}

          <div className="panel-footnote">
            <span className="info-mark">i</span>
            Les scores seront calculés par l’API. L’aperçu local affiche uniquement
            des valeurs brutes de développement.
          </div>
        </aside>

        <section className="results-panel" aria-label="Résultats de l’analyse">
          <div className="results-heading">
            <div>
              <span className="section-index">02 / EXPLORATION</span>
              <h2>
                {selectedModeDetails?.title ?? 'Résultats'}
                {selectedMode === 'calibration' && calibrationInstrument !== 'all'
                  ? ` · ${calibrationInstruments.find((item) => item.id === calibrationInstrument)?.label}`
                  : ''}
              </h2>
            </div>
            <div className="results-meta">
              {sites.length > 0 ? `${sites.length} SITES` : 'EN ATTENTE'}
              <span className="meta-divider" />
              <span>TERRE</span>
            </div>
          </div>

          {isPreview && (
            <div className="fixture-warning" role="status">
              <span className="warning-icon">!</span>
              <div>
                <strong>Aperçu de développement — ne pas utiliser en démo</strong>
                <p>
                  Valeurs de test, aucun score calculé. Les sites au NDVI supérieur à
                  0,1 sont marqués comme exclus lorsque le filtre est actif.
                </p>
              </div>
            </div>
          )}

          {!isPreview && sites.length === 0 && !error && (
            <div className="empty-state">
              <div className="empty-orbit" aria-hidden="true">
                <span className="orbit orbit-one" />
                <span className="orbit orbit-two" />
                <span className="orbit-core" />
              </div>
              <strong>Votre prochaine destination commence par une question.</strong>
              <p>Choisissez un mode, puis lancez l’analyse pour classer les sites.</p>
              <span className="empty-hint">OU CHARGEZ L’APERÇU LOCAL POUR EXPLORER L’INTERFACE</span>
            </div>
          )}

          {error && (
            <div className="api-error-state">
              <span className="error-symbol">!</span>
              <div>
                <strong>Impossible de joindre le service d’analyse</strong>
                <p>{error}</p>
                <small>Vérifiez que l’API est lancée, ou utilisez l’aperçu local.</small>
              </div>
            </div>
          )}

          {sites.length > 0 && (
            <div className="results-layout">
              <div className="map-frame">
                <MapContainer
                  center={[35, -35]}
                  className="site-map"
                  scrollWheelZoom
                  zoom={2}
                >
                  <MapResizeHandler />
                  <FitMapToSites sites={rankedSites} />
                  <TileLayer
                    attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
                    url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
                  />
                  {rankedSites.map((site) => (
                    <CircleMarker
                      center={[site.lat, site.lon]}
                      eventHandlers={{ click: () => setSelectedSiteId(site.id) }}
                      key={site.id}
                      pathOptions={{
                        color: selectedSiteId === site.id
                          ? '#ffffff'
                          : scoreColor(site.total, site.role, Boolean(site.excluded)),
                        fillColor: scoreColor(site.total, site.role, Boolean(site.excluded)),
                        fillOpacity: 0.9,
                        weight: selectedSiteId === site.id ? 3 : 1,
                      }}
                      radius={selectedSiteId === site.id ? 10 : 7}
                    >
                      <Popup>
                        <strong>{site.name}</strong>
                        <br />
                        {site.excluded
                          ? 'Exclu : végétation'
                          : site.total === null
                            ? roleLabel(site.role)
                            : `Score : ${site.total}/100`}
                      </Popup>
                    </CircleMarker>
                  ))}
                </MapContainer>
                <div className="map-legend">
                  {isPreview ? (
                    <>
                      <span><i className="legend-dot blue" /> Analogue connu</span>
                      <span><i className="legend-dot yellow" /> Site candidat</span>
                      <span><i className="legend-dot red" /> Témoin négatif</span>
                    </>
                  ) : (
                    <>
                      <span><i className="legend-dot green" /> Score élevé</span>
                      <span><i className="legend-dot yellow" /> À explorer</span>
                      <span><i className="legend-dot red" /> Score faible</span>
                    </>
                  )}
                  {rankedSites.some((site) => site.excluded) && (
                    <span><i className="legend-dot excluded" /> Exclu : végétation</span>
                  )}
                </div>
              </div>

              <div className="site-list">
                <div className="list-heading">
                  <span>{isPreview ? 'SITES DE L’APERÇU' : 'SITES CLASSÉS'}</span>
                  <span>{sites.length.toString().padStart(2, '0')}</span>
                </div>
                {rankedSites.map((site, index) => (
                  <button
                    className={`site-card ${selectedSiteId === site.id ? 'is-active' : ''} ${site.excluded ? 'is-excluded' : ''}`}
                    key={site.id}
                    onClick={() => setSelectedSiteId(site.id)}
                    type="button"
                  >
                    <span className="site-rank">{(index + 1).toString().padStart(2, '0')}</span>
                    <span className="site-card-copy">
                      <strong>{site.name}</strong>
                      <small>
                        {site.excluded ? 'Exclu : végétation' : roleLabel(site.role)}
                      </small>
                    </span>
                    {site.excluded ? (
                      <span className="excluded-label">EXCLU</span>
                    ) : (
                      <span className="site-score">
                        {site.total === null ? '—' : `${Math.round(site.total)}`}
                        {site.total !== null && <small>/100</small>}
                      </span>
                    )}
                  </button>
                ))}
              </div>
            </div>
          )}

          {selectedSite && (
            <section className="site-detail">
              <div className="detail-heading">
                <div>
                  <span className="section-index">
                    FICHE DU SITE ·{' '}
                    {selectedSite.excluded
                      ? 'EXCLU : VÉGÉTATION'
                      : roleLabel(selectedSite.role).toUpperCase()}
                  </span>
                  <h3>{selectedSite.name}</h3>
                </div>
                <span className="coordinates">
                  {selectedSite.lat.toFixed(2)}° / {selectedSite.lon.toFixed(2)}°
                </span>
              </div>
              {selectedSite.excluded && (
                <p className="exclusion-notice">
                  Ce site est exclu du classement parce que son indice de végétation
                  dépasse le seuil autorisé.
                </p>
              )}
              {!selectedSite.excluded && selectedSite.criteria.length > 0 ? (
                <div className="criterion-results">
                  {selectedSite.criteria.map((criterion) => {
                    const parameter = parameterCatalog.find((item) => item.id === criterion.param)
                    return (
                      <div className="criterion-result" key={criterion.param}>
                        <div className="criterion-copy">
                          <span>{parameter?.label ?? criterion.param}</span>
                          <strong>{formatValue(criterion.value, parameter?.unit)}</strong>
                        </div>
                        <div className="criterion-score">
                          <strong>{Math.round(criterion.score * 100)}%</strong>
                          <small>score</small>
                        </div>
                        <span className={`verdict verdict-${criterion.verdict}`}>
                          {verdictLabel(criterion.verdict)}
                        </span>
                      </div>
                    )
                  })}
                </div>
              ) : null}
              {isPreview && selectedSite.values ? (
                <div className="raw-values">
                  {Object.entries(selectedSite.values)
                    .map(([paramId, value]) => {
                      const parameter = parameterCatalog.find((item) => item.id === paramId)
                      return (
                        <div className="raw-value" key={paramId}>
                          <span>{parameter?.label ?? paramId}</span>
                          <strong>{formatValue(value, parameter?.unit)}</strong>
                        </div>
                      )
                    })}
                </div>
              ) : !isPreview && detailLoading ? (
                <p className="no-site-data">Chargement des valeurs et des sources…</p>
              ) : !isPreview && detailError ? (
                <p className="detail-error" role="alert">
                  Fiche détaillée indisponible : {detailError}
                </p>
              ) : !isPreview && siteDetail ? (
                <div className="raw-values">
                  {Object.entries(siteDetail.values).map(([paramId, value]) => {
                    const parameter = parameterCatalog.find((item) => item.id === paramId)
                    return (
                      <div className="raw-value" key={paramId}>
                        <span>{parameter?.label ?? paramId}</span>
                        <strong>{formatValue(value, parameter?.unit)}</strong>
                      </div>
                    )
                  })}
                </div>
              ) : (
                <p className="no-site-data">Aucune valeur brute n’a été renvoyée pour ce site.</p>
              )}
            </section>
          )}
        </section>
      </section>

      <footer className="page-footer">
        <span>CYBER&SPACE MONTRÉAL</span>
        <span>UN PROJET NASA SPACE APPS CHALLENGE 2026</span>
        <span>TERRE · LUNE · EXPLORATION</span>
      </footer>
    </main>
  )
}

export default App
