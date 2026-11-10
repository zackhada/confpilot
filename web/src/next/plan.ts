import { BOOKS, SESSIONS, type CatalogBook, type CatalogSession } from './catalog'

export const MAX_SESSIONS = 2
/** The gap (goal minus now) at which a book is worth recommending too. */
export const BOOK_GAP = 3

export interface PlanInput {
  /** Terms heard that the person does not know yet, most heard first. */
  gapIds: readonly string[]
  /** Self-rating now and the goal, both 1 to 10. */
  current: number
  goal: number
  categoryOf: (termId: string) => string | undefined
  sessions?: readonly CatalogSession[]
  books?: readonly CatalogBook[]
}

export interface PlannedSession {
  session: CatalogSession
  /** The unknown terms this session covers, in the order they were heard. */
  covers: string[]
}

export interface Plan {
  sessions: PlannedSession[]
  book: CatalogBook | null
}

/** How many sessions to suggest for the distance between where someone is and wants to be. */
export function sessionCount(current: number, goal: number): number {
  const gap = goal - current
  if (gap <= 0) return 0
  return gap <= 2 ? 1 : MAX_SESSIONS
}

function weakestCategory(gapIds: readonly string[], categoryOf: PlanInput['categoryOf']): string | null {
  const counts = new Map<string, number>()
  for (const id of gapIds) {
    const category = categoryOf(id)
    if (category) counts.set(category, (counts.get(category) ?? 0) + 1)
  }
  let best: string | null = null
  let bestCount = 0
  for (const [category, count] of counts) {
    if (count > bestCount) {
      best = category
      bestCount = count
    }
  }
  return best
}

/**
 * The next steps after a conversation: the sessions that cover the most terms the person
 * heard but does not know, and a book for their weakest category when the goal is far away.
 */
export function buildPlan({ gapIds, current, goal, categoryOf, sessions = SESSIONS, books = BOOKS }: PlanInput): Plan {
  const count = sessionCount(current, goal)
  if (count === 0) return { sessions: [], book: null }

  const ranked = sessions
    .map((session) => ({ session, covers: gapIds.filter((id) => session.termIds.includes(id)) }))
    .filter((planned) => planned.covers.length > 0)
    .sort((a, b) => b.covers.length - a.covers.length)

  // Only categories that have a book compete, so idiom or conference terms never hide one.
  const bookCategories = new Set(books.map((b) => b.category))
  const bookGaps = gapIds.filter((id) => bookCategories.has(categoryOf(id) ?? ''))
  const category = goal - current >= BOOK_GAP ? weakestCategory(bookGaps, categoryOf) : null
  const book = category ? (books.find((b) => b.category === category) ?? null) : null

  return { sessions: ranked.slice(0, count), book }
}
