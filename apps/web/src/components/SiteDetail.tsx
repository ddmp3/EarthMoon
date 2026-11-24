import { useState } from 'react'
import {
  moonNote,
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
import { Radar } from './Radar'
import { Assessment, ConfidenceNotes } from './Stability'
import { FR_LIMITS, FR_SOURCES } from '../content-fr'
import { formatNumber, useT, type Lang } from '../i18n'
import { scoreTone, siteName } from '../shared'

function formatValue(value: number | null | undefined, unit: string, lang: Lang): string {
  if (value === null || value === undefined) return '—'
  return `${formatNumber(value, lang)}${unit ? ` ${unit}` : ''}`
}

function formatMoon(value: MoonValue | undefined, fallbackUnit: string, lang: Lang): string | null {
  if (!value) return null
  const unit = value.unit === '°C' || value.unit === '°' || value.unit === 'm' || value.unit === '%' ? value.unit : fallbackUnit
  const u = unit ? ` ${unit}` : ''
  if (value.min !== undefined && value.max !== undefined) {
    return value.min === value.max ? `${formatNumber(value.min, lang)}${u}` : `${formatNumber(value.min, lang)} – ${formatNumber(value.max, lang)}${u}`
  }
  if (value.min !== undefined) return `≥ ${formatNumber(value.min, lang)}${u}`
  return `≤ ${formatNumber(value.max as number, lang)}${u}`
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

function sourceName(id: string | undefined, sources: DataSource[], lang: Lang): string {
  if (!id) return '—'
  const found = sources.find((source) => source.id === id)
  return (lang === 'fr' ? FR_SOURCES[id]?.short : undefined) ?? SHORT_SOURCES[id] ?? (found ? found.name : id)
}

/** Earth ↔ Moon crossfade at the same scale, with lunar-like slopes highlighted. */
function Comparator({ siteId, visual, manifest, children }: { siteId: string; visual: SiteVisual; manifest: VisualManifest; children?: React.ReactNode }) {
  const { t, lang } = useT()
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
        {highlight && (
          <figure aria-label={t.slopeScale} className="slope-scale">
            <figcaption>{t.slopeScale}</figcaption>
            <div className="slope-bar">
              <span className="slope-band" style={{ left: `${(Math.min(lo, 30) / 30) * 100}%`, width: `${((Math.min(hi, 30) - Math.min(lo, 30)) / 30) * 100}%` }}
                title={t.lunarRange} />
            </div>
            <div className="slope-ticks"><span>0°</span><span>10°</span><span>20°</span><span>30°+</span></div>
            <small>{t.lunarRange}: {lo}–{hi}°</small>
          </figure>
        )}
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
              <th scope="row">{paramInfo('slope_mean', lang).label}</th>
              <td>{formatValue(visual.earth.slope_mean, '°', lang)}</td>
              <td>{formatValue(visual.twin.slope_mean, '°', lang)}</td>
            </tr>
            <tr>
              <th scope="row">{paramInfo('slope_max', lang).label}</th>
              <td>{formatValue(visual.earth.slope_max, '°', lang)}</td>
              <td>{formatValue(visual.twin.slope_max, '°', lang)}</td>
            </tr>
            <tr>
              <th scope="row">{paramInfo('roughness', lang).label}</th>
              <td>{formatValue(visual.earth.roughness, 'm', lang)}</td>
              <td>{formatValue(visual.twin.roughness, 'm', lang)}</td>
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
          {t.reliefCredit}
        </p>
        {children}
      </div>
    </div>
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
  /** v3 data of the cell holding the site (missions with a v3 scenario). */
  v3Section?: React.ReactNode
}

export function SiteDetail({ site, rank, rankedTotal, detail, detailError, visual, manifest, sources, limits, v3Section }: Props) {
  const { t, lang } = useT()
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
          <h2>{siteName(site, lang)}</h2>
          <p className="coords">
            {Math.abs(site.lat).toFixed(2)}°{site.lat < 0 ? 'S' : 'N'}, {Math.abs(site.lon).toFixed(2)}°{site.lon < 0 ? (lang === 'fr' ? 'O' : 'W') : 'E'}
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
        <Assessment explanation={detail?.explanation ?? null} site={site} />
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

      {v3Section}

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
                  const info = paramInfo(criterion.param, lang)
                  const moon = formatMoon(detail?.moon[criterion.param], info.unit, lang)
                  return (
                    <tr key={criterion.param}>
                      <th scope="row" title={info.help}>
                        {info.label}
                        <small>{info.help}</small>
                      </th>
                      <td className="num" data-label={t.colEarth}>{formatValue(criterion.value, info.unit, lang)}</td>
                      <td className="num moon-cell" data-label={t.colMoon}>
                        {moon ?? <span className="moon-note">{moonNote(criterion.param, lang) ?? t.noLunarRef}</span>}
                      </td>
                      <td className="match-cell" data-label={t.colMatch}>
                        {criterion.verdict === 'missing' ? (
                          <>
                            <span className="match-bar match-bar-missing" />
                            <span className="num match-value">—</span>
                          </>
                        ) : (
                          <>
                            <span className="match-bar">
                              <i className={`tone-${criterion.verdict}`} style={{ width: `${Math.round(criterion.score * 100)}%` }} />
                            </span>
                            <span className="num match-value">{Math.round(criterion.score * 100)}%</span>
                          </>
                        )}
                      </td>
                      <td data-label={t.colVerdict}>
                        <span className={`pill tone-${criterion.verdict}`}>{t.verdicts[criterion.verdict]}</span>
                      </td>
                      <td className="source-cell" data-label={t.colSource}>{sourceName(detail?.valueSources[criterion.param], sources, lang)}</td>
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
                    const text = (lang === 'fr' ? FR_LIMITS[limit.id] : undefined) ?? limit
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
