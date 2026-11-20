import { paramInfo, type SiteResult } from '../api'
import { useT } from '../i18n'
import { wrapLabel } from '../shared'

/**
 * Match profile: one axis per criterion, outer ring = perfect match.
 * A criterion without data gets a dashed axis and no point: placing it at the centre would read as a 0 score.
 */
export function Radar({ site }: { site: SiteResult }) {
  const { lang } = useT()
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
  const measured = criteria.map((criterion, i) => ({ criterion, i })).filter(({ criterion }) => criterion.verdict !== 'missing')
  const shape = measured.map(({ criterion, i }) => point(i, r * Math.max(criterion.score, 0.03)).join(',')).join(' ')

  return (
    <svg className="radar" role="img" viewBox={`0 0 ${width} ${height}`}>
      {[0.25, 0.5, 0.75, 1].map((step) => (
        <polygon className={step === 1 ? 'radar-ring radar-target' : 'radar-ring'} fill="none" key={step} points={ring(r * step)} />
      ))}
      {criteria.map((criterion, i) => {
        const [x, y] = point(i, r)
        const [lx, ly] = point(i, r + 22)
        const anchor = Math.abs(lx - cx) < 12 ? 'middle' : lx > cx ? 'start' : 'end'
        const missing = criterion.verdict === 'missing'
        return (
          <g key={criterion.param}>
            <line className={missing ? 'radar-axis radar-axis-missing' : 'radar-axis'} x1={cx} x2={x} y1={cy} y2={y} />
            <text className={missing ? 'radar-label radar-label-missing' : 'radar-label'} dominantBaseline="middle" textAnchor={anchor} x={lx} y={ly}>
              {wrapLabel(paramInfo(criterion.param, lang).label).map((line, k, all) => (
                <tspan dy={k === 0 ? `${-(all.length - 1) * 0.55}em` : '1.1em'} key={k} x={lx}>
                  {line}
                </tspan>
              ))}
            </text>
          </g>
        )
      })}
      {measured.length > 0 && <polygon className="radar-shape" points={shape} />}
      {measured.map(({ criterion, i }) => {
        const [x, y] = point(i, r * Math.max(criterion.score, 0.03))
        return <circle className={`radar-dot tone-${criterion.verdict}`} cx={x} cy={y} key={criterion.param} r={4} />
      })}
    </svg>
  )
}
