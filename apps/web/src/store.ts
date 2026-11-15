import { create } from 'zustand'
import { parameterCatalog, type CalibrationInstrument, type ModeId, type ParamId } from './api'

export type SelectedMode = ModeId | 'custom'

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
  max: '15',
  tolerance: '10',
  weight: '1',
}

interface AppStore {
  selectedMode: SelectedMode
  criteriaDraft: CriterionDraft[]
  bareSoilOnly: boolean
  calibrationInstrument: CalibrationInstrument | 'all'
  setSelectedMode: (mode: SelectedMode) => void
  setBareSoilOnly: (bareSoilOnly: boolean) => void
  setCalibrationInstrument: (instrument: CalibrationInstrument | 'all') => void
  updateCriterion: (index: number, updates: Partial<CriterionDraft>) => void
  addCriterion: () => void
  removeCriterion: (index: number) => void
}

export const useAppStore = create<AppStore>((set) => ({
  selectedMode: 'robotics',
  criteriaDraft: [initialCriterion],
  bareSoilOnly: true,
  calibrationInstrument: 'all',
  setSelectedMode: (selectedMode) => set({ selectedMode }),
  setBareSoilOnly: (bareSoilOnly) => set({ bareSoilOnly }),
  setCalibrationInstrument: (calibrationInstrument) =>
    set({ calibrationInstrument }),
  updateCriterion: (index, updates) =>
    set((state) => ({
      criteriaDraft: state.criteriaDraft.map((criterion, criterionIndex) =>
        criterionIndex === index ? { ...criterion, ...updates } : criterion,
      ),
    })),
  addCriterion: () =>
    set((state) => {
      const nextParameter = parameterCatalog.find(
        (parameter) =>
          !state.criteriaDraft.some(
            (criterion) => criterion.param === parameter.id,
          ),
      )
      if (!nextParameter) return state

      return {
        criteriaDraft: [
          ...state.criteriaDraft,
          {
            ...initialCriterion,
            param: nextParameter.id,
            min: '',
            max: '',
            tolerance: '1',
            weight: '1',
          },
        ],
      }
    }),
  removeCriterion: (index) =>
    set((state) => ({
      criteriaDraft: state.criteriaDraft.filter(
        (_, criterionIndex) => criterionIndex !== index,
      ),
    })),
}))
