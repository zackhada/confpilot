import type { Knowledge } from '@contracts'
import { describe, expect, it } from 'vitest'
import { DAY_MS, initialKnowledge } from '@/lib/sm2'
import { buildDeck, grade, GRADES, nextReviewLabel, preview } from './deck'

const NOW = 1_800_000_000_000
const record = (termId: string, patch: Partial<Knowledge>): Knowledge => ({ ...initialKnowledge('u1', termId), ...patch })

describe('GRADES', () => {
  it('maps the three answers to SM-2 grades 1, 4 and 5', () => {
    expect(GRADES).toEqual({ again: 1, good: 4, easy: 5 })
  })
})

describe('buildDeck', () => {
  it('collects saved, learn-next and learning terms once each, saved first', () => {
    const deck = buildDeck({
      saved: ['rrf', 'bm25'],
      learnNext: ['bm25', 'rag'],
      knowledge: { pod: 'learning', sre: 'known' },
      records: {},
      now: NOW,
    })
    expect(deck).toEqual({ due: ['rrf', 'bm25', 'rag', 'pod'], later: [], learned: [] })
  })

  it('separates cards that are not due yet and cards already learned', () => {
    const deck = buildDeck({
      saved: ['rrf', 'bm25', 'rag', 'pod'],
      learnNext: [],
      knowledge: {},
      records: {
        rrf: record('rrf', { due_at: NOW - 1 }),
        bm25: record('bm25', { due_at: NOW + DAY_MS }),
        rag: record('rag', { due_at: NOW + 16 * DAY_MS, interval_days: 16, learned: true }),
      },
      now: NOW,
    })
    expect(deck).toEqual({ due: ['rrf', 'pod'], later: ['bm25'], learned: ['rag'] })
  })
})

describe('grade', () => {
  it('starts a new term from the SM-2 defaults and schedules it for tomorrow', () => {
    const next = grade(undefined, 'u1', 'rrf', 'good', NOW)
    expect(next).toMatchObject({ user_id: 'u1', term_id: 'rrf', reps: 1, interval_days: 1, status: 'learning', learned: false })
    expect(next.due_at).toBe(NOW + DAY_MS)
  })

  it('resets the streak on Again', () => {
    const next = grade(record('rrf', { reps: 2, interval_days: 6 }), 'u1', 'rrf', 'again', NOW)
    expect(next).toMatchObject({ reps: 0, interval_days: 1, learned: false })
  })

  it('marks the term learned once the interval reaches seven days', () => {
    const next = grade(record('rrf', { reps: 2, interval_days: 6, ease: 2.5 }), 'u1', 'rrf', 'easy', NOW)
    expect(next.interval_days).toBeGreaterThanOrEqual(7)
    expect(next).toMatchObject({ learned: true, status: 'known' })
  })
})

describe('labels', () => {
  it('says when a card comes back', () => {
    expect(nextReviewLabel({ interval_days: 1 })).toBe('tomorrow')
    expect(nextReviewLabel({ interval_days: 6 })).toBe('in 6 days')
  })

  it('previews each answer before the tap', () => {
    const labels = preview(record('rrf', { reps: 1, interval_days: 1 }), 'u1', 'rrf', NOW)
    expect(labels).toEqual({ again: 'tomorrow', good: 'in 6 days', easy: 'in 6 days' })
  })
})
