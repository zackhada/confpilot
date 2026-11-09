import { create } from 'zustand'

interface TermSheetStore {
  termId: string | null
  open: (termId: string) => void
  close: () => void
}

/** Any screen can open a term's card: `useTermSheet((s) => s.open)(termId)`. */
export const useTermSheet = create<TermSheetStore>((set) => ({
  termId: null,
  open: (termId) => set({ termId }),
  close: () => set({ termId: null }),
}))
