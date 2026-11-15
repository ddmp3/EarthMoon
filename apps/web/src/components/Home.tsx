import { useT } from '../i18n'
import { MISSION_ORDER, missionImage } from '../shared'
import type { SelectedMode } from '../store'

/** Home: full-bleed Artemis II photo, then the four missions as cards. */
export function Home({ onPick, siteCount }: { onPick: (mode: SelectedMode) => void; siteCount: number }) {
  const { t } = useT()
  const figures = [String(siteCount), '18', '8', '71,731']

  return (
    <>
      <section className="hero">
        <img className="hero-image" src={`${import.meta.env.BASE_URL}img/hero.jpg`} alt="" />
        <div className="hero-shade" />
        <div className="hero-copy">
          <span className="eyebrow">{t.heroEyebrow}</span>
          <h1>{t.heroTitle}</h1>
          <p>{t.heroLead}</p>
        </div>
        <span className="photo-credit hero-credit">{t.heroCredit}</span>
      </section>

      <section className="missions" aria-labelledby="missions-title">
        <div className="section-head">
          <div>
            <h2 id="missions-title">{t.chooseMission}</h2>
            <p>{t.chooseMissionLead}</p>
          </div>
          <div className="target-chips">
            <span className="chip chip-on">{t.target}</span>
            <span className="chip">{t.marsSoon}</span>
          </div>
        </div>

        <div className="mission-grid">
          {MISSION_ORDER.map((mode, index) => {
            const mission = t.missions[mode]
            return (
              <button className="mission-card" key={mode} onClick={() => onPick(mode)} type="button">
                <span className={`mission-photo mission-photo-${mode}`}>
                  <img src={missionImage(mode)} alt="" loading="lazy" />
                  <span className="mission-number">{String(index + 1).padStart(2, '0')}</span>
                  <span className="photo-credit">{mission.credit}</span>
                </span>
                <span className="mission-body">
                  <strong>{mission.title}</strong>
                  <span className="mission-text">{mission.text}</span>
                  <span className="mission-tags">
                    {mission.tags.map((tag) => (
                      <span key={tag}>{tag}</span>
                    ))}
                  </span>
                  <span className="mission-cta">{t.launch} →</span>
                </span>
              </button>
            )
          })}
        </div>

        <dl className="figures">
          {t.stats.map((label, index) => (
            <div key={label}>
              <dt>{figures[index]}</dt>
              <dd>{label}</dd>
            </div>
          ))}
        </dl>
      </section>
    </>
  )
}
