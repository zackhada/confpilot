import type { KnowledgeStatus, Term } from '@contracts'
import { answersToKnowledge, classify, type ProbeAnswers } from '@/lib/frontier'

export const PROBE_QUESTIONS = 9

/** Terms the adaptive check may ask about: everything the talk step did not already settle. */
export function probeCandidates(terms: readonly Term[], alreadyKnown: readonly string[]): Term[] {
  const known = new Set(alreadyKnown)
  return terms.filter((term) => !known.has(term.id))
}

/**
 * What the probe learned, as knowledge statuses: terms the person used when describing
 * their work (from /api/probe) are known, and every card answer counts, with an explicit
 * answer beating an inferred one.
 */
export function probeStatuses(
  terms: readonly Term[],
  usedTermIds: readonly string[],
  answers: ProbeAnswers,
): Record<string, KnowledgeStatus> {
  const inGlossary = new Set(terms.map((term) => term.id))
  const used = usedTermIds.filter((id) => inGlossary.has(id)).map((id) => [id, 'known'] as const)
  return { ...Object.fromEntries(used), ...answersToKnowledge(answers, [...terms]) }
}

export type BandKey = 'beyond' | 'frontier' | 'known'

export interface MapBand {
  key: BandKey
  count: number
  /** A few terms to show by name, the most telling first. */
  sample: Term[]
}

const SAMPLE_SIZE: Record<BandKey, number> = { beyond: 7, frontier: 9, known: 8 }

/**
 * The three bands of "Your map", far to near: beyond, frontier, known. Known shows the
 * hardest terms first (what the person can be proud of); frontier and beyond show the
 * most approachable first (where to go next).
 */
export function mapBands(terms: readonly Term[], knowledge: Readonly<Record<string, KnowledgeStatus>>): MapBand[] {
  const map = classify([...terms], { ...knowledge })
  const byId = new Map(terms.map((term) => [term.id, term]))
  const pickTerms = (ids: readonly string[]): Term[] => ids.flatMap((id) => byId.get(id) ?? [])
  const easiestFirst = (a: Term, b: Term): number => a.level - b.level
  const band = (key: BandKey, ids: readonly string[], order: (a: Term, b: Term) => number): MapBand => ({
    key,
    count: ids.length,
    sample: pickTerms(ids).sort(order).slice(0, SAMPLE_SIZE[key]),
  })
  return [
    band('beyond', map.beyond, easiestFirst),
    band('frontier', map.frontier, (a, b) => b.prereqs.length - a.prereqs.length || easiestFirst(a, b)),
    band('known', map.known, (a, b) => b.level - a.level),
  ]
}
