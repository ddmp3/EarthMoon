import type { Texts } from './i18n'
import { MARS_MISSIONS, MISSION_ORDER } from './shared'
import type { Body, SelectedMode } from './store'

/**
 * Credits of the images shown on the current page only (T45c, David 24/11): the home photos of the body, or the
 * banner, map, relief and globe of the mission. Data sources are listed in "Data and method" and on each site card,
 * so they are not repeated here.
 */
export function pageCredits(t: Texts, body: Body, mode: SelectedMode | null, env: string | null): string[] {
  if (!mode) {
    return body === 'mars'
      ? [t.marsHeroCredit, ...MARS_MISSIONS.map((m) => t.marsMissions[m.id].credit)]
      : [t.heroCredit, ...MISSION_ORDER.map((m) => t.missions[m].credit)]
  }
  const banner = mode === 'mars' ? (env && t.marsMissions[env] ? t.marsMissions[env].credit : t.missions.mars.credit) : t.missions[mode].credit
  return [banner, t.creditBaseMap, ...(mode === 'mars' ? [] : [t.creditSiteImagery]), t.creditRelief(body), t.creditGlobe(body), t.creditNames]
}

