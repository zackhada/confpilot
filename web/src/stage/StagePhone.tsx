import type { CardShownEvent, Speaker } from '@contracts'
import { AnimatePresence, m } from 'motion/react'
import { Captions } from '@/live/Captions'
import { TermCard } from '@/live/TermCard'
import { useCaptions } from '@/live/useCaptions'
import { MAX_FULL_CARDS } from '@/lib/cards'
import { useRoom } from '@/room/store'

const ENTER = { y: 28, scale: 0.985, opacity: 0.88 }
const REST = { y: 0, scale: 1, opacity: 1 }
const SPRING = { type: 'spring', stiffness: 560, damping: 40, mass: 0.7 } as const
const NO_CARDS: CardShownEvent[] = []

interface StagePhoneProps {
  /** Undefined until a speaker has joined and taken this side of the stage. */
  owner: Speaker | undefined
  side: 'left' | 'right'
}

/** One speaker's phone, mirrored for the projector from relayed card.shown events. */
export function StagePhone({ owner, side }: StagePhoneProps) {
  const utterances = useCaptions()
  const terms = useRoom((s) => s.terms)
  const shown = useRoom((s) => (owner ? s.shownByUser[owner.user_id] : undefined)) ?? NO_CARDS
  const full = shown.slice(0, MAX_FULL_CARDS)
  const chips = shown.slice(MAX_FULL_CARDS)
  const fresh = new Set(shown.map((card) => card.term_id))
  const headingId = `stage-phone-${side}`

  return (
    <section
      aria-labelledby={headingId}
      className="flex min-h-0 w-[26.5rem] flex-col overflow-hidden rounded-[2.75rem] border-[3px] border-rule bg-hall shadow-lift"
    >
      <header className="flex items-baseline justify-between px-7 pt-6 pb-2">
        <h2 id={headingId} className="font-display text-3xl">
          {owner ? `${owner.name}’s phone` : 'Open seat'}
        </h2>
        {owner && (
          <p className="tabular text-(length:--text-note) font-semibold text-ink-soft">
            {shown.length} {shown.length === 1 ? 'card' : 'cards'}
          </p>
        )}
      </header>

      {owner ? (
        <>
          <Captions
            utterances={utterances}
            knowledge={{}}
            freshTermIds={fresh}
            emptyHint="Waiting for someone to speak."
            className="px-7 [--text-caption-now:1.5rem] [--text-caption-past:1.0625rem]"
          />
          {chips.length > 0 && (
            <ul aria-label="Earlier terms" className="flex gap-2 overflow-hidden px-7 pb-2">
              {chips.map((card) => (
                <li
                  key={card.card_id}
                  className="shrink-0 rounded-(--radius-chip) border border-rule px-3 py-1.5 text-(length:--text-note) font-semibold"
                >
                  {terms[card.term_id]?.term ?? card.term_id}
                </li>
              ))}
            </ul>
          )}
          <ul aria-label={`Cards shown to ${owner.name}`} className="flex flex-col gap-2 px-5 pb-6">
            <AnimatePresence initial={false} mode="popLayout">
              {[...full].reverse().map((card, index, list) => (
                <m.li
                  key={card.card_id}
                  layout="position"
                  initial={ENTER}
                  animate={REST}
                  exit={{ opacity: 0, transition: { duration: 0.12 } }}
                  transition={SPRING}
                >
                  <TermCard
                    card={card}
                    latencyMs={card.word_to_card_ms}
                    term={terms[card.term_id]}
                    lit={index === list.length - 1}
                    lang={null}
                    terms={terms}
                    knowledge={{}}
                  />
                </m.li>
              ))}
            </AnimatePresence>
          </ul>
        </>
      ) : (
        <div className="flex flex-1 flex-col justify-end px-7 pb-8">
          <p className="max-w-[20ch] text-(length:--text-lead) text-ink-soft">
            Scan the code to join. This phone shows what you see.
          </p>
        </div>
      )}
    </section>
  )
}
