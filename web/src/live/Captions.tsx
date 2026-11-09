import type { KnowledgeStatus } from '@contracts'
import type { ReactNode } from 'react'
import type { Utterance } from '@/room/store'
import { cn } from '@/shared/cn'
import { groupTurns } from './turns'

interface CaptionsProps {
  utterances: readonly Utterance[]
  knowledge: Readonly<Record<string, KnowledgeStatus>>
  /** Term ids to mark as new. When omitted, every matched term the reader does not know. */
  freshTermIds?: ReadonlySet<string>
  meId?: string
  emptyHint: string
  className?: string
}

// New term: solid underline plus a wash of light. Known term: dotted underline. The line
// style carries the difference, so it does not depend on colour.
const MARK_FRESH =
  'relative rounded-[0.2em] bg-mark-bg px-[0.12em] text-mark-ink underline decoration-fresh decoration-[0.12em] underline-offset-[0.18em]'
const MARK_KNOWN = 'bg-transparent text-inherit underline decoration-known decoration-dotted decoration-[0.1em] underline-offset-[0.2em]'

function renderWords(utterance: Utterance, isFresh: (termId: string) => boolean): ReactNode[] {
  const starts = new Map(utterance.matches.map((m) => [m.first_word, m]))
  const nodes: ReactNode[] = []
  for (let i = 0; i < utterance.words.length; i += 1) {
    const match = starts.get(i)
    if (!match) {
      nodes.push(`${utterance.words[i]?.w ?? ''} `)
      continue
    }
    const spoken = utterance.words.slice(i, match.last_word + 1).map((w) => w.w).join(' ')
    // Keep a trailing comma or full stop outside the highlight.
    const [, text = spoken, trailing = ''] = /^(.*?)([.,!?;:]*)$/.exec(spoken) ?? []
    const fresh = isFresh(match.term_id)
    nodes.push(
      <mark key={`${utterance.utterance_id}:${i}`} className={fresh ? MARK_FRESH : MARK_KNOWN}>
        {fresh && (
          <span
            aria-hidden="true"
            className="pointer-events-none absolute inset-0 rounded-[inherit] bg-(--flash) opacity-0 [animation:term-flash_700ms_ease-out]"
          />
        )}
        {text}
      </mark>,
      `${trailing} `,
    )
    i = match.last_word
  }
  return nodes
}

const LONG_SENTENCE_WORDS = 14

/** The current turn keeps only its latest sentences, so the speaker's name stays in view. */
function visibleUtterances(utterances: Utterance[], current: boolean): Utterance[] {
  if (!current) return utterances
  const last = utterances[utterances.length - 1]
  const keep = last && last.words.length > LONG_SENTENCE_WORDS ? 1 : 2
  return utterances.slice(-keep)
}

/** Rolling captions, anchored to the bottom: the newest words sit right above the cards. */
export function Captions({ utterances, knowledge, freshTermIds, meId, emptyHint, className }: CaptionsProps) {
  const turns = groupTurns(utterances)
  const isFresh = (termId: string): boolean =>
    freshTermIds ? freshTermIds.has(termId) : knowledge[termId] !== 'known'

  if (turns.length === 0) {
    return (
      <div className={cn('flex min-h-0 flex-1 flex-col justify-end', className)}>
        <p className="max-w-[26ch] pb-4 text-(length:--text-lead) text-ink-soft">{emptyHint}</p>
      </div>
    )
  }

  return (
    <div className={cn('fade-top flex min-h-0 flex-1 flex-col justify-end overflow-hidden', className)}>
      {turns.map((turn, index) => {
        const current = index === turns.length - 1
        const first = turn.utterances[0]
        return (
          <p
            key={first?.utterance_id}
            className={cn(
              'pb-3',
              current
                ? 'text-(length:--text-caption-now) leading-[1.2] font-medium tracking-[-0.01em] text-ink'
                : 'text-(length:--text-caption-past) leading-snug text-ink-soft',
            )}
          >
            <span className="block pb-0.5 text-(length:--text-note) leading-normal font-bold tracking-normal text-ink-soft">
              {turn.speaker.user_id === meId ? 'You' : turn.speaker.name}
            </span>
            {visibleUtterances(turn.utterances, current).flatMap((u) => renderWords(u, isFresh))}
          </p>
        )
      })}
    </div>
  )
}
