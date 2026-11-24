import { useT } from '../i18n'
import { MARS_MISSIONS, MISSION_ORDER, missionImage } from '../shared'
import type { Body, SelectedMode } from '../store'

/** A figure of the banner: always read from the current release of the body, never typed (T45c). */
export type Figure = { value: string; label: string }

/**
 * Home of one body. The Moon: the Artemis II photo and the four lunar missions. Mars: the north polar cap and one
 * card per Martian terrain of scenario D. The Earth ↔ Moon / Earth ↔ Mars chips change the whole site (T45c, David 24/11).
 */
export function Home({ body, figures, onBody, onPick, onPickMars }: {
  body: Body
  figures: Figure[] | null
  onBody: (body: Body) => void
  onPick: (mode: SelectedMode) => void
  onPickMars: (target: string) => void
}) {
  const { t } = useT()
  const mars = body === 'mars'

  return (
    <>
      <section className="hero">
        <img className="hero-image" src={`${import.meta.env.BASE_URL}img/${mars ? 'mars-hero' : 'hero'}.jpg`} alt="" />
        <div className="hero-shade" />
        <div className="hero-copy">
          <span className="eyebrow">{mars ? t.marsHeroEyebrow : t.heroEyebrow}</span>
          <h1>{mars ? t.marsHeroTitle : t.heroTitle}</h1>
          <p>{mars ? t.marsHeroLead : t.heroLead}</p>
        </div>
        <span className="photo-credit hero-credit">{mars ? t.marsHeroCredit : t.heroCredit}</span>
      </section>

      <section className="missions" aria-labelledby="missions-title">
        <div className="section-head">
          <div>
            <h2 id="missions-title">{mars ? t.chooseMissionMars : t.chooseMission}</h2>
            <p>{mars ? t.chooseMissionMarsLead : t.chooseMissionLead}</p>
          </div>
          <div className="target-chips">
            <div aria-label={t.bodySwitch} className="body-switch" role="group">
              {(['moon', 'mars'] as Body[]).map((b) => (
                <button aria-pressed={body === b} key={b} onClick={() => onBody(b)} type="button">
                  {b === 'mars' ? t.targetMars : t.target}
                </button>
              ))}
            </div>
          </div>
        </div>

        <div className="mission-grid">
          {mars
            ? MARS_MISSIONS.map((m, index) => {
                const mission = t.marsMissions[m.id]
                return (
                  <button className={`mission-card${m.soon ? ' mission-soon' : ''}`} disabled={m.soon} key={m.id}
                    onClick={() => onPickMars(m.id)} type="button">
                    <span className={`mission-photo mission-photo-${m.image}`}>
                      <img src={`${import.meta.env.BASE_URL}img/${m.image}.jpg`} alt="" loading="lazy" />
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
                      <span className="mission-cta">{m.soon ? t.soon : `${t.launch} →`}</span>
                    </span>
                  </button>
                )
              })
            : MISSION_ORDER.map((mode, index) => {
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

        {figures && (
          <dl className="figures">
            {figures.map((f) => (
              <div key={f.label}>
                <dt>{f.value}</dt>
                <dd>{f.label}</dd>
              </div>
            ))}
          </dl>
        )}
      </section>
    </>
  )
}
