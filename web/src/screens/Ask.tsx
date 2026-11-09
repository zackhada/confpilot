import type { SearchHit } from '@contracts'
import { LoaderCircle, Search } from 'lucide-react'
import { useRef, useState, type FormEvent } from 'react'
import { parseHighlight, timeAgo } from '@/ask/highlight'
import { Button } from '@/components/ui/button'
import { searchRoom } from '@/room/api'
import { serverNow } from '@/room/session'
import { useRoom } from '@/room/store'
import { ScreenHeader } from '@/shell/ScreenHeader'
import { useTermSheet } from '@/shared/useTermSheet'

const SUGGESTIONS: readonly { text: string; lang: string }[] = [
  { text: 'What did Zack say about RAG?', lang: 'en' },
  { text: '¿Qué dijeron sobre la búsqueda híbrida?', lang: 'es' },
  { text: 'How does the search rank results?', lang: 'en' },
]

type Status =
  | { kind: 'idle' }
  | { kind: 'loading'; q: string }
  | { kind: 'done'; q: string; hits: SearchHit[] }
  | { kind: 'error'; q: string }

function Moment({ hit }: { hit: SearchHit }) {
  const terms = useRoom((s) => s.terms)
  const openTerm = useTermSheet((s) => s.open)
  const chips = hit.term_ids.filter((id) => terms[id]).slice(0, 4)
  return (
    <li className="border-b border-rule py-4">
      <p className="flex items-baseline justify-between gap-3 text-(length:--text-note)">
        <span className="font-bold">{hit.speaker.name}</span>
        <span className="tabular text-ink-soft">{timeAgo(hit.spoken_at, serverNow())}</span>
      </p>
      <p className="pt-1 text-(length:--text-lead) leading-snug">
        {parseHighlight(hit.highlight || hit.text).map((part, i) =>
          part.marked ? (
            <mark key={i} className="rounded-[0.2em] bg-mark-bg px-[0.12em] text-mark-ink underline decoration-fresh decoration-[0.12em] underline-offset-[0.18em]">
              {part.text}
            </mark>
          ) : (
            part.text
          ),
        )}
      </p>
      {chips.length > 0 && (
        <ul aria-label="Terms in this moment" className="flex flex-wrap gap-2 pt-2.5">
          {chips.map((id) => (
            <li key={id}>
              <button
                type="button"
                onClick={() => openTerm(id)}
                className="min-h-11 rounded-(--radius-chip) border border-rule px-3.5 text-(length:--text-note) font-semibold"
              >
                {terms[id]?.term}
              </button>
            </li>
          ))}
        </ul>
      )}
    </li>
  )
}

/** Ask your conference: search everything said in the room, in any language. */
export function Ask() {
  const me = useRoom((s) => s.me)
  const room = useRoom((s) => s.room)
  const [text, setText] = useState('')
  const [status, setStatus] = useState<Status>({ kind: 'idle' })
  const latest = useRef(0)

  const ask = (question: string): void => {
    const q = question.trim()
    if (!q || !me || !room) return
    setText(q)
    setStatus({ kind: 'loading', q })
    latest.current += 1
    const request = latest.current
    searchRoom(me.name, room, q)
      .then((hits) => {
        if (request === latest.current) setStatus({ kind: 'done', q, hits })
      })
      .catch(() => {
        if (request === latest.current) setStatus({ kind: 'error', q })
      })
  }

  const submit = (event: FormEvent): void => {
    event.preventDefault()
    ask(text)
  }

  return (
    <>
      <ScreenHeader>
        <h1 className="font-display text-xl">Ask</h1>
      </ScreenHeader>

      <div className="px-safe min-h-0 flex-1 overflow-y-auto" aria-live="polite" aria-busy={status.kind === 'loading'}>
        {status.kind === 'idle' && (
          <div className="flex h-full flex-col justify-end pb-5">
            <p className="max-w-[13ch] font-display text-(length:--text-title) leading-[1.05]">
              Ask about anything you heard.
            </p>
            <p className="max-w-[30ch] pt-4 text-(length:--text-lead) text-ink-soft">
              Use your own language. The answer is the moment it was said.
            </p>
          </div>
        )}
        {status.kind === 'loading' && (
          <p className="flex items-center gap-2.5 pt-4 text-(length:--text-lead) text-ink-soft">
            <LoaderCircle className="size-5 animate-spin" aria-hidden="true" />
            Searching the conversation
          </p>
        )}
        {status.kind === 'error' && (
          <div role="alert" className="pt-4">
            <p className="max-w-[28ch] text-(length:--text-lead) font-semibold">
              Search is not reachable right now. Your question is still in the box.
            </p>
            <Button className="mt-4" onClick={() => ask(status.q)}>Try again</Button>
          </div>
        )}
        {status.kind === 'done' && status.hits.length === 0 && (
          <p className="max-w-[28ch] pt-4 text-(length:--text-lead) text-ink-soft">
            No moment matched &ldquo;{status.q}&rdquo;. Try a word you heard, such as a term from your recap.
          </p>
        )}
        {status.kind === 'done' && status.hits.length > 0 && (
          <>
            <p className="pt-3 text-(length:--text-note) font-semibold text-ink-soft">
              {status.hits.length} {status.hits.length === 1 ? 'moment' : 'moments'}
            </p>
            <ol>{status.hits.map((hit) => <Moment key={hit.utterance_id} hit={hit} />)}</ol>
          </>
        )}
      </div>

      <div className="border-t border-rule pt-3 pb-3">
        <ul aria-label="Suggested questions" className="scrollbar-none px-safe flex gap-2 overflow-x-auto pb-3">
          {SUGGESTIONS.map((suggestion) => (
            <li key={suggestion.text} className="shrink-0">
              <button
                type="button"
                lang={suggestion.lang}
                onClick={() => ask(suggestion.text)}
                className="min-h-11 rounded-(--radius-chip) border border-rule bg-hall-raised px-4 text-(length:--text-note) font-semibold"
              >
                {suggestion.text}
              </button>
            </li>
          ))}
        </ul>
        <search>
          <form onSubmit={submit} className="px-safe flex gap-2">
          <input
            type="search"
            value={text}
            onChange={(e) => setText(e.target.value)}
            aria-label="Your question"
            placeholder="Ask in any language"
            enterKeyHint="search"
            className="min-h-13 min-w-0 flex-1 rounded-(--radius-control) border border-rule bg-hall-raised px-4 text-(length:--text-lead) text-ink placeholder:text-ink-soft"
          />
          <Button type="submit" variant="primary" size="icon" className="size-13" aria-label="Search" disabled={!text.trim()}>
            <Search aria-hidden="true" />
          </Button>
          </form>
        </search>
      </div>
    </>
  )
}
