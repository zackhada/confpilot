import type { Term } from '@contracts'
import { describe, expect, it } from 'vitest'
import { localRecap } from './localRecap'

const term = (id: string, prereqs: string[] = []): Term => ({
  id,
  term: id,
  aliases: [],
  say: null,
  category: 'data',
  level: 3,
  simple_def: 'x',
  prereqs,
  source: 'seed',
})
const terms = [term('keyword-search'), term('bm25', ['keyword-search']), term('rrf', ['hybrid-search']), term('hybrid-search'), term('pod')]

describe('localRecap', () => {
  const input = {
    room: 'slc1',
    heard: { bm25: 1, 'hybrid-search': 3, rrf: 2, pod: 4, 'keyword-search': 1 },
    shownTermIds: ['hybrid-search', 'bm25', 'rrf'],
    terms,
    knowledge: { pod: 'known' as const, 'keyword-search': 'known' as const },
  }

  it('counts the terms that got a card and ranks everything heard', () => {
    const recap = localRecap(input)
    expect(recap.new_term_count).toBe(3)
    expect(recap.heard.map((h) => h.term_id).slice(0, 2)).toEqual(['pod', 'hybrid-search'])
  })

  it('puts heard frontier terms in Learn next, most heard first', () => {
    // pod is known; rrf builds on hybrid search, which is not known yet, so it is beyond.
    expect(localRecap(input).learn_next).toEqual(['hybrid-search', 'bm25'])
  })

  it('moves a term into Learn next once its prerequisite is known', () => {
    const knowledge = { ...input.knowledge, 'hybrid-search': 'known' as const }
    expect(localRecap({ ...input, knowledge }).learn_next).toEqual(['rrf', 'bm25'])
  })

  it('is empty before anything was heard', () => {
    const recap = localRecap({ ...input, heard: {}, shownTermIds: [] })
    expect(recap).toMatchObject({ new_term_count: 0, heard: [], learn_next: [] })
  })
})
