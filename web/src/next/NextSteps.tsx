import type { KnowledgeStatus } from '@contracts'
import { BookOpen, CalendarClock, Check, ChevronRight, X } from 'lucide-react'
import { useState } from 'react'
import { Link, useLocation } from 'react-router'
import { recordStatus } from '@/room/knowledge'
import { useRoom } from '@/room/store'
import { readStoredJson, writeStored } from '@/shared/storage'
import { bookLink } from './catalog'
import { buildPlan } from './plan'

const LEVEL_KEY = 'nautilus.level'
const CHECK_LIMIT = 5

interface Level {
  current: number
  goal: number
}

const isLevel = (value: unknown): value is Level =>
  typeof value === 'object' &&
  value !== null &&
  typeof (value as Level).current === 'number' &&
  typeof (value as Level).goal === 'number'

interface Props {
  /** Heard term ids, most heard first. */
  heardIds: readonly string[]
}

/** After the recap: where you are, where you want to be, and the next sessions and book to get there. */
export function NextSteps({ heardIds }: Props) {
  const terms = useRoom((s) => s.terms)
  const knowledge = useRoom((s) => s.knowledge)
  const { search } = useLocation()
  const [level, setLevel] = useState<Level>(() => readStoredJson(LEVEL_KEY, isLevel) ?? { current: 4, goal: 7 })

  const update = (patch: Partial<Level>): void => {
    const next = { ...level, ...patch }
    setLevel(next)
    writeStored(LEVEL_KEY, JSON.stringify(next))
  }

  const name = (id: string): string => terms[id]?.term ?? id
  const checkIds = heardIds.slice(0, CHECK_LIMIT)
  const gapIds = heardIds.filter((id) => knowledge[id] !== 'known')
  const plan = buildPlan({ gapIds, ...level, categoryOf: (id) => terms[id]?.category })
  const reached = level.goal <= level.current

  return (
    <section aria-labelledby="next-move" className="mt-8">
      <h2 id="next-move" className="font-display text-xl">Your next move</h2>

      <div className="grid gap-3 pt-3">
        <LevelSlider label="Where you are now" value={level.current} onChange={(current) => update({ current })} />
        <LevelSlider label="Where you want to be" value={level.goal} onChange={(goal) => update({ goal })} />
      </div>

      {checkIds.length > 0 && (
        <>
          <h3 className="pt-5 pb-1 font-semibold">Do you know these?</h3>
          <ul>
            {checkIds.map((id) => (
              <KnowCheck key={id} label={name(id)} status={knowledge[id]} onSet={(status) => recordStatus(id, status, 'tap')} />
            ))}
          </ul>
        </>
      )}

      {reached ? (
        <p className="pt-5 text-ink-soft">You are where you wanted to be. Raise the goal to get a new plan.</p>
      ) : (
        <>
          {plan.sessions.length > 0 && (
            <>
              <h3 className="pt-5 pb-1 font-semibold">Go to these next</h3>
              <ul className="grid gap-2">
                {plan.sessions.map(({ session, covers }) => (
                  <li key={session.id} className="rounded-(--radius-card) bg-hall-raised px-4 py-3">
                    <p className="flex items-center gap-2 text-(length:--text-note) text-ink-soft">
                      <CalendarClock className="size-4 shrink-0" aria-hidden="true" />
                      {session.kind} · {session.when} · {session.room}
                    </p>
                    <p className="pt-1 font-semibold">{session.title}</p>
                    <p className="pt-1 text-(length:--text-note) text-ink-soft">Covers {covers.slice(0, 3).map(name).join(', ')}</p>
                  </li>
                ))}
              </ul>
            </>
          )}

          {plan.book && (
            <>
              <h3 className="pt-5 pb-1 font-semibold">Read this</h3>
              <a
                href={bookLink(plan.book)}
                target="_blank"
                rel="noreferrer"
                className="flex min-h-14 items-center gap-3 rounded-(--radius-card) bg-hall-raised px-4 py-3"
              >
                <BookOpen className="size-5 shrink-0" aria-hidden="true" />
                <span className="min-w-0 flex-1">
                  <span className="block font-semibold">{plan.book.title}</span>
                  <span className="block text-(length:--text-note) text-ink-soft">{plan.book.author}</span>
                </span>
                <ChevronRight className="size-5 shrink-0 text-ink-soft" aria-hidden="true" />
              </a>
            </>
          )}

          {plan.sessions.length === 0 && !plan.book && (
            <p className="pt-5 text-ink-soft">Mark a few terms you don&rsquo;t know yet and the plan fills in.</p>
          )}
        </>
      )}

      <Link
        to={{ pathname: '/cards', search }}
        className="mt-5 flex min-h-12 items-center justify-between border-y border-rule py-2 font-semibold"
      >
        Keep it going: review your flashcards
        <ChevronRight className="size-5 shrink-0 text-ink-soft" aria-hidden="true" />
      </Link>
    </section>
  )
}

interface LevelSliderProps {
  label: string
  value: number
  onChange: (value: number) => void
}

function LevelSlider({ label, value, onChange }: LevelSliderProps) {
  return (
    <label className="grid gap-1">
      <span className="flex justify-between text-(length:--text-note) text-ink-soft">
        {label}
        <span className="tabular font-semibold text-ink">{value} / 10</span>
      </span>
      <input
        type="range"
        min={1}
        max={10}
        step={1}
        value={value}
        onChange={(e) => onChange(Number(e.target.value))}
        className="min-h-11 w-full accent-current"
      />
    </label>
  )
}

interface KnowCheckProps {
  label: string
  status: KnowledgeStatus | undefined
  onSet: (status: KnowledgeStatus) => void
}

function KnowCheck({ label, status, onSet }: KnowCheckProps) {
  const known = status === 'known'
  return (
    <li className="flex min-h-12 items-center gap-2 border-b border-rule">
      <span className="min-w-0 flex-1 font-semibold">{label}</span>
      <button
        type="button"
        aria-pressed={known}
        aria-label={`I know ${label}`}
        onClick={() => onSet('known')}
        className={`grid size-11 place-items-center rounded-full ${known ? 'bg-ink text-hall' : 'text-ink-soft'}`}
      >
        <Check className="size-5" aria-hidden="true" />
      </button>
      <button
        type="button"
        aria-pressed={!known && status !== undefined}
        aria-label={`I don't know ${label}`}
        onClick={() => onSet('unknown')}
        className={`grid size-11 place-items-center rounded-full ${!known && status !== undefined ? 'bg-ink text-hall' : 'text-ink-soft'}`}
      >
        <X className="size-5" aria-hidden="true" />
      </button>
    </li>
  )
}
