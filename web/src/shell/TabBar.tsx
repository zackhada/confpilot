import { Captions, Layers, MessageCircleQuestion, NotebookText } from 'lucide-react'
import type { ComponentType } from 'react'
import { NavLink, useLocation } from 'react-router'
import { cn } from '@/shared/cn'

interface Tab {
  to: string
  label: string
  Icon: ComponentType<{ className?: string; 'aria-hidden'?: 'true' }>
}

const TABS: Tab[] = [
  { to: '/', label: 'Live', Icon: Captions },
  { to: '/recap', label: 'Recap', Icon: NotebookText },
  { to: '/cards', label: 'Cards', Icon: Layers },
  { to: '/ask', label: 'Ask', Icon: MessageCircleQuestion },
]

/** Bottom tab bar. It sits in the thumb zone and keeps the room code in the URL. */
export function TabBar() {
  const { search } = useLocation()
  return (
    <nav aria-label="Main" className="pb-safe border-t border-rule bg-hall-sunk">
      <ul className="mx-auto grid max-w-xl grid-cols-4">
        {TABS.map(({ to, label, Icon }) => (
          <li key={to}>
            <NavLink
              to={{ pathname: to, search }}
              end={to === '/'}
              className={({ isActive }) =>
                cn(
                  'relative flex min-h-14 flex-col items-center justify-center gap-0.5 px-2',
                  'text-(length:--text-note) -outline-offset-4',
                  isActive ? 'font-bold text-ink' : 'font-medium text-ink-soft',
                )
              }
            >
              {({ isActive }) => (
                <>
                  <span
                    aria-hidden="true"
                    className={cn(
                      'absolute top-0 left-1/2 h-[3px] w-10 -translate-x-1/2 rounded-b-full bg-fresh transition-opacity duration-150',
                      isActive ? 'opacity-100' : 'opacity-0',
                    )}
                  />
                  <Icon className="size-[22px]" aria-hidden="true" />
                  <span>{label}</span>
                </>
              )}
            </NavLink>
          </li>
        ))}
      </ul>
    </nav>
  )
}
