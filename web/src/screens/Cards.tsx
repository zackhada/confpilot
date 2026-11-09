import { BadgeCheck, Check, RotateCcw, Zap } from 'lucide-react'
import { MotionConfig } from 'motion/react'
import { useState, type ComponentType } from 'react'
import { Link, useLocation } from 'react-router'
import { buildDeck, grade, nextReviewLabel, preview, type Answer } from '@/cards/deck'
import { FlipCard } from '@/cards/FlipCard'
import { Button } from '@/components/ui/button'
import { useRecap } from '@/recap/useRecap'
import { saveReview } from '@/room/knowledge'
import { serverNow } from '@/room/session'
import { useRoom } from '@/room/store'
import { ScreenHeader } from '@/shell/ScreenHeader'

const ANSWERS: { answer: Answer; label: string; Icon: ComponentType<{ 'aria-hidden'?: 'true' }> }[] = [
  { answer: 'again', label: 'Again', Icon: RotateCcw },
  { answer: 'good', label: 'Good', Icon: Check },
  { answer: 'easy', label: 'Easy', Icon: Zap },
]

interface Session {
  queue: string[]
  total: number
  done: number
  flipped: boolean
  last: string | null
}

/** Flashcards: saved and learn-next terms as a flip deck, scheduled with SM-2. */
export function Cards() {
  const me = useRoom((s) => s.me)
  const terms = useRoom((s) => s.terms)
  const lang = useRoom((s) => s.lang)
  const saved = useRoom((s) => s.saved)
  const knowledge = useRoom((s) => s.knowledge)
  const records = useRoom((s) => s.records)
  const { recap } = useRecap()
  const { search } = useLocation()
  const [session, setSession] = useState<Session | null>(null)

  const deck = buildDeck({ saved, learnNext: recap.learn_next, knowledge, records, now: serverNow() })
  const start = (ids: string[]): void =>
    setSession({ queue: ids, total: ids.length, done: 0, flipped: false, last: null })
  const current = session?.queue[0]

  const answerCard = (answer: Answer): void => {
    if (!session || !current || !me) return
    const next = grade(records[current], me.user_id, current, answer, serverNow())
    saveReview(next)
    const rest = session.queue.slice(1)
    const name = terms[current]?.term ?? current
    setSession({
      ...session,
      // "Again" sends the card to the back of today's deck.
      queue: answer === 'again' ? [...rest, current] : rest,
      done: answer === 'again' ? session.done : session.done + 1,
      flipped: false,
      last: next.learned ? `${name} is learned.` : `${name} comes back ${nextReviewLabel(next)}.`,
    })
  }

  const header = (
    <ScreenHeader>
      <h1 className="font-display text-xl">Cards</h1>
      {session && current && (
        <p className="tabular text-(length:--text-note) font-semibold text-ink-soft">
          {session.done + 1} of {session.total}
        </p>
      )}
    </ScreenHeader>
  )

  if (session && current && me) {
    const labels = preview(records[current], me.user_id, current, serverNow())
    return (
      <MotionConfig reducedMotion="user">
        {header}
        <div className="px-safe flex min-h-0 flex-1 flex-col pb-4">
          <progress className="sr-only" aria-label="Deck progress" max={session.total} value={session.done} />
          <div aria-hidden="true" className="mb-4 h-1.5 overflow-hidden rounded-full bg-hall-raised">
            <div
              className="h-full origin-left rounded-full bg-fresh transition-transform duration-200"
              style={{ transform: `scaleX(${session.done / session.total})` }}
            />
          </div>
          <FlipCard
            key={`${current}-${session.done}-${session.queue.length}`}
            term={terms[current]}
            termId={current}
            lang={lang}
            flipped={session.flipped}
            onFlip={() => setSession({ ...session, flipped: true })}
          />
          <p aria-live="polite" className="min-h-10 py-2 text-(length:--text-note) text-ink-soft">{session.last}</p>
          {session.flipped ? (
            <div className="grid grid-cols-3 gap-2">
              {ANSWERS.map(({ answer, label, Icon }) => (
                <Button
                  key={answer}
                  variant={answer === 'good' ? 'primary' : 'quiet'}
                  onClick={() => answerCard(answer)}
                  className="min-h-16 flex-col gap-1 px-1"
                >
                  <span className="flex items-center gap-1.5">
                    <Icon aria-hidden="true" />
                    {label}
                  </span>
                  <span className="text-(length:--text-note) font-medium opacity-80">{labels[answer]}</span>
                </Button>
              ))}
            </div>
          ) : (
            <Button variant="primary" size="lg" className="min-h-16 w-full" onClick={() => setSession({ ...session, flipped: true })}>
              Show the answer
            </Button>
          )}
        </div>
      </MotionConfig>
    )
  }

  const finished = session !== null
  const nothing = deck.due.length + deck.later.length + deck.learned.length === 0
  return (
    <>
      {header}
      <div className="px-safe flex min-h-0 flex-1 flex-col overflow-y-auto pb-5">
        <h2 className="max-w-[14ch] pt-3 font-display text-(length:--text-title) leading-[1.05]">
          {finished ? 'Deck done.' : nothing ? 'Saved words become flashcards.' : deck.due.length > 0 ? `${deck.due.length} to review.` : 'All caught up.'}
        </h2>
        <p className="max-w-[30ch] pt-4 text-(length:--text-lead) text-ink-soft">
          {finished
            ? `You reviewed ${session.done} ${session.done === 1 ? 'card' : 'cards'}. They come back when you are about to forget them.`
            : nothing
              ? 'Nothing saved yet. Tap Save on any card in Live to keep it for later.'
              : `${deck.later.length} waiting for another day.`}
        </p>
        {deck.learned.length > 0 && (
          <p className="flex items-center gap-2 pt-4 font-semibold text-known">
            <BadgeCheck className="size-5" aria-hidden="true" />
            {deck.learned.length} learned: {deck.learned.map((id) => terms[id]?.term ?? id).join(', ')}
          </p>
        )}
        <div className="mt-auto flex flex-col gap-2 pt-8">
          {deck.due.length > 0 && (
            <Button variant="primary" size="lg" className="w-full" onClick={() => start(deck.due)}>
              {finished ? 'Review the rest' : 'Start reviewing'}
            </Button>
          )}
          {deck.due.length === 0 && deck.later.length > 0 && (
            <Button size="lg" className="w-full" onClick={() => start(deck.later)}>
              Review anyway
            </Button>
          )}
          <Button asChild size="lg" variant={deck.due.length > 0 ? 'ghost' : 'quiet'} className="w-full">
            <Link to={{ pathname: '/', search }}>Back to Live</Link>
          </Button>
        </div>
      </div>
    </>
  )
}
