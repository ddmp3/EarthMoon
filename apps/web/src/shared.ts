import type { SelectedMode } from "./store"

export const MISSION_ORDER: SelectedMode[] = ["robotics", "calibration", "colony", "custom"]
export const missionImage = (mode: SelectedMode) => `${import.meta.env.BASE_URL}img/${mode}.jpg`

export const siteName = (site: { name: string; nameEn?: string }) => site.nameEn ?? site.name

/** Couleur sémantique d un score sur 100 (indépendante de l accent). */
export function scoreTone(total: number, excluded = false): "good" | "mid" | "low" | "off" {
  if (excluded) return "off"
  if (total >= 70) return "good"
  if (total >= 40) return "mid"
  return "low"
}
