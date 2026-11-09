import type { SearchHit } from '@contracts'
import { LoaderCircle, Search } from 'lucide-react'
import { useEffect, useRef, useState, type FormEvent } from 'react'
import { parseHighlight, timeAgo } from '@/ask/highlight'
import { Button } from '@/components/ui/button'
import { askRoom } from '@/room/api'
import { serverNow } from '@/room/session'
import { useRoom } from '@/room/store'
import { ScreenHeader } from '@/shell/ScreenHeader'
import { useTermSheet } from '@/shared/useTermSheet'

const DEMO_QUESTION = 'What did Zack say about RAG?'

interface Query {
  room: string
  question: string
  hits: SearchHit[] | null
  answer: string | null
  pending: boolean
}

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

/** Answer a question using moments retrieved from the room transcript. */
export function Ask() {
  const me = useRoom((s) => s.me)
  const room = useRoom((s) => s.room)
  const ready = useRoom((s) => s.status === 'open' && s.members.some((m) => m.user_id === s.me?.user_id))
  const [text, setText] = useState('')
  const [query, setQuery] = useState<Query | null>(null)
  const active = useRef<AbortController | null>(null)
  const status = query?.room === room ? query : null

  useEffect(() => () => active.current?.abort(), [room, me])

  const ask = (question: string): void => {
    const q = question.trim()
    if (!q || !me || !room || !ready) return
    active.current?.abort()
    const controller = new AbortController()
    active.current = controller
    setText(q)

    let next: Query = { room, question: q, hits: null, answer: null, pending: true }
    setQuery(next)
    const signal = AbortSignal.any([controller.signal, AbortSignal.timeout(20_000)])
    void askRoom(me.name, { room, question: q }, (event) => {
      if (controller.signal.aborted) return
      next = event.type === 'moments'
        ? { ...next, hits: event.hits }
        : { ...next, answer: event.answer, pending: false }
      setQuery(next)
    }, signal).catch(() => {
      if (!controller.signal.aborted) setQuery({ ...next, pending: false })
    })
  }

  const submit = (event: FormEvent): void => {
    event.preventDefault()
    ask(text)
  }

  return (
    <>
      <ScreenHeader>
        <h1 className="font-display text-xl">Agent</h1>
      </ScreenHeader>

      <div className="px-safe min-h-0 flex-1 overflow-y-auto" aria-live="polite" aria-busy={status?.pending && status.hits === null}>
        {!status && (
          <div className="flex h-full flex-col justify-end pb-5">
            <p className="max-w-[13ch] font-display text-(length:--text-title) leading-[1.05]">
              Ask about anything you heard.
            </p>
            <p className="max-w-[30ch] pt-4 text-(length:--text-lead) text-ink-soft">
              Get an answer grounded in the conversation, with the moments it draws on.
            </p>
          </div>
        )}
        {status?.pending && status.hits === null && (
          <p className="flex items-center gap-2.5 pt-4 text-(length:--text-lead) text-ink-soft">
            <LoaderCircle className="size-5 motion-safe:animate-spin" aria-hidden="true" />
            Searching the conversation
          </p>
        )}
        {status && !status.pending && status.hits === null && (
          <div role="alert" className="pt-4">
            <p className="max-w-[28ch] text-(length:--text-lead) font-semibold">
              The agent couldn’t search the room. Your question is still in the box.
            </p>
            <Button className="mt-4" disabled={!ready} onClick={() => ask(status.question)}>Try again</Button>
          </div>
        )}
        {status?.hits?.length === 0 && (
          <p className="max-w-[28ch] pt-4 text-(length:--text-lead) text-ink-soft">
            No moment matched &ldquo;{status.question}&rdquo;. Try a word you heard, such as a term from your recap.
          </p>
        )}
        {status?.hits && status.hits.length > 0 && (
          <>
            <section aria-labelledby="agent-answer" className="mt-3 rounded-(--radius-card) border border-rule bg-hall-raised p-4">
              <h2 id="agent-answer" className="font-display text-xl">Answer</h2>
              <p className="pt-2 text-(length:--text-lead) leading-snug">
                {status.pending ? 'Writing an answer from these moments…' : status.answer ?? 'An answer is unavailable. You can still read the moments below.'}
              </p>
            </section>
            <p className="pt-3 text-(length:--text-note) font-semibold text-ink-soft">
              {status.hits.length} {status.hits.length === 1 ? 'moment' : 'moments'}
            </p>
            <ol>{status.hits.map((hit) => <Moment key={`${hit.speaker.user_id}:${hit.utterance_id}`} hit={hit} />)}</ol>
          </>
        )}
      </div>

      <div className="border-t border-rule pt-3 pb-3">
        <div className="px-safe pb-3">
          <button
            type="button"
            onClick={() => ask(DEMO_QUESTION)}
            disabled={!ready}
            className="min-h-11 rounded-(--radius-chip) border border-rule bg-hall-raised px-4 text-(length:--text-note) font-semibold"
          >
            {DEMO_QUESTION}
          </button>
        </div>
        <search>
          <form onSubmit={submit} className="px-safe flex gap-2">
          <input
            type="search"
            value={text}
            onChange={(e) => setText(e.target.value)}
            aria-label="Your question"
            maxLength={200}
            placeholder="Ask in any language"
            enterKeyHint="search"
            className="min-h-13 min-w-0 flex-1 rounded-(--radius-control) border border-rule bg-hall-raised px-4 text-(length:--text-lead) text-ink placeholder:text-ink-soft"
          />
          <Button type="submit" variant="primary" size="icon" className="size-13" aria-label="Ask the agent" disabled={!ready || !text.trim()}>
            <Search aria-hidden="true" />
          </Button>
          </form>
        </search>
      </div>
    </>
  )
}
