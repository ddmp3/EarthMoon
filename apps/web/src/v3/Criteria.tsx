import { useEffect, useMemo, useState } from 'react'
import { useAppStore } from '../store'
import { v3 as v3api, type CriteriaCatalogue, type CriteriaPreset, type CriteriaRun, type CriteriaVariable, type Criterion } from './api'
import { CRITERIA_TEXTS } from './criteriaText'
import { failedRequired, orderPresets, sameRule, strip } from './criteriaModel'

const OPS = ['>=', '<=', '>', '<'] as const

/** Criteria panel (T54): the criteria of a use, readable and editable, tested on every cell and on the known sites. */
export function CriteriaPanel({ release, mission, terrain, onPreset, onResults, onLoadError, load = v3api.criteria, run = v3api.runCriteria }: {
  release: string
  mission: string
  terrain?: string
  onPreset?: (p: CriteriaPreset) => void
  onResults?: (r: CriteriaRun | null) => void
  /** The catalogue could not be read: the mission shows its map without a preset. */
  onLoadError?: () => void
  load?: (release?: string) => Promise<CriteriaCatalogue>
  run?: (body: { preset?: string; criteria?: Criterion[]; limit?: number }, release?: string) => Promise<CriteriaRun>
}) {
  const lang = useAppStore((s) => s.lang)
  const t = CRITERIA_TEXTS[lang]
  // every state is keyed by what it belongs to (release, preset), so nothing is reset synchronously in an effect
  const [loaded, setLoaded] = useState<{ release: string; cat: CriteriaCatalogue | null; error: string | null } | null>(null)
  const [presetId, setPresetId] = useState<string | null>(null)
  const [draftAt, setDraftAt] = useState<{ id: string; criteria: Criterion[] } | null>(null)
  const [runAt, setRunAt] = useState<{ id: string; result: CriteriaRun | null; error: string | null } | null>(null)
  const [busy, setBusy] = useState(false)
  const [equation, setEquation] = useState('')

  useEffect(() => {
    let alive = true
    load(release)
      .then((c) => alive && setLoaded({ release, cat: c, error: null }))
      .catch((e: unknown) => {
        if (!alive) return
        setLoaded({ release, cat: null, error: e instanceof Error ? e.message : String(e) })
        onLoadError?.()
      })
    return () => {
      alive = false
    }
  }, [release, load])

  const cat = loaded?.release === release ? loaded.cat : null
  const loadError = loaded?.release === release ? loaded.error : null
  const presets = useMemo(() => (cat ? orderPresets(cat.presets, mission, terrain) : []), [cat, mission, terrain])
  const preset = presets.find((p) => p.id === presetId) ?? presets[0] ?? null
  const vars = useMemo(() => Object.fromEntries((cat?.variables ?? []).map((v) => [v.id, v])) as Record<string, CriteriaVariable>, [cat])
  const draft = preset ? (draftAt?.id === preset.id ? draftAt.criteria : preset.criteria) : []
  const result = preset && runAt?.id === preset.id ? runAt.result : null
  const error = preset && runAt?.id === preset.id ? runAt.error : null

  const send = (p: CriteriaPreset, criteria: Criterion[]) =>
    run({ preset: p.id, criteria: criteria.map(strip), limit: 200 }, release)
      .then((r) => {
        setRunAt({ id: p.id, result: r, error: null })
        onResults?.(r)
      })
      .catch((e: unknown) => {
        setRunAt({ id: p.id, result: null, error: e instanceof Error ? e.message : String(e) })
        onResults?.(null)
      })

  const test = (p: CriteriaPreset, criteria: Criterion[]) => {
    setBusy(true)
    void send(p, criteria).finally(() => setBusy(false))
  }

  // a preset is precalibrated: choosing it shows its criteria and runs them at once
  useEffect(() => {
    if (!preset) return
    onPreset?.(preset)
    void send(preset, preset.criteria)
  }, [preset?.id]) // eslint-disable-line react-hooks/exhaustive-deps

  if (loadError) return <section className="builder criteria"><p className="note note-error" role="alert">{t.unavailable} {loadError}</p></section>
  if (!cat) return null
  if (!preset) return <section className="builder criteria"><p className="note">{t.noPreset}</p></section>

  const setDraft = (criteria: Criterion[]) => setDraftAt({ id: preset.id, criteria })
  const edit = (i: number, patch: Partial<Criterion>) => setDraft(draft.map((c, k) => (k === i ? { ...c, ...patch } : c)))
  const custom = !sameRule(draft, preset.criteria)
  const firstVar = cat.variables[0]?.id
  const label = (c: Criterion) => (c.variable ? (vars[c.variable]?.label[lang] ?? c.variable) : '')

  return (
    <section aria-labelledby="criteria-title" className="builder criteria">
      <div className="section-head">
        <div>
          <h3 id="criteria-title">{t.title}</h3>
          <p>{t.lead}</p>
        </div>
      </div>

      <label className="field criteria-preset">
        <span>{t.preset}</span>
        <select id="criteria-preset" onChange={(e) => setPresetId(e.target.value)} value={preset.id}>
          {presets.map((p) => <option key={p.id} value={p.id}>{p.title[lang]}</option>)}
        </select>
      </label>
      <p className="criteria-use">{preset.use[lang]} <small>{t.imitates} : {preset.imitates[lang]}.</small></p>
      <p className="criteria-method"><strong>{t.method}.</strong> {cat.method[lang]}</p>

      <ol className="criteria-list">
        {draft.map((c, i) => (
          <li className={`criteria-row role-${c.role}`} key={i}>
            <select aria-label={t.roleHelp} className="criteria-role" id={`criterion-role-${i}`}
              onChange={(e) => edit(i, { role: e.target.value as Criterion['role'] })} value={c.role}>
              <option value="required">{t.required}</option>
              <option value="preferred">{t.preferred}</option>
            </select>
            {c.expression !== undefined ? (
              <input aria-label={t.addEquation} className="criteria-expression" id={`criterion-expression-${i}`}
                onChange={(e) => edit(i, { expression: e.target.value })} value={c.expression} />
            ) : (
              <span className="criteria-condition">
                <select aria-label={t.variable} id={`criterion-variable-${i}`} onChange={(e) => edit(i, { variable: e.target.value })} value={c.variable}>
                  {cat.variables.map((v) => <option key={v.id} value={v.id}>{v.label[lang]}</option>)}
                </select>
                <select aria-label="op" id={`criterion-op-${i}`} onChange={(e) => edit(i, { op: e.target.value as Criterion['op'] })} value={c.op}>
                  {OPS.map((o) => <option key={o} value={o}>{t.op[o]}</option>)}
                </select>
                <input aria-label={`${label(c)} ${t.op[c.op ?? '>=']}`} id={`criterion-value-${i}`} inputMode="decimal"
                  onChange={(e) => {
                    const v = Number(e.target.value.replace(',', '.'))
                    edit(i, { value: Number.isFinite(v) ? v : c.value })
                  }}
                  type="number" step="any" value={c.value ?? 0} />
                {c.variable && vars[c.variable] && <small className="criteria-unit">{t.unitName[vars[c.variable].unit] ?? vars[c.variable].unit}</small>}
              </span>
            )}
            <button className="ghost" disabled={draft.length === 1} onClick={() => setDraft(draft.filter((_, k) => k !== i))} type="button">{t.remove}</button>
            {c.why && <small className="criteria-why">{t.why} : {c.why[lang]}{c.source_text ? ` — ${t.source} : ${c.source_text[lang]}` : c.source ? ` — ${t.source} : ${c.source}` : ''}</small>}
            {!c.why && c.variable && vars[c.variable] && <small className="criteria-why">{vars[c.variable].help[lang]} — {t.dataSource} : {vars[c.variable].source[lang]}</small>}
          </li>
        ))}
      </ol>

      <div className="criteria-add">
        <button className="ghost" disabled={!firstVar || draft.length >= 12} id="criteria-add"
          onClick={() => setDraft([...draft, { variable: firstVar, op: '>=', value: 0.5, role: 'preferred' }])} type="button">
          + {t.addCriterion}
        </button>
        <input aria-label={t.addEquation} className="criteria-expression" id="criteria-equation" onChange={(e) => setEquation(e.target.value)}
          placeholder={t.equationPlaceholder} value={equation} />
        <button className="ghost" disabled={!equation.trim() || draft.length >= 12} id="criteria-add-equation"
          onClick={() => { setDraft([...draft, { expression: equation.trim(), role: 'required' }]); setEquation('') }} type="button">
          + {t.addEquation}
        </button>
        <small className="criteria-why">{t.equationHelp}</small>
      </div>

      {error && <p className="note note-error" role="alert">{t.refused} {error}</p>}
      <div className="builder-actions">
        <button className="ghost" disabled={!custom} onClick={() => setDraft(preset.criteria)} type="button">{t.reset}</button>
        <button className="primary" disabled={busy} id="criteria-run" onClick={() => void test(preset, draft)} type="button">
          {busy ? t.running : `${t.run} →`}
        </button>
      </div>

      {result && <CriteriaResult r={result} />}

      <details className="criteria-variables">
        <summary>{t.variables}</summary>
        <table>
          <thead><tr><th>{t.variable}</th><th>{t.unit}</th><th>{t.dataSource}</th><th>{t.scale}</th></tr></thead>
          <tbody>
            {cat.variables.map((v) => (
              <tr key={v.id}><td><code>{v.id}</code><br /><small>{v.label[lang]} — {v.help[lang]}</small></td><td>{t.unitName[v.unit] ?? v.unit}</td><td>{v.source[lang]}</td><td>{v.scale[lang]}</td></tr>
            ))}
          </tbody>
        </table>
      </details>
    </section>
  )
}

/** Counts, land share and the check on the known sites, with why each site was not recovered. */
export function CriteriaResult({ r }: { r: CriteriaRun }) {
  const lang = useAppStore((s) => s.lang)
  const t = CRITERIA_TEXTS[lang]
  const fmt = (n: number) => n.toLocaleString(lang === 'fr' ? 'fr-CA' : 'en-CA')
  const pct = `${(r.land_share * 100).toLocaleString(lang === 'fr' ? 'fr-CA' : 'en-CA', { maximumFractionDigits: 2 })} %`
  const ks = r.known_sites
  const rule = r.rule.criteria
  return (
    <div aria-live="polite" className="criteria-result">
      <p className={`criteria-label ${r.custom ? 'is-custom' : ''}`}>{r.custom ? t.customLabel : t.presetLabel}</p>
      <ul className="criteria-counts">
        <li><strong>{fmt(r.counts.candidate)}</strong> {t.candidates} · {t.landShare(pct, fmt(Math.round(r.area_km2)))}</li>
        <li>{fmt(r.counts['to check'])} {t.toCheck}</li>
        <li>{fmt(r.counts.excluded)} {t.excluded}</li>
      </ul>
      <h4>{t.known}</h4>
      <p className="criteria-why">{t.knownLead}</p>
      <p><strong>{t.recovered(ks.recovered, ks.with_data)}</strong>{t.unknownSites(ks.unknown)} · {t.falseAlarms(ks.false_alarms, ks.negatives)}</p>
      <table className="criteria-sites">
        <tbody>
          {ks.chapters.map((ch) => {
            const best = ch.sites.find((s) => s.state === ch.state) ?? ch.sites[0]
            const failed = best ? failedRequired(rule, best.states) : []
            return (
              <tr className={`state-${ch.state.replace(' ', '-')}`} key={ch.chapter}>
                <td>{ch.name}<br /><small>{ch.sites.length} {t.chapterSites}</small></td>
                <td>{t.state[ch.state] ?? ch.state}</td>
                <td><small>{failed.map((i) => rule[i].text ?? '').join(' ; ')}</small></td>
              </tr>
            )
          })}
        </tbody>
      </table>
      <p className="criteria-why">{t.knownSource}</p>
    </div>
  )
}
