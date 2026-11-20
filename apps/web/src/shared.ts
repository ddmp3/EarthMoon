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

/** Longest label line: with the side margins below, a line of this length stays inside the frame. */
export const LABEL_CHARS = 18

/** Splits a label into lines of at most LABEL_CHARS characters, on spaces (a longer single word keeps its line). */
export function wrapLabel(label: string, max = LABEL_CHARS): string[] {
  const lines: string[] = []
  for (const word of label.split(/\s+/).filter(Boolean)) {
    const last = lines[lines.length - 1]
    if (last !== undefined && `${last} ${word}`.length <= max) lines[lines.length - 1] = `${last} ${word}`
    else lines.push(word)
  }
  return lines
}
