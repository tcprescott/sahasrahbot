import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from 'react'
import { readStored, writeStored } from '../lib/storage'

export type ThemeChoice = 'system' | 'light' | 'dark'
type Resolved = 'light' | 'dark'

const KEY = 'sb.theme'
const QUERY = '(prefers-color-scheme: dark)'

interface ThemeState {
  choice: ThemeChoice
  resolved: Resolved
  setChoice: (choice: ThemeChoice) => void
}

const ThemeContext = createContext<ThemeState | null>(null)

function storedChoice(): ThemeChoice {
  const value = readStored(KEY)
  return value === 'light' || value === 'dark' ? value : 'system'
}

function systemDark(): boolean {
  return typeof matchMedia === 'function' && matchMedia(QUERY).matches
}

export function ThemeProvider({ children }: Readonly<{ children: ReactNode }>) {
  const [choice, setChoice] = useState<ThemeChoice>(storedChoice)
  const [prefersDark, setPrefersDark] = useState(systemDark)

  useEffect(() => {
    if (typeof matchMedia !== 'function') return
    const media = matchMedia(QUERY)
    const onChange = () => setPrefersDark(media.matches)
    media.addEventListener('change', onChange)
    return () => media.removeEventListener('change', onChange)
  }, [])

  const systemTheme: Resolved = prefersDark ? 'dark' : 'light'
  const resolved: Resolved = choice === 'system' ? systemTheme : choice

  useEffect(() => {
    document.documentElement.dataset.theme = resolved
  }, [resolved])

  const updateChoice = useCallback((next: ThemeChoice) => {
    writeStored(KEY, next === 'system' ? null : next)
    setChoice(next)
  }, [])

  const value = useMemo(() => ({ choice, resolved, setChoice: updateChoice }), [choice, resolved, updateChoice])
  return <ThemeContext.Provider value={value}>{children}</ThemeContext.Provider>
}

export function useTheme(): ThemeState {
  const value = useContext(ThemeContext)
  if (!value) throw new Error('useTheme needs a ThemeProvider')
  return value
}
