import { useEffect, useRef } from 'react'
import type { Coverage, GeologyShares, MethodSource, Scenario, Status, Zone } from './api'
import { cividis, legendRows, statusLines, zoneDimensions, type ZoneContext } from './model'
import { useAppStore } from '../store'
import { limitText, requirementText, stepText } from './content'
import type { V3Texts } from './text'

const two = (v: number | null | undefined) => (v === null || v === undefined ? '—' : v.toFixed(2))
const pct = (v: number | null | undefined) => (v === null || v === undefined ? '—' : `${Math.round(v * 100)}%`)

/** SVG patterns of the coverage overlay, defined once per page (the map's cells and the legend use them). */
export function Patterns() {
  const ink = '#b9c6e8'
  return (
    <svg aria-hidden="true" className="v3-patterns" focusable="false" height="0" width="0">
      <defs>
        <pattern height="6" id="pat-dense" patternTransform="rotate(45)" patternUnits="userSpaceOnUse" width="6">
          <line stroke={ink} strokeWidth="2.4" x1="0" x2="0" y1="0" y2="6" />
        </pattern>
        <pattern height="8" id="pat-hidden" patternTransform="rotate(-45)" patternUnits="userSpaceOnUse" width="8">
          <line stroke={ink} strokeWidth="2" x1="0" x2="0" y1="0" y2="8" />
        </pattern>
        <pattern height="10" id="pat-light" patternTransform="rotate(45)" patternUnits="userSpaceOnUse" width="10">
          <line stroke={ink} strokeOpacity="0.8" strokeWidth="1" x1="0" x2="0" y1="0" y2="10" />
        </pattern>
        <pattern height="7" id="pat-dots" patternUnits="userSpaceOnUse" width="7">
          <circle cx="3.5" cy="3.5" fill="#8a93a8" r="1.3" />
        </pattern>
        <pattern height="10" id="pat-outline" patternUnits="userSpaceOnUse" width="10">
          <rect fill="none" height="10" stroke={ink} strokeDasharray="2 2" strokeWidth="1" width="10" />
        </pattern>
      </defs>
    </svg>
  )
}


function Requirements({ scenario, zone, t }: { scenario: Scenario | null; zone: Zone; t: V3Texts }) {
  const lang = useAppStore((st) => st.lang)
  const reqs = (scenario?.requirements ?? []).filter((r) => zone.requirements[r.id])
  if (reqs.length === 0) return null
  return (
    <section>
      <h4>{t.requirements}</h4>
      <ul className="v3-reqs">
        {reqs.map((r) => {
          const c = zone.requirements[r.id] as { met?: number; failed?: number; unknown?: number }
          const state = (c.failed ?? 0) > 0 ? 'failed' : (c.unknown ?? 0) > 0 && !(c.met ?? 0) ? 'unknown' : 'met'
          return (
            <li key={r.id}>
              <span className={`v3-req v3-req-${state}`}>{t.reqState[state]}</span>
              <span>{requirementText(r.id, lang, r).what}</span>
              <span className="note">{requirementText(r.id, lang, r).value}</span>
              <span className="note">{t.reqCells(c.met ?? 0, c.failed ?? 0, c.unknown ?? 0)}</span>
            </li>
          )
        })}
      </ul>
    </section>
  )
}

export function ZoneCard({ zone, scenario, cannotAssess, onClose, onProvenance, status = null, t }: {
  zone: Zone
  scenario: Scenario | null
  status?: Status | null
  cannotAssess: string[]
  onClose: () => void
  onProvenance: () => void
  t: V3Texts
}) {
  const conf = zone.coverage.cells_by_confidence
  const lang = useAppStore((st) => st.lang)
  return (
    <section aria-label={`${t.zone} ${zone.rank}`} className="v3-card" role="region">
      <header>
        <h3>{zone.place?.[lang] ? <>{zone.place[lang]} <small>{t.zone} {zone.rank}</small></> : <>{t.zone} {zone.rank}</>} <small>{t.cellsArea(zone.cells, zone.area_km2)}</small></h3>
        <button aria-label={t.close} className="v3-close" onClick={onClose} type="button">×</button>
      </header>
      <p className="note">{zone.lat.toFixed(4)}, {zone.lon.toFixed(4)}{zone.slope_median != null ? ` · ${t.slopeMedian(zone.slope_median)}` : ''}</p>
      <StatusBar status={status} t={t} />
      <div className="v3-scroll">
      <table className="v3-dims">
        <thead>
          <tr><th scope="col">{t.dimension}</th><th scope="col">{t.median}</th><th scope="col">{t.iqr}</th><th scope="col">n ({t.windows})</th><th scope="col">{t.source}</th></tr>
        </thead>
        <tbody>
          {zoneDimensions(zone.typicality, zone.coverage.valid_unmasked, t, (zone as { geology?: GeologyShares | null }).geology ?? null,
            (zone as { context?: ZoneContext | null }).context ?? null).map((d) => (
            <tr className={d.missing ? 'v3-missing' : ''} key={d.name}>
              <th scope="row">{d.name}</th>
              {d.missing ? (
                <td colSpan={4}><span className="v3-missing-chip">{d.missing}</span></td>
              ) : d.text ? (
                <>
                  <td colSpan={3}>{d.text}</td>
                  <td>{d.source}</td>
                </>
              ) : (
                <>
                  <td>{two(d.median)}</td>
                  <td>{`${two(d.p25)}–${two(d.p75)}`}</td>
                  <td>{d.n}</td>
                  <td>{d.source}</td>
                </>
              )}
            </tr>
          ))}
        </tbody>
      </table>
      </div>
      <Requirements scenario={scenario} t={t} zone={zone} />
      <section>
        <h4>{t.confidenceLabel}</h4>
        <p>{t.highShare(zone.high_confidence_share)}</p>
        <p className="note">{t.confidenceLevel.high} {conf.high ?? 0} · {t.confidenceLevel.medium} {conf.medium ?? 0} · {t.confidenceLevel.low} {conf.low ?? 0}</p>
        <p className="note">{zone.monte_carlo?.top_decile_share != null ? t.monteCarlo(zone.monte_carlo.top_decile_share) : t.monteCarloNone}</p>
      </section>
      <section className="v3-cannot">
        <h4>{t.cannotReproduce}</h4>
        <ul>{cannotAssess.map((c) => <li key={c}>{limitText(c, lang)}</li>)}</ul>
      </section>
      <button className="ghost" onClick={onProvenance} type="button">{t.provenance}</button>
    </section>
  )
}

function Strip({ zone }: { zone: Zone }) {
  const { median, p25, p75 } = zone.typicality
  const x = (v: number) => 4 + v * 112
  return (
    <svg aria-label={`median ${two(median)}, IQR ${two(p25)}–${two(p75)}`} data-strip height="18" role="img" width="120">
      <line stroke="#3a4258" x1="4" x2="116" y1="9" y2="9" />
      <line stroke="#eef0f6" strokeWidth="2" x1={x(p25)} x2={x(p75)} y1="9" y2="9" />
      <line stroke="#eef0f6" x1={x(p25)} x2={x(p25)} y1="5" y2="13" />
      <line stroke="#eef0f6" x1={x(p75)} x2={x(p75)} y1="5" y2="13" />
      <circle cx={x(median)} cy="9" fill={cividis(median)} r="4" stroke="#05070d" />
    </svg>
  )
}

export function CompareZones({ zones, onClose, t }: { zones: Zone[]; onClose: () => void; t: V3Texts }) {
  const req = (z: Zone, id: string) => {
    const c = z.requirements[id] as { met?: number; failed?: number; unknown?: number } | undefined
    if (!c) return '—'
    return (c.failed ?? 0) > 0 ? t.reqState.failed : (c.met ?? 0) > 0 ? t.reqState.met : t.reqState.unknown
  }
  const reqIds = [...new Set(zones.flatMap((z) => Object.keys(z.requirements)))]
  return (
    <section aria-label={t.compareTitle} className="v3-card v3-compare" role="region">
      <header>
        <h3>{t.compareTitle}</h3>
        <button aria-label={t.close} className="v3-close" onClick={onClose} type="button">×</button>
      </header>
      <div className="v3-scroll">
        <table aria-label={t.compareTitle}>
          <thead>
            <tr><th scope="col">{t.dimension}</th>{zones.map((z) => <th key={z.id} scope="col">{t.zone} {z.rank}</th>)}</tr>
          </thead>
          <tbody>
            <tr><th scope="row">{t.layer.topography}</th>{zones.map((z) => <td key={z.id}><Strip zone={z} /></td>)}</tr>
            <tr><th scope="row">{t.layer.geology}</th>{zones.map((z) => <td key={z.id}><span className="v3-missing-chip">{t.geologyMissing}</span></td>)}</tr>
            {reqIds.map((id) => (
              <tr key={id}><th scope="row">{id}</th>{zones.map((z) => <td key={z.id}>{req(z, id)}</td>)}</tr>
            ))}
            <tr><th scope="row">{t.confidenceLabel}</th>{zones.map((z) => <td key={z.id}>{pct(z.high_confidence_share)}</td>)}</tr>
            <tr><th scope="row">km²</th>{zones.map((z) => <td key={z.id}>{Math.round(z.area_km2)}</td>)}</tr>
          </tbody>
        </table>
      </div>
    </section>
  )
}

function Dialog({ label, onClose, children, t }: { label: string; onClose: () => void; children: React.ReactNode; t: V3Texts }) {
  const ref = useRef<HTMLDivElement>(null)
  useEffect(() => {
    ref.current?.focus()
    const onKey = (e: KeyboardEvent) => e.key === 'Escape' && onClose()
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [onClose])
  return (
    <div className="v3-backdrop" onClick={onClose}>
      <div aria-label={label} aria-modal="true" className="v3-dialog" onClick={(e) => e.stopPropagation()} ref={ref} role="dialog" tabIndex={-1}>
        <header>
          <h2>{label}</h2>
          <button aria-label={t.close} className="v3-close" onClick={onClose} type="button">×</button>
        </header>
        {children}
      </div>
    </div>
  )
}

/** Parameters of a processing step (scales, classes, rules), as recorded by the run: technical, kept as written. */
function stepDetail(s: Record<string, unknown>): string {
  const parts: string[] = []
  for (const [k, v] of Object.entries(s)) {
    if (k === 'step' || k === 'what' || v === null || v === undefined) continue
    parts.push(`${k}: ${typeof v === 'object' ? JSON.stringify(v).replace(/[{}"[\]]/g, '').replace(/,/g, ', ').replace(/:/g, ': ') : String(v)}`)
  }
  return parts.join(' · ')
}

export function DataMethod({ coverage, sources, processing, cannotAssess, onClose, t }: {
  coverage: Coverage['coverage'] | null
  sources: MethodSource[]
  processing: Record<string, unknown>[]
  cannotAssess: string[]
  onClose: () => void
  t: V3Texts
}) {
  const lang = useAppStore((st) => st.lang)
  return (
    <Dialog label={t.dataMethod} onClose={onClose} t={t}>
      <section>
        <h3>{t.whatWeCover}</h3>
        {coverage ? (
          <p>{legendRows(coverage, t).map((r) => `${r.label} ${pct(r.share)}`).join(' · ')}</p>
        ) : (
          <p className="note">{t.loading}</p>
        )}
      </section>
      <section>
        <h3>{t.sourcesUsed}</h3>
        {t.catalogueNote && <p className="note">{t.catalogueNote}</p>}
        <ul className="v3-sources">
          {sources.map((s, i) => (
            <li aria-label={`source ${s.id}`} key={`${s.id}-${i}`}>
              <strong>{s.product ?? s.id}</strong>{' '}
              <span className={`v3-badge ${s.status === 'verified' ? 'v3-ok' : 'v3-warn'}`}>
                {s.status === 'not in catalogue' ? t.notInCatalogue : s.status === 'verified' && s.verified_on ? t.verifiedOn(s.verified_on) : s.status || t.notVerified}
              </span>
              {s.status !== 'verified' && s.verified_on && <span className="note"> · {t.verifiedOn(s.verified_on)}</span>}
              <dl>
                {s.producer && (<><dt>·</dt><dd>{s.producer}</dd></>)}
                {s.licence && (<><dt>{t.licence}</dt><dd>{s.licence}</dd></>)}
                {s.coverage && (<><dt>coverage</dt><dd>{s.coverage}</dd></>)}
                {s.resolution_spatial && (<><dt>{t.resolution}</dt><dd>{s.resolution_spatial}</dd></>)}
                {s.uncertainty && (<><dt>{t.uncertainty}</dt><dd>{s.uncertainty}</dd></>)}
                {s.limitations && (<><dt>{t.limits}</dt><dd>{s.limitations}</dd></>)}
              </dl>
            </li>
          ))}
        </ul>
      </section>
      <section>
        <h3>{t.howProcessed}</h3>
        <ol className="v3-steps">
          {processing.map((s, i) => (
            <li aria-label={`step ${String(s.step ?? i + 1)}`} key={i}>
              {stepText(String(s.step ?? ''), lang, typeof s.what === 'string' ? s.what : null)}
              {stepDetail(s) && <small className="note"> · {stepDetail(s)}</small>}
            </li>
          ))}
        </ol>
      </section>
      <section>
        <h3>{t.whatItCannotSay}</h3>
        <ul>{cannotAssess.map((c) => <li key={c}>{limitText(c, lang)}</li>)}</ul>
      </section>
    </Dialog>
  )
}

export function Provenance({ zone, release, onClose, status = null, t }: {
  zone: Zone
  status?: Status | null
  release: { release: string; run: string; protocol?: string; commit?: string } | null
  onClose: () => void
  t: V3Texts
}) {
  return (
    <Dialog label={`${t.provenance} · ${t.zone} ${zone.rank}`} onClose={onClose} t={t}>
      <p className="note">{t.provenanceLead}</p>
      <StatusBar status={status} t={t} />
      <dl className="v3-prov">
        <dt>{t.median}</dt><dd>{two(zone.typicality.median)} ({t.iqr} {two(zone.typicality.p25)}–{two(zone.typicality.p75)}), {zone.coverage.valid_unmasked} {t.windows}</dd>
        <dt>{t.provenanceRelease}</dt><dd>{release?.release ?? '—'}</dd>
        <dt>{t.provenanceRun}</dt><dd>{release?.run ?? '—'}</dd>
        <dt>{t.provenanceProtocol}</dt><dd>{release?.protocol ?? '—'}</dd>
        <dt>{t.provenanceCommit}</dt><dd><code>{release?.commit?.slice(0, 12) ?? '—'}</code></dd>
        <dt>DEM</dt><dd>{t.provenanceDem}</dd>
        <dt>masks</dt><dd>{t.provenanceMasks}</dd>
        <dt>{t.bodyLabel}</dt><dd>{t.provenanceMoon}</dd>
        <dt>tiles</dt><dd>{(zone.tiles ?? []).join(' · ') || '—'}</dd>
      </dl>
    </Dialog>
  )
}

export function StatusBar({ status, t }: { status: Status | null; t: V3Texts }) {
  if (!status) return null
  const l = statusLines(status, t)
  return (
    <div className={`v3-status v3-status-${l.state}`} role="status">
      <strong>{l.validity}</strong>
      {l.failing && <span>{l.failing}</span>}
      <span>{l.freshness}</span>
      {l.impact && <span>{l.impact}</span>}
    </div>
  )
}
