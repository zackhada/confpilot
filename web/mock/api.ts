// Mock versions of the API's data endpoints: knowledge, recap, search and probe. They keep
// everything in memory and use plain word matching where the real API uses Elasticsearch
// and an LLM, so the screens can be built and demoed without either.
import type {
  Knowledge,
  KnowledgePatch,
  ProbeResponse,
  Recap,
  SearchHit,
  Speaker,
  Term,
} from '../../contracts/types.ts'

export interface Moment {
  utterance_id: string
  speaker: Speaker
  spoken_at: number
  text: string
}

const words = (text: string): string[] => text.toLowerCase().match(/[a-z0-9]+/g) ?? []
const STOP_WORDS = new Set(['what', 'did', 'say', 'about', 'the', 'a', 'an', 'is', 'they', 'where', 'how', 'do', 'does', 'of', 'to'])

export function escapeHtml(text: string): string {
  return text.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;')
}

/** Escape first, then wrap the query's words in <mark>, as the real API's highlighter does. */
export function highlight(text: string, queryWords: ReadonlySet<string>): string {
  return text
    .split(/(\s+)/)
    .map((piece) => {
      const core = piece.toLowerCase().replace(/[^a-z0-9]/g, '')
      return core && queryWords.has(core) ? `<mark>${escapeHtml(piece)}</mark>` : escapeHtml(piece)
    })
    .join('')
}

/** Term ids whose name or an alias appears in the text as whole words. */
export function termsIn(text: string, terms: readonly Term[]): string[] {
  const padded = ` ${words(text).join(' ')} `
  return terms
    .filter((term) => [term.term, ...term.aliases].some((form) => {
      const needle = words(form).join(' ')
      return needle !== '' && padded.includes(` ${needle} `)
    }))
    .map((term) => term.id)
}

/** Rank moments by how many query words they contain; a speaker's name counts too. */
export function searchMoments(q: string, moments: readonly Moment[], terms: readonly Term[], limit: number): SearchHit[] {
  const queryWords = new Set(words(q).filter((w) => !STOP_WORDS.has(w)))
  if (queryWords.size === 0) return []
  return moments
    .map((moment) => {
      const haystack = new Set([...words(moment.text), ...words(moment.speaker.name)])
      const score = [...queryWords].filter((w) => haystack.has(w)).length
      return { moment, score }
    })
    .filter(({ score }) => score > 0)
    .sort((a, b) => b.score - a.score || b.moment.spoken_at - a.moment.spoken_at)
    .slice(0, limit)
    .map(({ moment }) => ({
      ...moment,
      highlight: highlight(moment.text, queryWords),
      term_ids: termsIn(moment.text, terms).filter((id) => ambiguousFree(id, terms)),
    }))
}

function ambiguousFree(termId: string, terms: readonly Term[]): boolean {
  return !terms.find((term) => term.id === termId)?.ambiguous
}

export function recapFor(room: string, shown: readonly string[], heard: ReadonlyMap<string, number>): Recap {
  const ranked = [...heard].sort(([, a], [, b]) => b - a).map(([term_id, count]) => ({ term_id, count }))
  const mine = new Set(shown)
  return {
    room,
    new_term_count: shown.length,
    heard: ranked,
    learn_next: ranked.filter((h) => mine.has(h.term_id)).slice(0, 5).map((h) => h.term_id),
  }
}

/** Stand-in for the LLM: terms the person used themselves are marked as known. */
export function probeFor(transcript: string, terms: readonly Term[]): ProbeResponse {
  const known = termsIn(transcript, terms).filter((id) => ambiguousFree(id, terms))
  return {
    role: /sre|platform|infra|kubernetes/i.test(transcript) ? 'Platform engineer' : 'Engineer',
    domain: /search|rag|embedding/i.test(transcript) ? 'search' : 'cloud infrastructure',
    known_term_ids: known,
    english_level: 'B2',
    goals: ['Follow the talks without getting lost in the jargon'],
  }
}

/** In-memory replacement for the user-knowledge index. */
export class KnowledgeStore {
  private readonly byUser = new Map<string, Map<string, Knowledge>>()

  list(userId: string): Knowledge[] {
    return [...(this.byUser.get(userId)?.values() ?? [])]
  }

  put(userId: string, termId: string, patch: KnowledgePatch): Knowledge {
    const records = this.byUser.get(userId) ?? new Map<string, Knowledge>()
    const previous: Knowledge = records.get(termId) ?? {
      user_id: userId,
      term_id: termId,
      status: 'unknown',
      source: 'tap',
      encounters: 0,
      ease: 2.5,
      interval_days: 0,
      reps: 0,
      due_at: null,
      learned: false,
    }
    const next: Knowledge = { ...previous, ...patch, user_id: userId, term_id: termId }
    records.set(termId, next)
    this.byUser.set(userId, records)
    return next
  }
}
