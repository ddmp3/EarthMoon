import type { SiteResult } from '../api'
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
