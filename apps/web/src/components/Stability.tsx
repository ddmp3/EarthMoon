import { paramInfo, type ParamId, type SiteDetail, type SiteResult } from '../api'
import { useT } from '../i18n'
import { stabilityLevel } from '../shared'

const DOTS = { high: 3, medium: 2, low: 1 } as const

/** Three dots: how solid the rank is when the expert choices (weights, ranges) are shaken. */
export function StabilityDots({ site, rank, total }: { site: SiteResult; rank: number; total: number }) {
  const { t } = useT()
  if (!site.stability) return null
  const level = stabilityLevel(site.stability, total)
  const label = `${t.stabilityLevels[level]}: ${t.stabilityLine(rank, site.stability.rankP10, site.stability.rankP90)}`
  return (
    <span aria-label={label} className={`stab stab-${level}`} role="img" title={label}>
      {[1, 2, 3].map((n) => (
        <i className={n <= DOTS[level] ? 'on' : ''} key={n} />
      ))}
    </span>
  )
}

/** Short explanation under the score of a site: stability and vegetation penalty. */
export function ConfidenceNotes({ site, rank, total }: { site: SiteResult; rank: number; total: number }) {
  const { t } = useT()
  const { stability, vegetationFactor } = site
  if (!stability && vegetationFactor === undefined) return null
  const level = stability ? stabilityLevel(stability, total) : null
  return (
    <div className="confidence">
      {stability && level && (
        <p>
          <strong className={`stab-text stab-${level}`}>
            {t.stabilityTitle}: {t.stabilityLevels[level]}.
          </strong>{' '}
          {t.stabilityLine(rank, stability.rankP10, stability.rankP90)} <small>{t.stabilityHint}</small>
        </p>
      )}
      {vegetationFactor !== undefined && <p>{t.vegetationNote(Math.round(vegetationFactor * 100))}</p>}
    </div>
  )
}

type Explanation = SiteDetail['explanation']

/** What the v2 API says about the solidity of a result: confidence, coverage, hard requirements and why (T45). */
export function Assessment({ site, explanation }: { site: SiteResult; explanation: Explanation | null }) {
  const { t, lang } = useT()
  const names = (ids: readonly ParamId[] | undefined) => (ids ?? []).map((id) => paramInfo(id, lang).label).join(', ')
  return (
    <section aria-label={t.assessmentTitle} className="assessment">
      <h4>{t.assessmentTitle}</h4>
      {site.confidence && (
        <p>
          <strong className={`conf conf-${site.confidence}`}>{t.confidenceLevels[site.confidence]}</strong> <small>{t.confidenceHint}</small>
        </p>
      )}
      <p>{t.coverageLine(Math.round(site.coverage * 100), site.totalRange.min, site.totalRange.max)}</p>
      <p>
        <strong className={`req req-${site.requirements}`}>{t.requirementsState[site.requirements]}</strong>
        {site.failedRequirements && site.failedRequirements.length > 0 && <> · {t.failedList}: {names(site.failedRequirements)}</>}
      </p>
      {site.missing && site.missing.length > 0 && !explanation && <p className="note">{t.missingList}: {names(site.missing)}</p>}
      {explanation && (
        <dl className="explain">
          {explanation.strengths.length > 0 && (<><dt>{t.strengths}</dt><dd>{names(explanation.strengths.map((c) => c.param))}</dd></>)}
          {explanation.weaknesses.length > 0 && (<><dt>{t.weaknesses}</dt><dd>{names(explanation.weaknesses.map((c) => c.param))}</dd></>)}
          {explanation.decisive.length > 0 && (<><dt>{t.decisive}</dt><dd>{names(explanation.decisive)}</dd></>)}
          {explanation.missing.length > 0 && (<><dt>{t.missingList}</dt><dd>{names(explanation.missing)}</dd></>)}
        </dl>
      )}
      {explanation && explanation.expertShare > 0 && <p className="note">{t.expertShare(Math.round(explanation.expertShare * 100))}</p>}
    </section>
  )
}
