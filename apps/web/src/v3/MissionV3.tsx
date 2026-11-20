import { useState } from 'react'
import { useAppStore } from '../store'
import { v3 as v3api, type CellProps, type QueryResult, type Scenario } from './api'
import { cellState, cividis, geologyText, layerList, legendRows } from './model'
import { coverageMeaning, requirementText, scenarioText } from './content'
import { Patterns } from './panels'
import { targetName, V3_TEXTS } from './text'
import type { SiteV3, V3State } from './useV3'
import './v3.css'

const two = (v: number | null | undefined) => (v === null || v === undefined ? '—' : v.toFixed(2))

function useV3Texts() {
  const lang = useAppStore((s) => s.lang)
  return { t: V3_TEXTS[lang], lang }
}

/** v3 settings in the mission's control bar: lunar environment, coverage overlay, Data and method. */
export function V3Controls({ v, overlay, onOverlay, onMethod, scenarioPicker = false, onScenario, layer, onLayer }: {
  layer: 'typicality' | 'geology'
  onLayer: (l: 'typicality' | 'geology') => void
  v: V3State
  overlay: boolean
  onOverlay: (on: boolean) => void
  onMethod: () => void
  scenarioPicker?: boolean
  onScenario?: (id: string) => void
}) {
  const { t, lang } = useV3Texts()
  const s = v.scenario
  return (
    <>
      {scenarioPicker && onScenario && (
        <label className="field">
          <span>{t.scenario}</span>
          <select id="v3-scenario" onChange={(e) => onScenario(e.target.value)} value={s?.id ?? ''}>
            {v.scenarios.map((x) => (
              <option key={x.id} value={x.id}>{x.id} · {scenarioText(x.id, lang, x).name}</option>
            ))}
          </select>
        </label>
      )}
      {s && (
        <label className="field">
          <span>{t.environment}</span>
          <select id="v3-env" onChange={(e) => v.setEnv(e.target.value)} value={v.env}>
            {s.targets.map((id) => (
              <option disabled={!s.assessed_targets.includes(id)} key={id} value={id}>
                {targetName(t, id)}{s.assessed_targets.includes(id) ? '' : ` (${t.notComparable})`}
              </option>
            ))}
          </select>
        </label>
      )}
      {s && (
        <label className="field">
          <span>{t.layerPick}</span>
          <select id="v3-layer" onChange={(e) => onLayer(e.target.value === 'geology' ? 'geology' : 'typicality')} value={layer === 'geology' ? 'geology' : 'topography'}>
            {layerList(t, v.available).map((l) => (
              <option disabled={!l.enabled} key={l.id} value={l.id}>{l.label}{l.reason ? ` (${l.reason})` : ''}</option>
            ))}
          </select>
        </label>
      )}
      {s && (
        <label className="check">
          <input checked={overlay} id="v3-overlay" onChange={(e) => onOverlay(e.target.checked)} type="checkbox" />
          <span>
            {t.overlay} <small>{t.overlayHint}</small>
          </span>
        </label>
      )}
      {s && (
        <button className="ghost" onClick={onMethod} type="button">
          {t.dataMethod}
        </button>
      )}
    </>
  )
}

/** One line on the validity of the data shown (ADR-009), under the controls. */
export function V3StatusLine({ v }: { v: V3State }) {
  const { t } = useV3Texts()
  if (!v.status) return null
  const failed = v.status.validity.checks.filter((c) => c.pass !== true).map((c) => t.checkName[c.check] ?? c.check)
  const fmt = v.status.validity.state === 'validated' ? t.validity.validated : t.validity.not_validated
  const d = /^(\d{4})-(\d{2})-(\d{2})/.exec(v.status.validity.published)
  return (
    <p className={`v3-statusline v3-status-${v.status.validity.state}`} role="status">
      <strong>{fmt(v.status.validity.protocol, v.status.validity.release, d ? `${d[3]}/${d[2]}/${d[1]}` : v.status.validity.published)}</strong>
      {failed.length > 0 && <span> · {t.validity.failing(failed.join(', '))}</span>}
    </p>
  )
}

export type Tab = 'sites' | 'zones' | 'results'

export function RankTabs({ tab, onTab, counts }: { tab: Tab; onTab: (t: Tab) => void; counts: Partial<Record<Tab, number | null>> }) {
  const { t, lang } = useV3Texts()
  const label: Record<Tab, string> = { sites: t.tabKnown, zones: t.tabZones, results: t.tabResults }
  const fmt = (n: number) => n.toLocaleString(lang === 'fr' ? 'fr-CA' : 'en-CA')
  return (
    <div className="rank-tabs" role="tablist">
      {(Object.keys(counts) as Tab[]).map((k) => (
        <button aria-selected={tab === k} className={`chip${tab === k ? ' chip-on' : ''}`} key={k} onClick={() => onTab(k)} role="tab" type="button">
          {label[k]}{counts[k] != null ? ` · ${fmt(counts[k] as number)}` : ''}
        </button>
      ))}
    </div>
  )
}

/** Small mark on a ranked site: the v3 typicality of its cell for the chosen environment, or why there is none. */
export function SiteV3Chip({ site, env }: { site: SiteV3 | undefined; env: string }) {
  const { t } = useV3Texts()
  if (!site) return null
  const c = site.values?.[env]
  if (!c) return <span className="v3-chip v3-chip-none" title={t.notAssessed}>{t.v3Badge} —</span>
  const st = cellState(c, t)
  if (st.state !== 'evaluated' || c.typicality.median === null) {
    return <span className="v3-chip v3-chip-none" title={st.text}>{t.v3Badge} {st.state === 'masked' ? '▨' : '—'}</span>
  }
  return (
    <span className="v3-chip" style={{ borderColor: cividis(c.typicality.median) }} title={`${t.layer.topography} ${two(c.typicality.median)} · ${t.confidenceLabel} ${c.confidence ?? '—'}`}>
      {t.v3Badge} {two(c.typicality.median)}
    </span>
  )
}

/** Section of the site card: what run-002 says about the cell holding the site, per lunar environment. */
export function SiteV3Section({ site, scenario, release, onMethod }: {
  site: SiteV3 | undefined
  scenario: Scenario | null
  release: string | null
  onMethod: () => void
}) {
  const { t, lang } = useV3Texts()
  if (!scenario || !site) return null
  const rows = scenario.assessed_targets.map((env) => ({ env, c: site.values?.[env] ?? null }))
  return (
    <section className="detail-section v3-site" aria-labelledby="v3-site-title">
      <Patterns />
      <h3 id="v3-site-title">{t.v3Here}</h3>
      <p className="lead">{t.v3HereLead} {release ?? '—'}).</p>
      {!site.cell ? (
        <p className="note">{t.notAssessed}</p>
      ) : (
        <div className="table-scroll">
          <table className="scorecard v3-site-table">
            <thead>
              <tr>
                <th scope="col">{t.environment}</th>
                <th scope="col">{t.legendTitle}</th>
                <th scope="col">{t.iqr}</th>
                <th scope="col">n ({t.windows})</th>
                <th scope="col">{t.coverageLabel}</th>
                <th scope="col">{t.confidenceLabel}</th>
                <th scope="col">{t.layer.geology}</th>
              </tr>
            </thead>
            <tbody>
              {rows.map(({ env, c }) => {
                const st = c ? cellState(c, t) : null
                const cov = c ? ((t.coverageClass as Record<string, string>)[c.coverage] ?? c.coverage) : '—'
                return (
                  <tr key={env}>
                    <th scope="row">{targetName(t, env)}</th>
                    <td>
                      {c && st?.state === 'evaluated' && c.typicality.median !== null ? (
                        <span className="v3-chip" style={{ borderColor: cividis(c.typicality.median) }}>{two(c.typicality.median)}</span>
                      ) : (
                        <span className="v3-missing-chip">{st?.text ?? t.states.not_evaluated}</span>
                      )}
                    </td>
                    <td>{c ? `${two(c.typicality.p25)}–${two(c.typicality.p75)}` : '—'}</td>
                    <td>{c?.windows.valid ?? '—'}/{c?.windows.total ?? '—'}</td>
                    <td title={c ? coverageMeaning(c.coverage, lang, '') : ''}>{cov}</td>
                    <td>{c?.confidence ? (t.confidenceLevel[c.confidence] ?? c.confidence) : '—'}</td>
                    <td>{geologyText(c?.geology, t) ?? <span className="v3-missing-chip">{t.geologyMissing}</span>}</td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
      )}
      <button className="ghost" onClick={onMethod} type="button">{t.dataMethod}</button>
    </section>
  )
}

/** Zones (or search results) in the ranking panel, in the same rows as the known sites. */
export function ZoneRows({ items, selectedId, onSelect, picked, onPick }: {
  items: { id: string; lat: number; lon: number; value: number; sub: string }[]
  selectedId: string | null
  onSelect: (id: string) => void
  picked?: string[]
  onPick?: (id: string) => void
}) {
  const { t } = useV3Texts()
  if (items.length === 0) return <p className="screening-note">{t.noZone}</p>
  return (
    <ol>
      {items.map((z, i) => (
        <li className="zone-row-wrap" key={z.id}>
          {onPick && picked && (
            <input
              aria-label={`${t.compare} ${t.zone} ${i + 1}`}
              checked={picked.includes(z.id)}
              className="zone-pick"
              disabled={!picked.includes(z.id) && picked.length >= 4}
              onChange={() => onPick(z.id)}
              type="checkbox"
            />
          )}
          <button aria-current={z.id === selectedId} className="rank-row zone-row" onClick={() => onSelect(z.id)} type="button">
            <span className="rank-number">{String(i + 1).padStart(2, '0')}</span>
            <span className="zone-swatch" style={{ background: cividis(z.value) }} />
            <span className="rank-copy">
              <strong>{t.resultCell(z.lat, z.lon)}</strong>
              <small>{z.sub}</small>
            </span>
            <span className="rank-score">{two(z.value)}</span>
          </button>
        </li>
      ))}
    </ol>
  )
}


/** Legend drawn over the mission map: typicality ramp, and the coverage classes with their land share. */
const GEO_SWATCH: Record<number, string> = { 1: 'rgb(0, 158, 115)', 2: 'rgb(86, 180, 233)', 3: 'rgb(120, 126, 140)' }

export function MapLegend({ coverage, overlay, layer = 'typicality', available = ['topography'] }: {
  coverage: V3State['coverage']
  overlay: boolean
  layer?: 'typicality' | 'geology'
  available?: string[]
}) {
  const { t, lang } = useV3Texts()
  const [open, setOpen] = useState(true)
  const stops = Array.from({ length: 11 }, (_, i) => cividis(i / 10))
  return (
    <div className="map-legend">
      <button aria-expanded={open} className="map-legend-toggle" onClick={() => setOpen(!open)} type="button">{t.mapLegend}</button>
      {open && (
        <div className="map-legend-body">
          {layer === 'geology' ? (
            <>
              <strong>{t.geoLegend}</strong>
              <ul aria-label={t.geoLegend} className="v3-legend">
                {[1, 2, 3, 4].map((k) => (
                  <li key={k}>
                    <svg aria-hidden="true" className="legend-swatch" height="14" width="20">
                      <rect fill={GEO_SWATCH[k] ?? '#1d2335'} height="14" width="20" />
                      {k === 4 && <rect fill="url(#pat-dense)" height="14" width="20" />}
                    </svg>
                    <span className="legend-label">{t.geoClass[k]}</span>
                  </li>
                ))}
              </ul>
              <small>{t.geoSource}</small>
            </>
          ) : (
            <>
              <strong>{t.legendTitle}</strong>
              <div aria-hidden="true" className="v3-ramp" style={{ background: `linear-gradient(to right, ${stops.join(', ')})` }} />
              <div className="v3-ramp-ends"><span>0</span><span>1</span></div>
              <small>{t.legendScale}</small>
            </>
          )}
          <ul aria-label={t.layers} className="map-layers">
            {layerList(t, available).map((l) => (
              <li className={l.enabled ? 'on' : 'off'} key={l.id}>{l.label}{l.reason ? ` · ${l.reason}` : ''}</li>
            ))}
          </ul>
          {overlay && coverage && (
            <ul aria-label={t.overlay} className="v3-legend">
              {legendRows(coverage, t).map((r) => (
                <li key={r.id} title={coverageMeaning(r.id, lang, r.meaning)}>
                  <svg aria-hidden="true" className="legend-swatch" height="14" width="20">
                    <rect fill="#1d2335" height="14" width="20" />
                    <rect fill={r.pattern === 'pat-none' ? 'none' : `url(#${r.pattern})`} height="14" stroke="#b9c6e8" strokeOpacity="0.5" width="20" />
                  </svg>
                  <span className="legend-label">{r.label}</span>
                  <span className="legend-share">{r.share == null ? '—' : `${Math.round(r.share * 100)}%`}</span>
                </li>
              ))}
            </ul>
          )}
        </div>
      )}
    </div>
  )
}

const REQS = ['base_slope', 'climbing_limit_lrv', 'climbing_limit_viper'] as const

/** Mission 4: a search over the cells of the whole Earth (POST /api/v3/query), inside the current map view. */
export function V3Search({ v, bbox, onResults, onScenario }: {
  v: V3State
  bbox: [number, number, number, number] | null
  onResults: (r: QueryResult | null) => void
  onScenario: (id: string) => void
}) {
  const { t, lang } = useV3Texts()
  const [minTyp, setMinTyp] = useState('0.8')
  const [minConf, setMinConf] = useState('high')
  const [reqs, setReqs] = useState<string[]>([])
  const [busy, setBusy] = useState(false)
  const [message, setMessage] = useState<string | null>(null)
  const s = v.scenario
  const usable = (s?.requirements ?? []).map((x) => x.id)
  const run = async () => {
    if (!s || !v.env) return
    if (!bbox) {
      setMessage(t.noMapYet)
      return
    }
    const mt = Number(minTyp.replace(',', '.'))
    setBusy(true)
    setMessage(null)
    try {
      const r = await v3api.query({ scenario: s.id, env: v.env, min_typicality: Number.isFinite(mt) ? Math.min(1, Math.max(0, mt)) : 0.8,
        min_confidence: minConf, requirements_met: reqs.filter((r) => usable.includes(r)), bbox: bbox.map((x) => Math.round(x * 1000) / 1000), limit: 100 })
      onResults(r)
      setMessage(r.matched ? t.searchMatched(r.matched, r.area_km2) : t.searchNone)
    } catch (e) {
      onResults(null)
      setMessage(e instanceof Error ? e.message : String(e))
    } finally {
      setBusy(false)
    }
  }
  return (
    <section className="builder v3-search" aria-labelledby="v3-search-title">
      <div className="section-head">
        <div>
          <h3 id="v3-search-title">{t.searchTitle}</h3>
          <p>{t.searchLead}</p>
        </div>
      </div>
      <div className="v3-search-row">
        <label>
          <span>{t.scenarioForSearch}</span>
          <select id="v3-search-scenario" onChange={(e) => onScenario(e.target.value)} value={s?.id ?? ''}>
            {v.scenarios.map((x) => <option key={x.id} value={x.id}>{x.id} · {scenarioText(x.id, lang, x).name}</option>)}
          </select>
        </label>
        <label>
          <span>{t.environment}</span>
          <select id="v3-search-env" onChange={(e) => v.setEnv(e.target.value)} value={v.env}>
            {s?.assessed_targets.map((id) => <option key={id} value={id}>{targetName(t, id)}</option>)}
          </select>
        </label>
        <label>
          <span>{t.minTypicality}</span>
          <input id="v3-min-typicality" inputMode="decimal" onChange={(e) => setMinTyp(e.target.value)} value={minTyp} />
        </label>
        <label>
          <span>{t.minConfidence}</span>
          <select id="v3-min-confidence" onChange={(e) => setMinConf(e.target.value)} value={minConf}>
            {['low', 'medium', 'high'].map((c) => <option key={c} value={c}>{t.confidenceLevel[c]}</option>)}
          </select>
        </label>
      </div>
      <fieldset className="v3-search-reqs">
        <legend>{t.requirementsMet}</legend>
        {REQS.filter((r) => s?.requirements.some((x) => x.id === r)).map((r) => (
          <label className="check" key={r}>
            <input checked={reqs.includes(r)} onChange={() => setReqs(reqs.includes(r) ? reqs.filter((x) => x !== r) : [...reqs, r])} type="checkbox" />
            <span>{s ? reqLabel(r, lang, s) : r}</span>
          </label>
        ))}
      </fieldset>
      {message && <p className="note" role="status">{message}</p>}
      <div className="builder-actions">
        <span />
        <button className="primary" disabled={busy || !s} onClick={() => void run()} type="button">{t.searchRun} →</button>
      </div>
    </section>
  )
}

function reqLabel(id: string, lang: 'en' | 'fr', s: Scenario) {
  const r = s.requirements.find((x) => x.id === id)
  return r ? requirementText(id, lang, r).what : id
}

export type { CellProps }
