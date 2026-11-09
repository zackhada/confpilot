import type { KnowledgeStatus, Lang, Term } from '@contracts'
import { Bookmark, BookmarkCheck, Check, CircleDashed, Sparkles } from 'lucide-react'
import { Button } from '@/components/ui/button'
import type { LiveCard } from '@/lib/cards'
import { cn } from '@/shared/cn'
import { LatencyBadge } from './LatencyBadge'

export interface TermCardProps {
  card: Pick<LiveCard, 'card_id' | 'term_id' | 'tier'>
  /** Word-to-card time; null until the first paint has been stamped. */
  latencyMs: number | null
  /** Undefined when a card arrives for a term this device has no definition for yet. */
  term: Term | undefined
  /** The lit card is the open one: full definition, native line and labelled buttons. */
  lit: boolean
  lang: Lang | null
  terms: Readonly<Record<string, Term>>
  knowledge: Readonly<Record<string, KnowledgeStatus>>
  saved?: boolean
  onOpen?: () => void
  onKnow?: () => void
  onSave?: () => void
}

function BuildsOn({ term, terms, knowledge }: Pick<TermCardProps, 'terms' | 'knowledge'> & { term: Term }) {
  const prereqs = term.prereqs.map((id) => terms[id]).filter((t): t is Term => t !== undefined)
  if (prereqs.length === 0) return null
  return (
    <p className="mt-3 flex flex-wrap items-center gap-x-2 gap-y-1.5 text-(length:--text-note)">
      <span className="text-lit-soft">Builds on</span>
      {prereqs.slice(0, 2).map((prereq) => {
        const known = knowledge[prereq.id] === 'known'
        const Icon = known ? Check : CircleDashed
        return (
          <span
            key={prereq.id}
            className={cn(
              'inline-flex items-center gap-1 rounded-(--radius-chip) border px-2.5 py-1 font-semibold',
              known ? 'border-lit-known text-lit-known' : 'border-lit-fresh text-lit-fresh',
            )}
          >
            <Icon className="size-3.5" strokeWidth={2.5} aria-hidden="true" />
            {prereq.term}
            <span className="sr-only">{known ? ', which you know' : ', also new to you'}</span>
          </span>
        )
      })}
    </p>
  )
}

/** One jargon card. Lit: the open card under the reading light. Settled: compact, in the hall. */
export function TermCard(props: TermCardProps) {
  const { card, term, lit, lang, latencyMs, saved = false, onOpen, onKnow, onSave } = props
  const name = term?.term ?? card.term_id
  const headingId = `card-${card.card_id}`
  const native = lang ? term?.translations?.[lang] : undefined
  const SaveIcon = saved ? BookmarkCheck : Bookmark
  const interactive = Boolean(onKnow && onSave)

  if (!lit) {
    return (
      <article
        aria-labelledby={headingId}
        className="flex items-stretch rounded-(--radius-card) border border-rule bg-hall-raised"
      >
        <button
          type="button"
          onClick={onOpen}
          disabled={!onOpen}
          aria-label={`Open the ${name} card`}
          className="min-w-0 flex-1 rounded-l-(--radius-card) py-2.5 pr-1 pl-4 text-left -outline-offset-4"
        >
          <span className="flex items-baseline gap-2.5">
            <span id={headingId} className="truncate font-display text-xl leading-tight">{name}</span>
            <LatencyBadge ms={latencyMs} className="font-medium text-ink-soft" />
          </span>
          <span className="mt-0.5 line-clamp-2 text-[0.9375rem] leading-snug text-ink-soft [@media(max-height:700px)]:line-clamp-1">
            {term?.simple_def ?? 'Definition on its way.'}
          </span>
        </button>
        {interactive && (
          <div className="flex shrink-0 items-center pr-1.5">
            <Button variant="ghost" size="icon" onClick={onKnow} aria-label={`I know ${name}`}>
              <Check aria-hidden="true" />
            </Button>
            <Button variant="ghost" size="icon" onClick={onSave} aria-pressed={saved} aria-label={`Save ${name}`}>
              <SaveIcon className={saved ? 'text-fresh' : undefined} aria-hidden="true" />
            </Button>
          </div>
        )}
      </article>
    )
  }

  return (
    <article
      aria-labelledby={headingId}
      className="on-lit rounded-(--radius-card) bg-lit px-4 pt-3.5 pb-4 text-lit-ink shadow-lift"
    >
      <header className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <h2 id={headingId} className="font-display text-(length:--text-headword) leading-[1.05] break-words">
            {name}
          </h2>
          {term?.say && (
            <p className="mt-1 text-(length:--text-note) text-lit-soft">
              say <span className="font-bold tracking-wide text-lit-ink">{term.say}</span>
            </p>
          )}
        </div>
        <div className="flex shrink-0 flex-col items-end gap-1 pt-1">
          <LatencyBadge ms={latencyMs} className="text-lit-soft" />
          {card.tier === 3 && (
            <span className="inline-flex items-center gap-1 text-(length:--text-note) font-semibold text-lit-fresh">
              <Sparkles className="size-3.5" aria-hidden="true" />
              Just added
            </span>
          )}
        </div>
      </header>

      <p className="mt-2.5 text-(length:--text-lead) leading-snug font-medium">
        {term?.simple_def ?? 'Definition on its way.'}
      </p>
      {native && lang && (
        <p lang={lang} className="mt-1.5 leading-snug text-lit-soft">{native}</p>
      )}
      {term && <BuildsOn term={term} terms={props.terms} knowledge={props.knowledge} />}

      {interactive && (
        <div className="mt-3.5 flex gap-2">
          <Button variant="litSolid" className="flex-1" onClick={onKnow}>
            <Check aria-hidden="true" />
            I know this
          </Button>
          <Button variant="litQuiet" className="px-5" onClick={onSave} aria-pressed={saved}>
            <SaveIcon aria-hidden="true" />
            {saved ? 'Saved' : 'Save'}
          </Button>
        </div>
      )}
    </article>
  )
}
