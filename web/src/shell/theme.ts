import { create } from 'zustand'
import { readStored, writeStored } from '@/shared/storage'

export type Theme = 'dark' | 'light'

const THEME_KEY = 'confpilot.theme'
const THEME_COLORS: Record<Theme, string> = { dark: '#0c1326', light: '#f4efe4' }

function initialTheme(): Theme {
  return readStored(THEME_KEY) === 'light' ? 'light' : 'dark'
}

function applyTheme(theme: Theme): void {
  document.documentElement.setAttribute('data-theme', theme)
  document
    .querySelector('meta[name="theme-color"]')
    ?.setAttribute('content', THEME_COLORS[theme])
}

interface ThemeStore {
  theme: Theme
  toggle: () => void
}

/** Dark is the default because the app is used in dim halls; the choice is remembered. */
export const useTheme = create<ThemeStore>((set, get) => ({
  theme: initialTheme(),
  toggle: () => {
    const next: Theme = get().theme === 'dark' ? 'light' : 'dark'
    writeStored(THEME_KEY, next)
    applyTheme(next)
    set({ theme: next })
  },
}))

applyTheme(useTheme.getState().theme)
