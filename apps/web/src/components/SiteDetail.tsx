import { useState } from 'react'
import {
  MOON_NOTES,
  paramInfo,
  siteImage,
  type DataSource,
  type EarthLimit,
  type MoonValue,
  type SiteDetail as SiteDetailData,
  type SiteResult,
  type SiteVisual,
  type VisualManifest,
} from '../api'
import { ConfidenceNotes } from './Stability'
import { formatNumber, useT } from '../i18n'
import { scoreTone, siteName } from '../shared'

function formatValue(value: number | null | undefined, unit: string): string {
  if (value === null || value === undefined) return '—'
  return `${formatNumber(value)}${unit ? ` ${unit}` : ''}`
}

function formatMoon(value: MoonValue | undefined, fallbackUnit: string): string | null {
  if (!value) return null
  const unit = value.unit === '°C' || value.unit === '°' || value.unit === 'm' || value.unit === '%' ? value.unit : fallbackUnit
  const u = unit ? ` ${unit}` : ''
  if (value.min !== undefined && value.max !== undefined) {
    return value.min === value.max ? `${formatNumber(value.min)}${u}` : `${formatNumber(value.min)} – ${formatNumber(value.max)}${u}`
  }
  if (value.min !== undefined) return `≥ ${formatNumber(value.min)}${u}`
  return `≤ ${formatNumber(value.max as number)}${u}`
}

// Short names for the table; the full name and attribution are in the source list at the bottom of the page.
const SHORT_SOURCES: Record<string, string> = {
  coordinates: 'Site coordinates',
  'nasa-power': 'NASA POWER',
  'usgs-comcat': 'USGS Earthquake Catalog',
  'smithsonian-gvp': 'Smithsonian GVP',
  'copernicus-dem': 'Copernicus DEM GLO-30 (ESA)',
  modis: 'NASA MODIS',
  fixtures: 'Sample data (not for demo)',
}

function sourceName(id: string | undefined, sources: DataSource[]): string {
  if (!id) return '—'
  const found = sources.find((source) => source.id === id)
  return SHORT_SOURCES[id] ?? (found ? found.name : id)
}

/** Earth ↔ Moon crossfade at the same scale, with lunar-like slopes highlighted. */
function Comparator({ siteId, visual, manifest, children }: { siteId: string; visual: SiteVisual; manifest: VisualManifest; children?: React.ReactNode }) {
  const { t } = useT()
  const hasPhoto = Boolean(visual.photo)
  // ?fade=60 in the URL sets the initial crossfade (demo links).
  const [fade, setFade] = useState(() => {
    const wanted = Number(new URLSearchParams(window.location.search).get('fade'))
    return Number.isFinite(wanted) ? Math.min(Math.max(wanted, 0), 100) : 0
  })
  const [layer, setLayer] = useState<'satellite' | 'relief'>(hasPhoto ? 'satellite' : 'relief')
  const [highlight, setHighlight] = useState(true)
  const moon = fade / 100
  const earthLayer = layer === 'satellite' && hasPhoto ? 'earth.jpg' : 'earth-relief.jpg'
  const [lo, hi] = manifest.slope_band_deg
  const percent = (share: number) => `${Math.round(share * 100)}%`

  return (
    <div className="comparator">
      <div className="stage-column">
        <div className="stage">
          <img className="stage-layer" src={siteImage(siteId, earthLayer)} alt="" />
          {highlight && <img className="stage-layer stage-mask" src={siteImage(siteId, 'earth-match.png')} alt="" style={{ opacity: 1 - moon }} />}
          <img className="stage-layer" src={siteImage(siteId, 'moon-relief.jpg')} alt="" style={{ opacity: moon }} />
          {highlight && <img className="stage-layer stage-mask" src={siteImage(siteId, 'moon-match.png')} alt="" style={{ opacity: moon }} />}
          <span className="stage-tag stage-tag-earth" style={{ opacity: 1 - moon * 0.75 }}>{t.earth}</span>
          <span className="stage-tag stage-tag-moon" style={{ opacity: 0.25 + moon * 0.75 }}>{t.moon}</span>
          <span className="scale-bar"><i />{t.scaleBar}</span>
        </div>
        <label className="fader">
          <span>{t.earth}</span>
          <input
            aria-label={`${t.earth} ↔ ${t.moon}`}
            id={`fade-${siteId}`}
            max={100}
            min={0}
            onChange={(event) => setFade(Number(event.target.value))}
            type="range"
            value={fade}
          />
          <span>{t.moon}</span>
        </label>
        <div className="stage-controls">
          <div className="segmented" role="group">
            <button aria-pressed={layer === 'satellite'} disabled={!hasPhoto} onClick={() => setLayer('satellite')} type="button">{t.satellite}</button>
            <button aria-pressed={layer === 'relief'} onClick={() => setLayer('relief')} type="button">{t.relief}</button>
          </div>
          <label className="check">
            <input checked={highlight} id={`highlight-${siteId}`} onChange={(event) => setHighlight(event.target.checked)} type="checkbox" />
            <span><i className="swatch" />{t.highlight}</span>
          </label>
        </div>
        {!hasPhoto && <p className="note">{t.noPhoto}</p>}
      </div>

      <div className="twin-facts">
        <table className="twin-table">
          <thead>
            <tr>
              <th scope="col" />
              <th scope="col">{t.earth}</th>
              <th scope="col">{t.lunarTwin}</th>
            </tr>
          </thead>
          <tbody>
            <tr>
              <th scope="row">{paramInfo('slope_mean', 'en').label}</th>
              <td>{formatValue(visual.earth.slope_mean, '°')}</td>
              <td>{formatValue(visual.twin.slope_mean, '°')}</td>
            </tr>
            <tr>
              <th scope="row">{paramInfo('slope_max', 'en').label}</th>
              <td>{formatValue(visual.earth.slope_max, '°')}</td>
              <td>{formatValue(visual.twin.slope_max, '°')}</td>
            </tr>
            <tr>
              <th scope="row">{paramInfo('roughness', 'en').label}</th>
              <td>{formatValue(visual.earth.roughness, 'm')}</td>
              <td>{formatValue(visual.twin.roughness, 'm')}</td>
            </tr>
            <tr>
              <th scope="row">{t.terrainShare}</th>
              <td>{percent(visual.earth.match_share)}</td>
              <td>{percent(visual.twin.match_share)}</td>
            </tr>
          </tbody>
        </table>
        <p className="note">
          {t.lunarTwin}: {t.twinAt(visual.twin.lat, visual.twin.lon)}. {t.highlightHint(lo, hi)}.
        </p>
        <p className="note">
          {visual.photo ? `${visual.photo.credit}. ` : ''}
          {manifest.earth_relief_source}. {manifest.moon_source}.
        </p>
        {children}
      </div>
    </div>
  )
}

/** Match profile: one axis per criterion, outer ring = perfect match. */
function Radar({ site }: { site: SiteResult }) {
  const criteria = site.criteria
  const n = criteria.length
  // Wide side margins: long labels ("Minimum air temperature") stay inside the frame.
  const width = 520
  const height = 330
  const cx = width / 2
  const cy = height / 2
  const r = 108
  const point = (index: number, radius: number): [number, number] => {
    const angle = (Math.PI * 2 * index) / n - Math.PI / 2
    return [cx + Math.cos(angle) * radius, cy + Math.sin(angle) * radius]
  }
  const ring = (radius: number) => criteria.map((_, i) => point(i, radius).join(',')).join(' ')
  const shape = criteria.map((criterion, i) => point(i, r * Math.max(criterion.score, 0.03)).join(',')).join(' ')

  return (
    <svg className="radar" role="img" viewBox={`0 0 ${width} ${height}`}>
      {[0.25, 0.5, 0.75, 1].map((step) => (
        <polygon className={step === 1 ? 'radar-ring radar-target' : 'radar-ring'} fill="none" key={step} points={ring(r * step)} />
      ))}
      {criteria.map((criterion, i) => {
        const [x, y] = point(i, r)
        const [lx, ly] = point(i, r + 22)
        const anchor = Math.abs(lx - cx) < 12 ? 'middle' : lx > cx ? 'start' : 'end'
        return (
          <g key={criterion.param}>
            <line className="radar-axis" x1={cx} x2={x} y1={cy} y2={y} />
            <text className="radar-label" dominantBaseline="middle" textAnchor={anchor} x={lx} y={ly}>
              {paramInfo(criterion.param, 'en').label}
            </text>
          </g>
        )
      })}
      <polygon className="radar-shape" points={shape} />
      {criteria.map((criterion, i) => {
        const [x, y] = point(i, r * Math.max(criterion.score, 0.03))
        return <circle className={`radar-dot tone-${criterion.verdict}`} cx={x} cy={y} key={criterion.param} r={4} />
      })}
    </svg>
  )
}

interface Props {
  site: SiteResult
  rank: number
  /** Number of ranked (non-excluded) sites, to read the rank range. */
  rankedTotal: number
  detail: SiteDetailData | null
  detailError: string | null
  visual: SiteVisual | undefined
  manifest: VisualManifest | null
  sources: DataSource[]
  limits: EarthLimit[]
}

export function SiteDetail({ site, rank, rankedTotal, detail, detailError, visual, manifest, sources, limits }: Props) {
  const { t } = useT()
  const evaluated = site.criteria.filter((criterion) => criterion.verdict !== 'missing').length
  const count = (verdict: string) => site.criteria.filter((criterion) => criterion.verdict === verdict).length
  const tone = scoreTone(site.total, Boolean(site.excluded))

  return (
    <article className="site-detail">
      <header className="detail-head">
        <div>
          <span className="eyebrow">
            #{rank} · {site.excluded ? t.excluded : t.roles[site.role]}
          </span>
          <h2>{siteName(site)}</h2>
          <p className="coords">
            {Math.abs(site.lat).toFixed(2)}°{site.lat < 0 ? 'S' : 'N'}, {Math.abs(site.lon).toFixed(2)}°{site.lon < 0 ? 'W' : 'E'}
          </p>
        </div>
        <div className={`score-block tone-${tone}`}>
          <strong>{site.excluded ? '—' : Math.round(site.total)}</strong>
          <span>
            {t.score}
            <small>
              {evaluated}/{site.criteria.length} {t.criteriaEvaluated}
            </small>
          </span>
        </div>
        <ConfidenceNotes rank={rank} site={site} total={rankedTotal} />
        <ul className="verdict-summary">
          {(['match', 'partial', 'mismatch', 'missing'] as const).map((verdict) =>
            count(verdict) > 0 ? (
              <li className={`tone-${verdict}`} key={verdict}>
                <b>{count(verdict)}</b> {t.verdicts[verdict]}
              </li>
            ) : null,
          )}
        </ul>
      </header>

      {visual && manifest && (
        <section className="detail-section">
          <h3>{t.seeTheMatch}</h3>
          <p className="lead">{t.seeTheMatchLead}</p>
          <Comparator key={site.id} manifest={manifest} siteId={site.id} visual={visual}>
            {site.criteria.length >= 3 && !site.excluded && (
              <figure className="radar-figure">
                <figcaption>
                  <strong>{t.radarTitle}</strong>
                  <span>{t.radarLead}</span>
                </figcaption>
                <Radar site={site} />
              </figure>
            )}
          </Comparator>
        </section>
      )}

      <section className="detail-section">
        <h3>{t.scorecard}</h3>
        <p className="lead">{t.scorecardLead}</p>
        <div className="scorecard-layout">
          <div className="table-scroll">
            <table className="scorecard">
              <thead>
                <tr>
                  <th scope="col">{t.colParameter}</th>
                  <th scope="col">{t.colEarth}</th>
                  <th scope="col">{t.colMoon}</th>
                  <th scope="col">{t.colMatch}</th>
                  <th scope="col">{t.colVerdict}</th>
                  <th scope="col">{t.colSource}</th>
                </tr>
              </thead>
              <tbody>
                {site.criteria.map((criterion) => {
                  const info = paramInfo(criterion.param, 'en')
                  const moon = formatMoon(detail?.moon[criterion.param], info.unit)
                  return (
                    <tr key={criterion.param}>
                      <th scope="row" title={info.help}>
                        {info.label}
                        <small>{info.help}</small>
                      </th>
                      <td className="num" data-label={t.colEarth}>{formatValue(criterion.value, info.unit)}</td>
                      <td className="num moon-cell" data-label={t.colMoon}>
                        {moon ?? <span className="moon-note">{MOON_NOTES[criterion.param] ?? t.noLunarRef}</span>}
                      </td>
                      <td className="match-cell" data-label={t.colMatch}>
                        <span className="match-bar">
                          <i className={`tone-${criterion.verdict}`} style={{ width: `${Math.round(criterion.score * 100)}%` }} />
                        </span>
                        <span className="num match-value">{Math.round(criterion.score * 100)}%</span>
                      </td>
                      <td data-label={t.colVerdict}>
                        <span className={`pill tone-${criterion.verdict}`}>{t.verdicts[criterion.verdict]}</span>
                      </td>
                      <td className="source-cell" data-label={t.colSource}>{sourceName(detail?.valueSources[criterion.param], sources)}</td>
                    </tr>
                  )
                })}
              </tbody>
              {limits.length > 0 && (
                <tbody className="limits">
                  <tr className="group-row">
                    <th colSpan={6} scope="colgroup">
                      {t.limitsTitle}
                    </th>
                  </tr>
                  {limits.map((limit) => {
                    const text = limit
                    return (
                      <tr key={limit.id}>
                        <th scope="row">
                          {text.label}
                          <small>{text.effect}</small>
                        </th>
                        <td data-label={t.colEarth}>{text.earth}</td>
                        <td className="moon-cell" data-label={t.colMoon}>{text.moon}</td>
                        <td className="cell-empty">
                          <span className="match-bar match-bar-none" />
                        </td>
                        <td data-label={t.colVerdict}>
                          <span className="pill tone-limit">{t.limitsVerdict}</span>
                        </td>
                        <td className="source-cell" data-label={t.colSource}>{limit.source.split(' — ')[0]}</td>
                      </tr>
                    )
                  })}
                </tbody>
              )}
            </table>
          </div>
        </div>
        {detailError && <p className="note note-error">{detailError}</p>}
      </section>
    </article>
  )
}
