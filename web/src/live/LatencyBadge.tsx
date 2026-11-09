import { Hourglass, Zap } from 'lucide-react'
import { cn } from '@/shared/cn'

/** The promise: 95% of cards are on screen within 800 ms of the word being spoken. */
export const LATENCY_TARGET_MS = 800

interface LatencyBadgeProps {
  /** Null until the card's first paint has been stamped. */
  ms: number | null
  className?: string
}

/** Word-to-card time for one card. The icon changes with the state, not just the colour. */
export function LatencyBadge({ ms, className }: LatencyBadgeProps) {
  if (ms === null) return null
  const onTarget = ms <= LATENCY_TARGET_MS
  const Icon = onTarget ? Zap : Hourglass
  return (
    <span
      className={cn(
        'tabular inline-flex shrink-0 items-center gap-1 text-(length:--text-note) font-semibold whitespace-nowrap',
        className,
      )}
    >
      <Icon className="size-3.5" aria-hidden="true" />
      <span aria-hidden="true">{ms} ms</span>
      <span className="sr-only">
        Shown {ms} milliseconds after the word was spoken{onTarget ? '' : ', slower than the target'}
      </span>
    </span>
  )
}
