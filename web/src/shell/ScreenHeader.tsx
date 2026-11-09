import type { ReactNode } from 'react'
import { ThemeToggle } from './ThemeToggle'

interface ScreenHeaderProps {
  /** Left side: a title, or the room status on the Live screen. */
  children: ReactNode
  actions?: ReactNode
}

export function ScreenHeader({ children, actions }: ScreenHeaderProps) {
  return (
    <header className="flex min-h-13 items-center justify-between gap-2 pr-1.5 pl-4">
      <div className="flex min-w-0 items-center gap-2.5">{children}</div>
      <div className="flex shrink-0 items-center">
        {actions}
        <ThemeToggle />
      </div>
    </header>
  )
}
