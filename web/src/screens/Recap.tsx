import { ChevronRight, CloudOff } from 'lucide-react'
import { Link, useLocation } from 'react-router'
import { Button } from '@/components/ui/button'
import { useRecap } from '@/recap/useRecap'
import { useRoom } from '@/room/store'
import { ScreenHeader } from '@/shell/ScreenHeader'
import { useTermSheet } from '@/shared/useTermSheet'

const MOST_HEARD_LIMIT = 6

/** The pay-off after a conversation: how much was new, what to learn next, what came up most. */
export function Recap() {
  const { recap, source } = useRecap()
  const terms = useRoom((s) => s.terms)
  const openTerm = useTermSheet((s) => s.open)
  const { search } = useLocation()
  const name = (id: string): string => terms[id]?.term ?? id
  const top = recap.heard[0]
  const mostHeard = recap.heard.slice(0, MOST_HEARD_LIMIT)
  const peak = Math.max(1, ...mostHeard.map((h) => h.count))

  return (
    <>
      <ScreenHeader>
        <p className="font-display text-xl">Recap</p>
      </ScreenHeader>
      <div className="px-safe min-h-0 flex-1 overflow-y-auto pb-6">
        <h1 className="pt-2 font-display leading-none">
          <span className="block text-(length:--text-lead) text-ink-soft font-sans">You heard</span>
          <span className="tabular block pt-1 text-[5.5rem]">{recap.new_term_count}</span>
          <span className="block text-3xl">{recap.new_term_count === 1 ? 'new term' : 'new terms'}</span>
        </h1>

        {recap.heard.length === 0 ? (
          <div className="pt-8">
            <p className="max-w-[28ch] pb-5 text-(length:--text-lead) text-ink-soft">
              Nothing to recap yet. Listen to a conversation and this page fills in by itself.
            </p>
            <Button asChild variant="primary" size="lg" className="w-full">
              <Link to={{ pathname: '/', search }}>Go to Live</Link>
            </Button>
          </div>
        ) : (
          <>
            {top && (
              <p className="pt-3 text-(length:--text-lead) text-ink-soft">
                <span className="font-semibold text-ink">{name(top.term_id)}</span> came up{' '}
                {top.count === 1 ? 'once' : `${top.count} times`}.
              </p>
            )}

            {recap.learn_next.length > 0 && (
              <section aria-labelledby="learn-next" className="on-lit mt-7 rounded-(--radius-card) bg-lit text-lit-ink shadow-lift">
                <h2 id="learn-next" className="px-4 pt-3.5 pb-1 font-display text-xl">Learn next</h2>
                <p className="px-4 pb-2 text-(length:--text-note) text-lit-soft">
                  You heard these, and you already know what they build on.
                </p>
                <ul>
                  {recap.learn_next.map((id) => (
                    <li key={id} className="border-t border-lit-rule">
                      <button
                        type="button"
                        onClick={() => openTerm(id)}
                        className="flex min-h-14 w-full items-center gap-3 px-4 py-2.5 text-left -outline-offset-4"
                      >
                        <span className="min-w-0 flex-1">
                          <span className="block font-semibold">{name(id)}</span>
                          <span className="line-clamp-1 text-(length:--text-note) text-lit-soft">
                            {terms[id]?.simple_def}
                          </span>
                        </span>
                        <ChevronRight className="size-5 shrink-0 text-lit-soft" aria-hidden="true" />
                      </button>
                    </li>
                  ))}
                </ul>
              </section>
            )}

            <section aria-labelledby="most-heard" className="mt-7">
              <h2 id="most-heard" className="pb-1 font-display text-xl">Most heard</h2>
              <ol>
                {mostHeard.map(({ term_id, count }) => (
                  <li key={term_id} className="border-b border-rule">
                    <button
                      type="button"
                      onClick={() => openTerm(term_id)}
                      className="relative flex min-h-12 w-full items-center justify-between gap-4 py-2 text-left"
                    >
                      <span
                        aria-hidden="true"
                        className="absolute inset-y-1.5 left-0 -z-0 origin-left rounded-r-md bg-hall-raised"
                        style={{ width: '100%', transform: `scaleX(${count / peak})` }}
                      />
                      <span className="relative pl-2.5 font-semibold">{name(term_id)}</span>
                      <span className="tabular relative text-(length:--text-note) font-semibold text-ink-soft">
                        {count === 1 ? 'once' : `${count} times`}
                      </span>
                    </button>
                  </li>
                ))}
              </ol>
            </section>

            {source === 'local' && (
              <p className="flex items-center gap-2 pt-5 text-(length:--text-note) text-ink-soft">
                <CloudOff className="size-4 shrink-0" aria-hidden="true" />
                Counted on this phone. The room&rsquo;s full recap loads when the server is reachable.
              </p>
            )}
          </>
        )}
      </div>
    </>
  )
}
