import { Moon, Sun } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { useTheme } from './theme'

export function ThemeToggle() {
  const theme = useTheme((s) => s.theme)
  const toggle = useTheme((s) => s.toggle)
  const next = theme === 'dark' ? 'light' : 'dark'
  return (
    <Button variant="ghost" size="icon" onClick={toggle} aria-label={`Switch to ${next} theme`}>
      {theme === 'dark' ? <Sun aria-hidden="true" /> : <Moon aria-hidden="true" />}
    </Button>
  )
}
