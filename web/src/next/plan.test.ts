import { describe, expect, it } from 'vitest'
import { bookLink, BOOKS, SESSIONS } from './catalog'
import { buildPlan, sessionCount } from './plan'

const categories: Record<string, string> = {
  rag: 'ai',
  embedding: 'ai',
  chunking: 'ai',
  mcp: 'ai',
  kubernetes: 'cloud',
  pod: 'cloud',
  slo: 'ops',
}
const categoryOf = (id: string): string | undefined => categories[id]

describe('sessionCount', () => {
  it('maps the gap between now and goal to how much to do', () => {
    expect(sessionCount(7, 7)).toBe(0)
    expect(sessionCount(8, 6)).toBe(0)
    expect(sessionCount(5, 6)).toBe(1)
    expect(sessionCount(4, 6)).toBe(1)
    expect(sessionCount(4, 7)).toBe(2)
  })
})

describe('buildPlan', () => {
  it('picks the sessions that cover the most unknown terms, with the reason', () => {
    const plan = buildPlan({ gapIds: ['rag', 'embedding', 'chunking', 'slo'], current: 4, goal: 7, categoryOf })
    expect(plan.sessions.map((s) => s.session.id)).toEqual(['rag-zero', 'slo-budgets'])
    expect(plan.sessions[0]?.covers).toEqual(['rag', 'embedding', 'chunking'])
  })

  it('recommends one session for a small gap and no book', () => {
    const plan = buildPlan({ gapIds: ['rag', 'kubernetes'], current: 5, goal: 6, categoryOf })
    expect(plan.sessions).toHaveLength(1)
    expect(plan.book).toBeNull()
  })

  it('recommends a book for the weakest category on a big gap', () => {
    const plan = buildPlan({ gapIds: ['kubernetes', 'pod', 'rag'], current: 3, goal: 8, categoryOf })
    expect(plan.book?.id).toBe('k8s-up-running')
  })

  it('recommends nothing once the goal is reached', () => {
    const plan = buildPlan({ gapIds: ['rag'], current: 8, goal: 7, categoryOf })
    expect(plan).toEqual({ sessions: [], book: null })
  })

  it('skips sessions that cover none of the gaps', () => {
    const plan = buildPlan({ gapIds: ['unheard-of'], current: 2, goal: 9, categoryOf })
    expect(plan.sessions).toEqual([])
    expect(plan.book).toBeNull()
  })

  it('keeps catalog order on ties, so the plan is stable', () => {
    const plan = buildPlan({ gapIds: ['mcp'], current: 2, goal: 9, categoryOf })
    expect(plan.sessions.map((s) => s.session.id)).toEqual(['agents-mcp'])
  })
})

describe('catalog', () => {
  it('labels every session as a sample', () => {
    expect(SESSIONS.every((s) => s.title.startsWith('Sample:'))).toBe(true)
  })

  it('has unique ids', () => {
    expect(new Set(SESSIONS.map((s) => s.id)).size).toBe(SESSIONS.length)
    expect(new Set(BOOKS.map((b) => b.id)).size).toBe(BOOKS.length)
  })

  it('builds an encoded search link for a book', () => {
    expect(bookLink({ title: 'AI Engineering', author: 'Chip Huyen' })).toBe(
      'https://openlibrary.org/search?q=AI%20Engineering%20Chip%20Huyen',
    )
  })
})
