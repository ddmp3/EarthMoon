import type { SelectedMode } from "./store"

export const MISSION_ORDER: SelectedMode[] = ["robotics", "calibration", "colony", "custom"]
export const missionImage = (mode: SelectedMode) => `${import.meta.env.BASE_URL}img/${mode}.jpg`

export const siteName = (site: { name: string }) => site.name

/** Semantic color of a score out of 100 (independent of the accent). */
export function scoreTone(total: number, excluded = false): "good" | "mid" | "low" | "off" {
  if (excluded) return "off"
  if (total >= 70) return "good"
  if (total >= 40) return "mid"
  return "low"
}
