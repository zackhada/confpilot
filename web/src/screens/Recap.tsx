import { useRecap } from '@/recap/useRecap'
import { useRoom } from '@/room/store'
import { ScreenHeader } from '@/shell/ScreenHeader'
import { useTermSheet } from '@/shared/useTermSheet'

export function Recap() {
  const { recap } = useRecap()
  const terms = useRoom((s) => s.terms)
  const knowledge = useRoom((s) => s.knowledge)
  const records = useRoom((s) => s.records)
  const openTerm = useTermSheet((s) => s.open)
  const newTerms = recap.heard.filter(
    ({ term_id }) => knowledge[term_id] !== 'known' && !records[term_id]?.learned,
  )

  return (
    <>
      <ScreenHeader>
        <p className="font-display text-xl">Recap</p>
      </ScreenHeader>
      <div className="px-safe min-h-0 flex-1 overflow-y-auto pb-6">
        <h1 aria-live="polite" className="pt-2 font-display leading-none">
          <span className="block text-(length:--text-lead) text-ink-soft font-sans">You heard</span>
          <span className="tabular block pt-1 text-[5.5rem]">{newTerms.length}</span>
          <span className="block text-3xl">{newTerms.length === 1 ? 'new term' : 'new terms'}</span>
        </h1>

        {newTerms.length > 0 && (
          <ul aria-label="New terms" className="mt-6">
            {newTerms.map(({ term_id }) => (
              <li key={term_id} className="border-b border-rule">
                <button
                  type="button"
                  onClick={() => openTerm(term_id)}
                  className="min-h-12 w-full py-2 text-left font-semibold"
                >
                  {terms[term_id]?.term ?? term_id}
                </button>
              </li>
            ))}
          </ul>
        )}
      </div>
    </>
  )
}
