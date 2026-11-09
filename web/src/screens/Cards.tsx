import { BookmarkCheck } from 'lucide-react'
import { useRoom } from '@/room/store'
import { EmptyState } from './EmptyState'

/** Placeholder for the flashcards slice. It already lists what was saved from Live. */
export function Cards() {
  const saved = useRoom((s) => s.saved)
  const terms = useRoom((s) => s.terms)

  return (
    <EmptyState
      screen="Cards"
      title="Saved words become flashcards."
      hint="Reviews with spaced repetition arrive in the next update."
    >
      {saved.length === 0 ? (
        <p className="max-w-[28ch] text-(length:--text-lead) text-ink-soft">
          Nothing saved yet. Tap Save on any card in Live to keep it for later.
        </p>
      ) : (
        <ul className="flex flex-col gap-2" aria-label="Saved terms">
          {saved.map((termId) => (
            <li
              key={termId}
              className="flex items-start gap-3 rounded-(--radius-card) border border-rule bg-hall-raised px-4 py-3"
            >
              <BookmarkCheck className="mt-1 size-5 shrink-0 text-fresh" aria-hidden="true" />
              <div className="min-w-0">
                <p className="font-display text-xl leading-tight">{terms[termId]?.term ?? termId}</p>
                <p className="text-[0.9375rem] leading-snug text-ink-soft">{terms[termId]?.simple_def}</p>
              </div>
            </li>
          ))}
        </ul>
      )}
    </EmptyState>
  )
}
