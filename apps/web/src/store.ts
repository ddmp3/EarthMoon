import { create } from 'zustand'
import { parameterCatalog, type CalibrationInstrument, type ModeId, type ParamId } from './api'
import type { Lang } from './i18n'

export type SelectedMode = ModeId | 'custom' | 'mars'
/** The body a mission compares Earth with: the four lunar missions, or Mars (mission 5, T48). */
export type Body = 'moon' | 'mars'

export interface CriterionDraft {
  param: ParamId
  min: string
  max: string
  tolerance: string
  weight: string
}

const initialCriterion: CriterionDraft = {
  param: 'slope_mean',
  min: '5',
  max: '13',
  tolerance: '10',
  weight: '1',
}

/**
 * English by default (Space Apps submission requirement). A visitor's choice is kept in the browser;
 * ?lang=fr in the address also selects French (shareable link).
 */
function initialLang(): Lang {
  const fromAddress = new URLSearchParams(window.location.search).get('lang')
  if (fromAddress === 'fr' || fromAddress === 'en') return fromAddress
  try {
    const saved = localStorage.getItem('lang')
    if (saved === 'fr' || saved === 'en') return saved
  } catch {
    // storage unavailable (private browsing): keep the default
  }
  return 'en'
}

interface AppStore {
  lang: Lang
  setLang: (lang: Lang) => void
  body: Body
  setBody: (body: Body) => void
  criteriaDraft: CriterionDraft[]
  bareSoilOnly: boolean
  calibrationInstrument: CalibrationInstrument | 'all'
  setBareSoilOnly: (bareSoilOnly: boolean) => void
  setCalibrationInstrument: (instrument: CalibrationInstrument | 'all') => void
  updateCriterion: (index: number, updates: Partial<CriterionDraft>) => void
  addCriterion: () => void
  removeCriterion: (index: number) => void
}

export const useAppStore = create<AppStore>((set) => ({
  lang: initialLang(),
  body: 'moon',
  setBody: (body) => set({ body }),
  setLang: (lang) => {
    try {
      localStorage.setItem('lang', lang)
    } catch {
      // without storage the choice lasts for the session
    }
    set({ lang })
  },
  criteriaDraft: [initialCriterion],
  bareSoilOnly: true,
  calibrationInstrument: 'all',
  setBareSoilOnly: (bareSoilOnly) => set({ bareSoilOnly }),
  setCalibrationInstrument: (calibrationInstrument) => set({ calibrationInstrument }),
  updateCriterion: (index, updates) =>
    set((state) => ({
      criteriaDraft: state.criteriaDraft.map((criterion, criterionIndex) =>
        criterionIndex === index ? { ...criterion, ...updates } : criterion,
      ),
    })),
  addCriterion: () =>
    set((state) => {
      const nextParameter = parameterCatalog.find(
        (parameter) => !state.criteriaDraft.some((criterion) => criterion.param === parameter.id),
      )
      if (!nextParameter) return state
      return {
        criteriaDraft: [
          ...state.criteriaDraft,
          { param: nextParameter.id, min: '', max: '', tolerance: '1', weight: '1' },
        ],
      }
    }),
  removeCriterion: (index) =>
    set((state) => ({
      criteriaDraft: state.criteriaDraft.filter((_, criterionIndex) => criterionIndex !== index),
    })),
}))
