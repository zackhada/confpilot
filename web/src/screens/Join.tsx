import type { Lang } from '@contracts'
import { Check } from 'lucide-react'
import { RadioGroup } from 'radix-ui'
import { useId, useState, type FormEvent } from 'react'
import { Button } from '@/components/ui/button'
import { parseRoomCode, type Profile } from '@/room/identity'
import { isLang, isPersonaId, LANGUAGES, personaById, PERSONAS, type PersonaId } from '@/room/personas'
import { cn } from '@/shared/cn'
import { ThemeToggle } from '@/shell/ThemeToggle'

interface JoinProps {
  initialRoom: string | null
  onJoin: (profile: Profile, room: string) => void
}

const FIELD =
  'min-h-12 w-full rounded-(--radius-control) border border-rule bg-hall-raised px-3.5 text-(length:--text-lead) text-ink placeholder:text-ink-soft/70'
const LABEL = 'mb-1.5 block text-(length:--text-note) font-semibold text-ink-soft'

/** First screen: pick a room, say who you are, and choose what you already know. */
export function Join({ initialRoom, onJoin }: JoinProps) {
  const ids = { room: useId(), name: useId(), lang: useId(), error: useId() }
  const [room, setRoom] = useState(initialRoom ?? '')
  const [persona, setPersona] = useState<PersonaId>('clayton')
  const [name, setName] = useState('Clayton')
  const [lang, setLang] = useState<Lang | null>(null)
  const [error, setError] = useState<string | null>(null)

  const choosePersona = (value: string): void => {
    if (!isPersonaId(value)) return
    const next = personaById(value)
    // Keep a name the person typed; only swap one persona's name for another's.
    if (name.trim() === '' || PERSONAS.some((p) => p.name === name.trim())) setName(next.name)
    setPersona(next.id)
    setLang(next.lang)
  }

  const submit = (event: FormEvent): void => {
    event.preventDefault()
    const code = parseRoomCode(room)
    if (!code) return setError('Enter the room code from the stage screen, like slc1.')
    if (name.trim() === '') return setError('Enter the name other people will see.')
    onJoin({ name: name.trim().slice(0, 40), persona, lang }, code)
  }

  return (
    <div className="pt-safe mx-auto flex min-h-dvh w-full max-w-xl flex-col bg-hall">
      <header className="flex min-h-13 items-center justify-between pr-1.5 pl-4">
        <p className="font-display text-lg">ConfPilot</p>
        <ThemeToggle />
      </header>

      <form onSubmit={submit} noValidate className="px-safe pb-safe flex flex-1 flex-col">
        <div className="pt-3 pb-6">
          <h1 className="font-display text-(length:--text-title) leading-[1.05]">Stop nodding along.</h1>
          <p className="mt-3 max-w-[30ch] text-(length:--text-lead) text-ink-soft">
            Live captions, with a card for each word you don&rsquo;t know yet.
          </p>
        </div>

        <div className="grid grid-cols-[7.5rem_1fr] gap-3">
          <div>
            <label htmlFor={ids.room} className={LABEL}>Room</label>
            <input
              id={ids.room}
              className={cn(FIELD, 'tabular')}
              value={room}
              onChange={(e) => setRoom(e.target.value)}
              placeholder="slc1"
              autoCapitalize="none"
              autoCorrect="off"
              spellCheck={false}
              aria-describedby={error ? ids.error : undefined}
            />
          </div>
          <div>
            <label htmlFor={ids.name} className={LABEL}>Your name</label>
            <input
              id={ids.name}
              className={FIELD}
              value={name}
              onChange={(e) => setName(e.target.value)}
              autoComplete="name"
              maxLength={40}
              aria-describedby={error ? ids.error : undefined}
            />
          </div>
        </div>

        <RadioGroup.Root
          value={persona}
          onValueChange={choosePersona}
          aria-label="What you already know"
          className="mt-5 overflow-hidden rounded-(--radius-card) border border-rule"
        >
          {PERSONAS.map((p) => (
            <RadioGroup.Item
              key={p.id}
              value={p.id}
              className="group flex min-h-16 w-full items-center gap-3.5 border-b border-rule px-4 py-2.5 text-left -outline-offset-4 last:border-b-0 data-[state=checked]:bg-hall-raised"
            >
              <span
                aria-hidden="true"
                className="grid size-6 shrink-0 place-items-center rounded-full border-2 border-ink-soft group-data-[state=checked]:border-fresh group-data-[state=checked]:bg-fresh"
              >
                <RadioGroup.Indicator>
                  <Check className="size-4 text-fresh-ink" strokeWidth={3} />
                </RadioGroup.Indicator>
              </span>
              <span className="min-w-0">
                <span className="block font-semibold group-data-[state=checked]:font-bold">{p.name}</span>
                <span className="block text-(length:--text-note) text-ink-soft">{p.knows}</span>
              </span>
            </RadioGroup.Item>
          ))}
        </RadioGroup.Root>

        <div className="mt-5">
          <label htmlFor={ids.lang} className={LABEL}>Add a line in your language</label>
          <select
            id={ids.lang}
            className={cn(FIELD, 'appearance-none')}
            value={lang ?? ''}
            onChange={(e) => setLang(isLang(e.target.value) ? e.target.value : null)}
          >
            <option value="">English only</option>
            {LANGUAGES.map((l) => (
              <option key={l.code} value={l.code} lang={l.code}>{l.label}</option>
            ))}
          </select>
        </div>

        <div className="mt-auto pt-6 pb-5">
          <p id={ids.error} role="alert" className="mb-3 min-h-6 font-semibold text-danger">
            {error}
          </p>
          <Button type="submit" variant="primary" size="lg" className="w-full">
            Join the room
          </Button>
        </div>
      </form>
    </div>
  )
}
