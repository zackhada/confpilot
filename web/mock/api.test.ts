import { describe, expect, it } from 'vitest'
import type { Term } from '../../contracts/types.ts'
import { highlight, KnowledgeStore, probeFor, recapFor, searchMoments, termsIn, type Moment } from './api.ts'

const term = (id: string, name: string, aliases: string[] = [], ambiguous = false): Term => ({
  id,
  term: name,
  aliases,
  say: null,
  category: 'data',
  level: 3,
  simple_def: 'x',
  prereqs: [],
  ambiguous,
  source: 'seed',
})
const terms = [term('rag', 'RAG'), term('hybrid-search', 'hybrid search'), term('service', 'service', [], true)]
const zack = { user_id: 'u-zack', name: 'Zack' }
const moments: Moment[] = [
  { utterance_id: 'a', speaker: zack, spoken_at: 1000, text: 'We do managed hybrid search, including RAG.' },
  { utterance_id: 'b', speaker: { user_id: 'u-c', name: 'Clayton' }, spoken_at: 2000, text: 'Can I get your LinkedIn?' },
]

describe('highlight', () => {
  it('escapes the text and marks only the query words', () => {
    expect(highlight('RAG <b> & search', new Set(['rag']))).toBe('<mark>RAG</mark> &lt;b&gt; &amp; search')
  })
})

describe('termsIn', () => {
  it('finds whole-word terms, including multi-word ones', () => {
    expect(termsIn('managed hybrid search, including RAG', terms)).toEqual(['rag', 'hybrid-search'])
    expect(termsIn('I had to drag the file', terms)).toEqual([])
  })
})

describe('searchMoments', () => {
  it('finds the moment, with highlight and term chips', () => {
    const hits = searchMoments('What did Zack say about RAG?', moments, terms, 5)
    expect(hits).toHaveLength(1)
    expect(hits[0]).toMatchObject({ utterance_id: 'a', term_ids: ['rag', 'hybrid-search'] })
    expect(hits[0]?.highlight).toContain('<mark>RAG.</mark>')
  })

  it('returns nothing for a question with no searchable words or no match', () => {
    expect(searchMoments('what did they say', moments, terms, 5)).toEqual([])
    expect(searchMoments('kubernetes', moments, terms, 5)).toEqual([])
  })
})

describe('recapFor', () => {
  it('counts the user’s new terms and ranks what was heard', () => {
    const recap = recapFor('slc1', ['rag', 'bm25'], new Map([['rag', 2], ['bm25', 1], ['pod', 3]]))
    expect(recap.new_term_count).toBe(2)
    expect(recap.heard[0]).toEqual({ term_id: 'pod', count: 3 })
    expect(recap.learn_next).toEqual(['rag', 'bm25'])
  })
})

describe('probeFor', () => {
  it('marks terms the person used as known, skipping ambiguous everyday words', () => {
    const result = probeFor('I build RAG pipelines behind a search service', terms)
    expect(result.known_term_ids).toEqual(['rag'])
  })
})

describe('KnowledgeStore', () => {
  it('merges patches per user and term', () => {
    const store = new KnowledgeStore()
    store.put('u1', 'rag', { status: 'learning', source: 'tap' })
    const next = store.put('u1', 'rag', { interval_days: 6, reps: 2 })
    expect(next).toMatchObject({ status: 'learning', interval_days: 6, reps: 2, user_id: 'u1', term_id: 'rag' })
    expect(store.list('u1')).toHaveLength(1)
    expect(store.list('u2')).toEqual([])
  })
})
