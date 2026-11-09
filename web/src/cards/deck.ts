import type { Knowledge, KnowledgeStatus } from '@contracts'
import { DAY_MS, initialKnowledge, review, type Sm2Grade } from '@/lib/sm2'

/** The three answers on a flashcard and the SM-2 grade each one stands for. */
export const GRADES = { again: 1, good: 4, easy: 5 } as const satisfies Record<string, Sm2Grade>
export type Answer = keyof typeof GRADES

export interface DeckInput {
  saved: readonly string[]
  learnNext: readonly string[]
  knowledge: Readonly<Record<string, KnowledgeStatus>>
  records: Readonly<Record<string, Knowledge>>
  /** Server-time ms. */
  now: number
}

export interface Deck {
  /** Never reviewed, or due now. Saved terms first, then learn-next, then other learning terms. */
  due: string[]
  /** Reviewed and not due yet. */
  later: string[]
  /** Interval of seven days or more. */
  learned: string[]
}

/** Everything worth a flashcard: saved terms, the recap's learn-next list, and terms being learned. */
export function buildDeck({ saved, learnNext, knowledge, records, now }: DeckInput): Deck {
  const learning = Object.keys(knowledge).filter((id) => knowledge[id] === 'learning')
  const ids = [...new Set([...saved, ...learnNext, ...learning])]
  const isLearned = (id: string): boolean => records[id]?.learned === true
  const isDue = (id: string): boolean => {
    const dueAt = records[id]?.due_at
    return dueAt === null || dueAt === undefined || dueAt <= now
  }
  const open = ids.filter((id) => !isLearned(id))
  return {
    due: open.filter(isDue),
    later: open.filter((id) => !isDue(id)),
    learned: ids.filter(isLearned),
  }
}

/** Apply one answer with SM-2. A term with no record yet starts from the SM-2 defaults. */
export function grade(
  record: Knowledge | undefined,
  userId: string,
  termId: string,
  answer: Answer,
  now: number,
): Knowledge {
  return review(record ?? initialKnowledge(userId, termId), GRADES[answer], now)
}

/** "tomorrow", "in 6 days": when a reviewed card comes back. */
export function nextReviewLabel(record: Pick<Knowledge, 'interval_days'>): string {
  const days = Math.max(1, Math.round(record.interval_days))
  return days === 1 ? 'tomorrow' : `in ${days} days`
}

/** What each answer would do to this card, shown under the buttons before the tap. */
export function preview(record: Knowledge | undefined, userId: string, termId: string, now: number): Record<Answer, string> {
  const label = (answer: Answer): string => nextReviewLabel(grade(record, userId, termId, answer, now))
  return { again: label('again'), good: label('good'), easy: label('easy') }
}

export { DAY_MS }
