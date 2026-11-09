import type { ReactNode } from 'react'
import { ScreenHeader } from '@/shell/ScreenHeader'

interface ComingSoonProps {
  title: string
  children: ReactNode
}

/** Temporary screen body until the slice for this tab lands. */
export function ComingSoon({ title, children }: ComingSoonProps) {
  return (
    <>
      <ScreenHeader>
        <h1 className="font-display text-xl">{title}</h1>
      </ScreenHeader>
      <div className="px-safe flex flex-1 flex-col justify-end pb-8">
        <p className="max-w-[28ch] text-(length:--text-lead) text-ink-soft">{children}</p>
      </div>
    </>
  )
}
