import type { KnowledgeStatus, Term } from '@contracts'
import { Check, Lock, Sparkles } from 'lucide-react'
import { motion } from 'motion/react'
import type { ComponentType } from 'react'
import { Button } from '@/components/ui/button'
import { cn } from '@/shared/cn'
import { useTermSheet } from '@/shared/useTermSheet'
import { mapBands, type BandKey, type MapBand } from './probeLogic'

interface BandLook {
  title: string
  note: string
  Icon: ComponentType<{ className?: string; 'aria-hidden'?: 'true' }>
  band: string
  icon: string
  chip: string
}

// Three strata, far to near. Each has its own icon and words, so the colours (grey, amber,
// green) are never the only way to tell them apart.
const LOOKS: Record<BandKey, BandLook> = {
  beyond: {
    title: 'Later',
    note: 'Builds on things you have not met yet',
    Icon: Lock,
    band: 'bg-hall-sunk text-beyond border border-b-0 border-dashed border-rule',
    icon: 'text-beyond',
    chip: 'text-beyond',
  },
  frontier: {
    title: 'Next for you',
    note: 'You know what these build on. Cards start here.',
    Icon: Sparkles,
    band: 'on-lit bg-lit text-lit-ink shadow-lift',
    icon: 'text-lit-fresh',
    chip: 'border border-lit-fresh text-lit-fresh font-semibold',
  },
  known: {
    title: 'You know',
    note: 'No cards for these',
    Icon: Check,
    band: 'bg-[color-mix(in_oklab,var(--known)_16%,var(--hall))] text-ink border border-[color-mix(in_oklab,var(--known)_45%,transparent)]',
    icon: 'text-known',
    chip: 'text-ink',
  },
}

// One orchestrated reveal: the ground you stand on first, then the lit edge, then the distance.
const RISE_ORDER: Record<BandKey, number> = { known: 0, frontier: 1, beyond: 2 }

function Band({ band }: { band: MapBand }) {
  const look = LOOKS[band.key]
  const openTerm = useTermSheet((s) => s.open)
  const more = band.count - band.sample.length
  const headingId = `map-${band.key}`
  return (
    <motion.section
      aria-labelledby={headingId}
      initial={{ y: 28, opacity: 0 }}
      animate={{ y: 0, opacity: 1 }}
      transition={{ type: 'spring', stiffness: 260, damping: 30, delay: 0.15 + RISE_ORDER[band.key] * 0.16 }}
      className={cn('-mt-4 rounded-t-[1.75rem] px-5 pt-4 pb-8 first:mt-0 last:rounded-b-[1.75rem] last:pb-5', look.band)}
    >
      <div className="flex items-center gap-2.5">
        <look.Icon className={cn('size-5 shrink-0', look.icon)} aria-hidden="true" />
        <h2 id={headingId} className="flex-1 font-display text-xl">{look.title}</h2>
        <p className="tabular text-3xl leading-none font-bold">
          {band.count}
          <span className="sr-only"> terms</span>
        </p>
      </div>
      <p className="pt-0.5 pl-[1.875rem] text-(length:--text-note) opacity-80">{look.note}</p>
      <ul className="flex flex-wrap gap-x-2 gap-y-1.5 pt-3">
        {band.sample.map((term: Term) => (
          <li key={term.id}>
            {band.key === 'frontier' ? (
              <button
                type="button"
                onClick={() => openTerm(term.id)}
                className={cn('min-h-11 rounded-(--radius-chip) px-3.5 text-(length:--text-note)', look.chip)}
              >
                {term.term}
              </button>
            ) : (
              <span className={cn('inline-block py-0.5 pr-2 text-[0.9375rem]', look.chip)}>{term.term}</span>
            )}
          </li>
        ))}
        {more > 0 && <li className="self-center text-(length:--text-note) opacity-80">and {more} more</li>}
      </ul>
    </motion.section>
  )
}

interface MapStepProps {
  terms: readonly Term[]
  knowledge: Readonly<Record<string, KnowledgeStatus>>
  onDone: () => void
}

/** "Your map": what you know, what is within reach, and what comes later. */
export function MapStep({ terms, knowledge, onDone }: MapStepProps) {
  const bands = mapBands(terms, knowledge)
  const count = (key: BandKey): number => bands.find((b) => b.key === key)?.count ?? 0
  return (
    <div className="px-safe flex min-h-0 flex-1 flex-col pb-5">
      <h1 className="pt-2 font-display text-(length:--text-title) leading-[1.05]">Your map</h1>
      <p className="max-w-[32ch] pt-2 pb-4 text-(length:--text-lead) text-ink-soft">
        You know {count('known')} terms, and {count('frontier')} more are within reach.
      </p>
      <div className="min-h-0 flex-1 overflow-y-auto">
        {bands.map((band) => (
          <Band key={band.key} band={band} />
        ))}
      </div>
      <Button variant="primary" size="lg" className="mt-4 w-full" onClick={onDone}>
        Start listening
      </Button>
    </div>
  )
}
