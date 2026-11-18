import { FR_SITES } from "./content-fr"
import type { Lang } from "./i18n"
import type { SelectedMode } from "./store"

export const MISSION_ORDER: SelectedMode[] = ["robotics", "calibration", "colony", "custom"]
export const missionImage = (mode: SelectedMode) => `${import.meta.env.BASE_URL}img/${mode}.jpg`

/** Site name in the interface language (the data files are in English). */
export const siteName = (site: { id: string; name: string }, lang: Lang = "en") => (lang === "fr" ? FR_SITES[site.id] : undefined) ?? site.name

/** Semantic color of a score out of 100 (independent of the accent). */
export function scoreTone(total: number, excluded = false): "good" | "mid" | "low" | "off" {
  if (excluded) return "off"
  if (total >= 70) return "good"
  if (total >= 40) return "mid"
  return "low"
}

export type StabilityLevel = "high" | "medium" | "low"

/**
 * Plain-language reading of a rank range: the share of the list the rank moves across between the best and
 * worst cases of the sensitivity analysis (6% or less: stable; up to 25%: moderate; more: fragile).
 * The cut-offs are a presentation choice, documented in docs/VALIDATION.md.
 */
export function stabilityLevel(stability: { rankP10: number; rankP90: number }, rankedSites: number): StabilityLevel {
  const share = (stability.rankP90 - stability.rankP10) / Math.max(rankedSites, 1)
  if (share <= 0.06) return "high"
  if (share <= 0.25) return "medium"
  return "low"
}
