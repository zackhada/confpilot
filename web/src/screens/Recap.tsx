import { useRoom } from '@/room/store'
import { EmptyState } from './EmptyState'

const TOP_TERMS = 5

/** Placeholder for the recap slice. It already counts what this session heard. */
export function Recap() {
  const heard = useRoom((s) => s.heard)
  const terms = useRoom((s) => s.terms)
  const shownCount = useRoom((s) => s.stack.shownTermIds.length)
  const ranked = Object.entries(heard).sort(([, a], [, b]) => b - a).slice(0, TOP_TERMS)

  return (
    <EmptyState
      screen="Recap"
      title="Your talk, as a study plan."
      hint="The full recap, with what to learn next, arrives after the talk."
    >
      {ranked.length === 0 ? (
        <p className="max-w-[28ch] text-(length:--text-lead) text-ink-soft">
          Nothing heard yet. Once people speak, the terms you met are counted here.
        </p>
      ) : (
        <>
          <p className="text-(length:--text-lead)">
            <span className="tabular font-display text-4xl">{shownCount}</span>{' '}
            <span className="text-ink-soft">{shownCount === 1 ? 'term was' : 'terms were'} new to you so far.</span>
          </p>
          <ol className="mt-5 border-t border-rule" aria-label="Most heard terms">
            {ranked.map(([termId, count]) => (
              <li key={termId} className="flex items-baseline justify-between gap-4 border-b border-rule py-3">
                <span className="font-display text-xl">{terms[termId]?.term ?? termId}</span>
                <span className="tabular text-(length:--text-note) font-semibold text-ink-soft">
                  heard {count} {count === 1 ? 'time' : 'times'}
                </span>
              </li>
            ))}
          </ol>
        </>
      )}
    </EmptyState>
  )
}
