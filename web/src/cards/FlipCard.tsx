import type { Lang, Term } from '@contracts'
import { m } from 'motion/react'

interface FlipCardProps {
  term: Term | undefined
  termId: string
  lang: Lang | null
  flipped: boolean
  onFlip: () => void
}

const FACE =
  'on-lit absolute inset-0 flex flex-col rounded-(--radius-card) bg-lit px-5 py-5 text-lit-ink shadow-lift [backface-visibility:hidden]'

/**
 * One flashcard. The flip is a single rotateY (transform only, about a third of a second).
 * With reduced motion the rotation is skipped and the faces swap at once.
 */
export function FlipCard({ term, termId, lang, flipped, onFlip }: FlipCardProps) {
  const name = term?.term ?? termId
  const native = lang ? term?.translations?.[lang] : undefined
  return (
    <div className="min-h-0 flex-1 [perspective:1200px]">
      <m.div
        className="relative h-full [transform-style:preserve-3d]"
        initial={false}
        animate={{ rotateY: flipped ? 180 : 0 }}
        transition={{ duration: 0.34, ease: [0.3, 0.7, 0.2, 1] }}
      >
        <button
          type="button"
          onClick={onFlip}
          disabled={flipped}
          aria-hidden={flipped}
          aria-label={`${name}. Show the answer`}
          className={`${FACE} items-start justify-center text-left`}
        >
          <span className="text-(length:--text-note) text-lit-soft">What does this mean?</span>
          <span className="pt-2 font-display text-[2.75rem] leading-[1.05] break-words">{name}</span>
          {term?.say && (
            <span className="pt-2 text-lit-soft">
              say <span className="font-bold text-lit-ink">{term.say}</span>
            </span>
          )}
        </button>

        <div aria-hidden={!flipped} className={`${FACE} justify-center [transform:rotateY(180deg)]`}>
          <h2 className="font-display text-2xl">{name}</h2>
          <p className="pt-3 text-[1.375rem] leading-snug font-medium">
            {term?.simple_def ?? 'No definition on this phone yet.'}
          </p>
          {native && lang && <p lang={lang} className="pt-2 leading-snug text-lit-soft">{native}</p>}
          {term?.example && <p className="pt-4 leading-snug text-lit-soft">&ldquo;{term.example}&rdquo;</p>}
        </div>
      </m.div>
    </div>
  )
}
