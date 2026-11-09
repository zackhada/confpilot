import type { Term } from '@contracts'
import { describe, expect, it } from 'vitest'
import { mapBands, probeCandidates, probeStatuses } from './probeLogic'

const term = (id: string, level: Term['level'], prereqs: string[] = []): Term => ({
  id,
  term: id,
  aliases: [],
  say: null,
  category: 'cloud',
  level,
  simple_def: 'x',
  prereqs,
  source: 'seed',
})
const terms = [
  term('container', 2),
  term('kubernetes', 3, ['container']),
  term('pod', 3, ['kubernetes']),
  term('crashloop', 4, ['pod']),
  term('vector', 2),
  term('embedding', 3, ['vector']),
]

describe('probeCandidates', () => {
  it('leaves out terms the talk step already settled', () => {
    expect(probeCandidates(terms, ['kubernetes', 'pod']).map((t) => t.id)).toEqual([
      'container',
      'crashloop',
      'vector',
      'embedding',
    ])
  })
})

describe('probeStatuses', () => {
  it('marks used terms as known and ignores ids that are not in the glossary', () => {
    expect(probeStatuses(terms, ['kubernetes', 'not-a-term'], {})).toEqual({ kubernetes: 'known' })
  })

  it('turns answers into statuses and infers the prerequisites of an explained term', () => {
    const statuses = probeStatuses(terms, [], { pod: 'explain', embedding: 'heard', vector: 'new' })
    expect(statuses).toMatchObject({
      pod: 'known',
      kubernetes: 'known',
      container: 'known',
      embedding: 'learning',
      vector: 'unknown',
    })
  })

  it('lets an explicit answer beat what the talk step assumed', () => {
    expect(probeStatuses(terms, ['vector'], { vector: 'new' }).vector).toBe('unknown')
  })
})

describe('mapBands', () => {
  const bands = mapBands(terms, { container: 'known', kubernetes: 'known' })
  const ids = (key: string): string[] => bands.find((b) => b.key === key)?.sample.map((t) => t.id) ?? []

  it('orders the bands far to near and counts each one', () => {
    expect(bands.map((b) => [b.key, b.count])).toEqual([
      ['beyond', 2],
      ['frontier', 2],
      ['known', 2],
    ])
  })

  it('puts a term on the frontier only when everything it builds on is known', () => {
    expect(ids('frontier')).toEqual(['pod', 'vector'])
    expect(ids('beyond')).toEqual(['embedding', 'crashloop'])
  })

  it('shows the hardest known terms first', () => {
    expect(ids('known')).toEqual(['kubernetes', 'container'])
  })
})
