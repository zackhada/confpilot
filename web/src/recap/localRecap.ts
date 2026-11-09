import type { KnowledgeStatus, Recap, Term } from '@contracts'
import { classify } from '@/lib/frontier'

export const LEARN_NEXT_LIMIT = 5

export interface LocalRecapInput {
  room: string
  /** Times each term was heard this session. */
  heard: Readonly<Record<string, number>>
  /** Terms that got a card on this phone. */
  shownTermIds: readonly string[]
  terms: readonly Term[]
  knowledge: Readonly<Record<string, KnowledgeStatus>>
}

/**
 * The recap computed on the phone, used when the API cannot be reached. "Learn next" ranks
 * terms by times heard multiplied by whether the term is on the person's frontier (not yet
 * known, with every prerequisite known), so only frontier terms that were heard qualify.
 */
export function localRecap({ room, heard, shownTermIds, terms, knowledge }: LocalRecapInput): Recap {
  const ranked = Object.entries(heard)
    .map(([term_id, count]) => ({ term_id, count }))
    .sort((a, b) => b.count - a.count)
  const frontier = new Set(classify([...terms], { ...knowledge }).frontier)
  return {
    room,
    new_term_count: shownTermIds.length,
    heard: ranked,
    learn_next: ranked.filter((h) => frontier.has(h.term_id)).slice(0, LEARN_NEXT_LIMIT).map((h) => h.term_id),
  }
}
