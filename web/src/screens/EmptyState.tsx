import { Captions } from 'lucide-react'
import type { ReactNode } from 'react'
import { Link, useLocation } from 'react-router'
import { Button } from '@/components/ui/button'
import { ScreenHeader } from '@/shell/ScreenHeader'

interface EmptyStateProps {
  /** Screen name, shown small in the header. */
  screen: string
  /** The one thing this screen will do, as a sentence. */
  title: string
  children: ReactNode
  /** What to do now so the screen has something to show. */
  hint: string
}

/** Shared empty screen: says what will appear here and sends the person back to Live. */
export function EmptyState({ screen, title, children, hint }: EmptyStateProps) {
  const { search } = useLocation()
  return (
    <>
      <ScreenHeader>
        <p className="font-display text-xl">{screen}</p>
      </ScreenHeader>
      <div className="px-safe flex min-h-0 flex-1 flex-col overflow-y-auto pb-5">
        <h1 className="max-w-[14ch] pt-3 font-display text-(length:--text-title) leading-[1.05]">{title}</h1>
        <div className="pt-6">{children}</div>
        <div className="mt-auto pt-8">
          <p className="pb-3 text-(length:--text-note) text-ink-soft">{hint}</p>
          <Button asChild size="lg" className="w-full">
            <Link to={{ pathname: '/', search }}>
              <Captions aria-hidden="true" />
              Back to Live
            </Link>
          </Button>
        </div>
      </div>
    </>
  )
}
