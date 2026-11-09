import type { Term } from '@contracts'
import { AnimatePresence, motion } from 'motion/react'
import { useEffect, useState } from 'react'
import type { LiveCard } from '@/lib/cards'
import { cardPainted, markKnown, reopenCard, toggleSave } from '@/room/session'
import { cardLatencyMs, useRoom } from '@/room/store'
import { TermCard } from './TermCard'
import { usePaintStamp } from './usePaintStamp'

// The card is fully legible on its first painted frame; the spring only settles its position.
const ENTER = { y: 28, scale: 0.985, opacity: 0.88 }
const REST = { y: 0, scale: 1, opacity: 1 }
const SPRING = { type: 'spring', stiffness: 560, damping: 40, mass: 0.7 } as const
const LEAVE = { opacity: 0, scale: 0.96, transition: { duration: 0.12 } }

interface StackedCardProps {
  card: LiveCard
  lit: boolean
  onOpen: () => void
}

function StackedCard({ card, lit, onOpen }: StackedCardProps) {
  const term = useRoom((s) => s.terms[card.term_id])
  const terms = useRoom((s) => s.terms)
  const knowledge = useRoom((s) => s.knowledge)
  const lang = useRoom((s) => s.lang)
  const saved = useRoom((s) => s.saved.includes(card.term_id))
  usePaintStamp(card.rendered_at === null, () => cardPainted(card.card_id))

  return (
    <motion.li layout="position" initial={ENTER} animate={REST} exit={LEAVE} transition={SPRING}>
      <TermCard
        card={card}
        latencyMs={cardLatencyMs(card)}
        term={term}
        lit={lit}
        lang={lang}
        terms={terms}
        knowledge={knowledge}
        saved={saved}
        onOpen={onOpen}
        onKnow={() => markKnown(card.term_id)}
        onSave={() => toggleSave(card.term_id)}
      />
    </motion.li>
  )
}

function Chip({ card, term }: { card: LiveCard; term: Term | undefined }) {
  const count = useRoom((s) => s.heard[card.term_id] ?? 1)
  return (
    <motion.li
      layout="position"
      initial={{ opacity: 0, scale: 0.9 }}
      animate={{ opacity: 1, scale: 1 }}
      exit={{ opacity: 0 }}
      transition={{ duration: 0.16 }}
      className="shrink-0"
    >
      <button
        type="button"
        onClick={() => reopenCard(card.card_id)}
        aria-label={`${term?.term ?? card.term_id}, heard ${count} ${count === 1 ? 'time' : 'times'}. Open the card again`}
        className="inline-flex min-h-11 items-center gap-1.5 rounded-(--radius-chip) border border-rule px-3.5 text-(length:--text-note) font-semibold text-ink"
      >
        {term?.term ?? card.term_id}
        {count > 1 && <span className="tabular font-medium text-ink-soft">×{count}</span>}
      </button>
    </motion.li>
  )
}

/** Up to three cards, newest at the bottom next to the thumb; older ones settle into chips. */
export function CardStack() {
  const full = useRoom((s) => s.stack.full)
  const chips = useRoom((s) => s.stack.chips)
  const terms = useRoom((s) => s.terms)
  const newestId = full[0]?.card_id ?? null
  // A new card always takes the light; tapping an older card borrows it until the next one.
  const [opened, setOpened] = useState<{ id: string; whileNewest: string | null } | null>(null)
  const borrowed = opened?.whileNewest === newestId && full.some((c) => c.card_id === opened.id)
  const litId = borrowed && opened ? opened.id : newestId

  // A short buzz tells someone looking at the stage that a card arrived (where supported).
  useEffect(() => {
    if (newestId) navigator.vibrate?.(12)
  }, [newestId])
  if (full.length === 0 && chips.length === 0) {
    return (
      <p className="px-safe pb-3 text-(length:--text-note) text-ink-soft">
        Cards appear here for words that are new to you.
      </p>
    )
  }

  return (
    <section aria-label="Terms new to you" className="pb-3">
      {chips.length > 0 && (
        <ul aria-label="Earlier terms" className="scrollbar-none px-safe flex gap-2 overflow-x-auto pb-2">
          <AnimatePresence initial={false} mode="popLayout">
            {chips.map((card) => (
              <Chip key={card.card_id} card={card} term={terms[card.term_id]} />
            ))}
          </AnimatePresence>
        </ul>
      )}
      <ul className="px-safe flex flex-col gap-2">
        <AnimatePresence initial={false} mode="popLayout">
          {[...full].reverse().map((card) => (
            <StackedCard
              key={card.card_id}
              card={card}
              lit={card.card_id === litId}
              onOpen={() => setOpened({ id: card.card_id, whileNewest: newestId })}
            />
          ))}
        </AnimatePresence>
      </ul>
    </section>
  )
}
