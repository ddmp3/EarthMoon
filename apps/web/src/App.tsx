import { useCallback, useEffect, useState } from 'react'
import {
  analyzeSites,
  getEarthLimits,
  getModeCriteria,
  getSiteDetails,
  getSources,
  getVisualManifest,
  type Criterion,
  type DataSource,
  type EarthLimit,
  type ParamId,
  type SiteDetail as SiteDetailData,
  type SiteResult,
  type VisualManifest,
} from './api'
import { Home } from './components/Home'
import { Mission } from './components/Mission'
import { SiteDetail } from './components/SiteDetail'
import { FR_SOURCES } from './content-fr'
import { useT, type Lang, type Texts } from './i18n'
import { MISSION_ORDER } from './shared'
import { SiteV3Section } from './v3/MissionV3'
import { DataMethod } from './v3/panels'
import { V3_TEXTS } from './v3/text'
import { homeFigures } from './v3/model'
import { useV3 } from './v3/useV3'
import { useAppStore, type Body, type CriterionDraft, type SelectedMode } from './store'

/** Mode 4 criteria entered in the form; throws a readable error if the input is invalid. */
function buildCustomCriteria(drafts: CriterionDraft[], t: Texts): Criterion[] {
  const seen = new Set<ParamId>()
  return drafts.map((draft) => {
    if (seen.has(draft.param)) throw new Error(t.customErrors.duplicate)
    seen.add(draft.param)
    const min = draft.min.trim() === '' ? undefined : Number(draft.min.replace(',', '.'))
    const max = draft.max.trim() === '' ? undefined : Number(draft.max.replace(',', '.'))
    const tolerance = Number(draft.tolerance.replace(',', '.'))
    const weight = Number(draft.weight.replace(',', '.'))
    if (min === undefined && max === undefined) throw new Error(t.customErrors.range)
    const bad = (n: number | undefined) => n !== undefined && !Number.isFinite(n)
    if (bad(min) || bad(max) || !Number.isFinite(tolerance) || !Number.isFinite(weight) || tolerance <= 0 || weight <= 0) {
      throw new Error(t.customErrors.number)
    }
    if (min !== undefined && max !== undefined && min > max) throw new Error(t.customErrors.order)
    return { param: draft.param, ...(min !== undefined ? { min } : {}), ...(max !== undefined ? { max } : {}), tolerance, weight }
  })
}

/** Shareable address: #mission or #mission/site (for example #colony/tunnunik). */
/** Home of Mars: the whole site in its Mars mode (T45c). */
const MARS_HOME = '#mars-home'

function parseHash(): { mode: SelectedMode | null; site: string | null; body: Body | null } {
  if (window.location.hash === '#discover') return { mode: 'custom', site: null, body: 'moon' } // the v3 map now lives in mission 4
  if (window.location.hash === MARS_HOME) return { mode: null, site: null, body: 'mars' }
  const [mode, site] = window.location.hash.replace(/^#/, '').split('/')
  if (mode === 'mars') return { mode: 'mars', site: site || null, body: 'mars' }
  return MISSION_ORDER.includes(mode as SelectedMode) ? { mode: mode as SelectedMode, site: site || null, body: 'moon' } : { mode: null, site: null, body: null }
}

function App() {
  const { t, lang } = useT()
  const { criteriaDraft, bareSoilOnly, calibrationInstrument, setLang } = useAppStore()

  useEffect(() => {
    document.documentElement.lang = lang
  }, [lang])
  const [mode, setMode] = useState<SelectedMode | null>(() => parseHash().mode)
  // v3 scenario of each mission: robotics = B, colony = A, free criteria = the one picked in its search; calibration has none yet.
  const [customScenario, setCustomScenario] = useState('B')
  // Mars reads the current Mars release, scenario D. The body switch changes the whole site (T45c).
  const scenarioId = mode === 'robotics' ? 'B' : mode === 'colony' ? 'A' : mode === 'custom' ? customScenario : mode === 'mars' ? 'D' : null
  const storeBody = useAppStore((s) => s.body)
  const setBody = useAppStore((s) => s.setBody)
  const body: Body = mode === 'mars' ? 'mars' : mode ? 'moon' : (parseHash().body ?? storeBody)
  useEffect(() => setBody(body), [body, setBody])
  useEffect(() => {
    document.documentElement.dataset.body = body
  }, [body])
  const v3 = useV3(scenarioId, body)
  const [siteMethod, setSiteMethod] = useState(false)
  const [sites, setSites] = useState<SiteResult[]>([])
  const [selectedId, setSelectedId] = useState<string | null>(() => parseHash().site)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [builderError, setBuilderError] = useState<string | null>(null)
  const [detail, setDetail] = useState<{ id: string; data?: SiteDetailData; error?: string } | null>(null)
  const [manifest, setManifest] = useState<VisualManifest | null>(null)
  const [sources, setSources] = useState<DataSource[]>([])
  const [limits, setLimits] = useState<EarthLimit[]>([])

  // Reference data: loaded once; if it fails, the page stays usable.
  useEffect(() => {
    let active = true
    getVisualManifest().then((m) => active && setManifest(m)).catch(() => undefined)
    getSources().then((s) => active && setSources(s)).catch(() => undefined)
    getEarthLimits().then((l) => active && setLimits(l)).catch(() => undefined)
    return () => {
      active = false
    }
  }, [])

  const run = useCallback(
    async (target: Exclude<SelectedMode, 'mars'>) => {
      setError(null)
      setBuilderError(null)
      let request: Parameters<typeof analyzeSites>[0]
      try {
        if (target === 'custom') {
          request = { criteria: buildCustomCriteria(criteriaDraft, t), bareSoilOnly }
        } else if (target === 'calibration' && calibrationInstrument !== 'all') {
          const all = await getModeCriteria('calibration')
          request = {
            criteria: all.filter((c) => c.group === calibrationInstrument).map(({ group: _group, ...c }) => c),
            bareSoilOnly,
          }
        } else {
          request = { mode: target, bareSoilOnly }
        }
      } catch (e) {
        setBuilderError(e instanceof Error ? e.message : String(e))
        return
      }
      setLoading(true)
      try {
        const response = await analyzeSites(request)
        setSites(response.sites)
        setSelectedId((current) => (current && response.sites.some((s) => s.id === current) ? current : (response.sites[0]?.id ?? null)))
      } catch (e) {
        setSites([])
        setError(e instanceof Error ? e.message : String(e))
      } finally {
        setLoading(false)
      }
    },
    [bareSoilOnly, calibrationInstrument, criteriaDraft, t],
  )

  // Predefined modes re-run on their own when a setting changes; mode 4 waits for the button.
  useEffect(() => {
    if (mode === 'mars') setSites([])                       // no v2 site ranking for Mars: zones only
    else if (mode && mode !== 'custom') void run(mode)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [mode, bareSoilOnly, calibrationInstrument])

  useEffect(() => {
    if (!selectedId) return
    const controller = new AbortController()
    getSiteDetails(selectedId, controller.signal)
      .then((data) => setDetail({ id: selectedId, data }))
      .catch((e: unknown) => {
        if (!controller.signal.aborted) setDetail({ id: selectedId, error: e instanceof Error ? e.message : String(e) })
      })
    return () => controller.abort()
  }, [selectedId])

  // State -> address. Changing screen (home <-> mission) adds a history entry, so the browser Back button
  // returns to the missions; selecting another site only replaces the current entry.
  useEffect(() => {
    const hash = mode ? `#${mode}${selectedId ? `/${selectedId}` : ''}` : body === 'mars' ? MARS_HOME : ''
    if (window.location.hash === hash) return
    const url = hash || window.location.pathname + window.location.search
    if (parseHash().mode !== mode) window.history.pushState(null, '', url)
    else window.history.replaceState(null, '', url)
  }, [mode, selectedId, body])

  // Address -> state: Back and Forward buttons, a pasted link, a bookmark opened in the same tab.
  useEffect(() => {
    const onAddressChange = () => {
      const next = parseHash()
      setMode((current) => {
        if (current !== next.mode) {
          setSites([])
          setError(null)
          setBuilderError(null)
        }
        return next.mode
      })
      setSelectedId(next.site)
      useAppStore.getState().setBody(next.body ?? 'moon')
    }
    window.addEventListener('hashchange', onAddressChange)
    window.addEventListener('popstate', onAddressChange)
    return () => {
      window.removeEventListener('hashchange', onAddressChange)
      window.removeEventListener('popstate', onAddressChange)
    }
  }, [])

  const pick = (next: SelectedMode) => {
    setSites([])
    setSelectedId(null)
    setError(null)
    setBuilderError(null)
    setMode(next)
    window.scrollTo({ top: 0 })
  }

  /** A Martian terrain of the Mars home: the Mars mission, on that target. */
  const pickMars = (target: string) => {
    pick('mars')
    v3.setEnv(target)
  }

  /** The body switch: the home of the other body, the whole site in its mode. */
  const switchBody = (next: Body) => {
    setBody(next)
    setSites([])
    setSelectedId(null)
    setMode(null)
    window.history.pushState(null, '', next === 'mars' ? MARS_HOME : window.location.pathname + window.location.search)
    window.scrollTo({ top: 0 })
  }

  const selected = sites.find((site) => site.id === selectedId) ?? null
  const current = detail && detail.id === selectedId ? detail : null

  return (
    <div className="app">
      <header className="topbar">
        <button className="brand" onClick={() => setMode(null)} type="button">
          <span className="brand-mark" aria-hidden="true" />
          <span>
            <strong>{t.brand}</strong>
            <small>{t.tagline}</small>
          </span>
        </button>
        <div className="topbar-right">
          <span className="topbar-target">{body === 'mars' ? t.targetMars : t.target}</span>
          <div aria-label={t.languageSwitch} className="lang-switch" role="group">
            {(['en', 'fr'] as Lang[]).map((code) => (
              <button aria-pressed={lang === code} key={code} lang={code} onClick={() => setLang(code)} type="button">
                {code.toUpperCase()}
              </button>
            ))}
          </div>
        </div>
      </header>

      <main>
        {mode === null ? (
          <Home body={body} figures={homeFigures(v3, body, lang, t.figureLabels)} onBody={switchBody} onPick={pick} onPickMars={pickMars} />
        ) : (
          <Mission
            key={mode}
            builderError={builderError}
            error={error}
            loading={loading}
            manifest={manifest}
            mode={mode}
            onBack={() => setMode(null)}
            onRun={() => mode !== 'mars' && void run(mode)}
            onSelect={setSelectedId}
            onScenario={setCustomScenario}
            selectedId={selectedId}
            sites={sites}
            v3={v3}
          >
            {selected && (
              <SiteDetail
                detail={current?.data ?? null}
                detailError={current?.error ?? null}
                limits={limits}
                manifest={manifest}
                rank={sites.findIndex((site) => site.id === selected.id) + 1}
                rankedTotal={sites.filter((site) => !site.excluded).length}
                site={selected}
                sources={sources}
                v3Section={<SiteV3Section onMethod={() => setSiteMethod(true)} release={v3.release?.release ?? null} scenario={v3.scenario} site={v3.sites?.[selected.id]} />}
                visual={manifest?.sites[selected.id]}
              />
            )}
          </Mission>
        )}

        <section className="credits">
          {body === 'mars' && v3.method && (
            <div>
              <h3>{t.sourcesTitle}</h3>
              <ul>
                {v3.method.sources.map((source) => (
                  <li key={source.id}>
                    <a href={source.url} rel="noopener noreferrer" target="_blank">{source.product ?? source.id}</a>
                    {source.producer ? ` · ${source.producer}` : ''}.{' '}
                    {source.licence && <small>{source.licence}</small>}
                  </li>
                ))}
              </ul>
            </div>
          )}
          {body === 'moon' && sources.length > 0 && (
            <div>
              <h3>{t.sourcesTitle}</h3>
              <ul>
                {sources.map((source) => (
                  <li key={source.id}>
                    <a href={source.url} rel="noopener noreferrer" target="_blank">
                      {(lang === 'fr' ? FR_SOURCES[source.id]?.name : undefined) ?? source.name}
                    </a>{' '}
                    · {source.provider} · {source.body === 'moon' ? t.moon : t.earth}.{' '}
                    <small>{(lang === 'fr' ? FR_SOURCES[source.id]?.terms : undefined) ?? source.terms}</small>
                  </li>
                ))}
              </ul>
            </div>
          )}
          <div>
            <h3>{t.imagesTitle}</h3>
            <p>{t.imagesText}</p>
          </div>
        </section>
      </main>

      {siteMethod && v3.method && (
        <DataMethod cannotAssess={v3.scenario?.cannot_assess ?? []} coverage={v3.coverage} onClose={() => setSiteMethod(false)}
          processing={v3.method.processing} sources={v3.method.sources} t={V3_TEXTS[lang]} />
      )}
      <footer className="footer">{t.footer}</footer>
    </div>
  )
}

export default App
