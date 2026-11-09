import { describe, expect, it } from 'vitest'
import type { Utterance } from '@/room/store'
import { withoutEchoes } from './dedupe'

const clayton = { user_id: 'u-clayton', name: 'Clayton' }
const zack = { user_id: 'u-zack', name: 'Zack' }

function utterance(id: string, speaker: typeof zack, text: string, firstSeenAt: number): Utterance {
  return {
    utterance_id: id,
    speaker,
    words: text.split(' ').map((w, i) => ({ w, start_ms: i * 300, end_ms: i * 300 + 250 })),
    matches: [],
    is_final: true,
    seq: 0,
    started_at: firstSeenAt,
    first_seen_at: firstSeenAt,
  }
}

const ids = (list: Utterance[]): string[] => list.map((u) => u.utterance_id)

describe('withoutEchoes', () => {
  it('hides the later arrival when another phone heard the same sentence', () => {
    const shown = withoutEchoes([
      utterance('a', zack, 'It uses BM25 for keyword matches.', 1000),
      utterance('b', clayton, 'it uses bm 25 for keyword matches', 1900),
    ])
    expect(ids(shown)).toEqual(['a'])
  })

  it('goes by arrival order even when the later arrival claims an earlier start', () => {
    const first = utterance('a', zack, 'It uses BM25 for keyword matches.', 1000)
    const echo = { ...utterance('b', clayton, 'It uses BM25 for keyword matches.', 1400), started_at: 200 }
    expect(ids(withoutEchoes([first, echo]))).toEqual(['a'])
  })

  it('keeps both when the later one arrives more than three seconds after', () => {
    const shown = withoutEchoes([
      utterance('a', zack, 'It uses BM25 for keyword matches.', 1000),
      utterance('b', clayton, 'It uses BM25 for keyword matches.', 4500),
    ])
    expect(ids(shown)).toEqual(['a', 'b'])
  })

  it('keeps short replies, which share words by chance', () => {
    const shown = withoutEchoes([
      utterance('a', zack, 'Yeah, for sure!', 1000),
      utterance('b', clayton, 'Yeah, for sure!', 1500),
    ])
    expect(ids(shown)).toEqual(['a', 'b'])
  })

  it('keeps a growing interim until it covers 80% of the longer sentence', () => {
    const full = utterance('a', zack, 'It uses BM25 for keyword matches and RRF to rank.', 1000)
    const partial = utterance('b', clayton, 'It uses BM25 for', 1300)
    const nearlyAll = utterance('b', clayton, 'It uses BM25 for keyword matches and RRF to', 1300)
    expect(ids(withoutEchoes([full, partial]))).toEqual(['a', 'b'])
    expect(ids(withoutEchoes([full, nearlyAll]))).toEqual(['a'])
  })

  it('never hides two utterances from the same speaker', () => {
    const shown = withoutEchoes([
      utterance('a', zack, 'We do managed hybrid search.', 1000),
      utterance('b', zack, 'We do managed hybrid search.', 1800),
    ])
    expect(ids(shown)).toEqual(['a', 'b'])
  })

  it('does not hide a real answer that follows an echo', () => {
    const shown = withoutEchoes([
      utterance('a', zack, 'It uses BM25 for keyword matches.', 1000),
      utterance('b', clayton, 'It uses BM25 for keyword matches.', 1500),
      utterance('c', clayton, 'Oh, that makes a lot of sense!', 2600),
    ])
    expect(ids(shown)).toEqual(['a', 'c'])
  })
})
