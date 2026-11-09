import type { CardShownEvent, ServerCardEvent, Term, TranscriptEvent } from '@contracts'
import { describe, expect, it } from 'vitest'
import type { Match } from '@/lib/match/matcher'
import {
  INITIAL_ROOM_DATA,
  MAX_UTTERANCES,
  reduceCardShown,
  reduceServerCard,
  reduceTranscript,
  type RoomData,
} from './store'

const zack = { user_id: 'u-zack', name: 'Zack' }
const base: RoomData = { ...INITIAL_ROOM_DATA, role: 'speaker', me: { user_id: 'u-me', name: 'Me' } }

function transcript(overrides: Partial<TranscriptEvent> = {}): TranscriptEvent {
  return {
    type: 'transcript',
    utterance_id: 'utt-1',
    seq: 0,
    is_final: false,
    text: 'It uses BM25',
    words: [
      { w: 'It', start_ms: 0, end_ms: 120 },
      { w: 'uses', start_ms: 160, end_ms: 380 },
      { w: 'BM25', start_ms: 420, end_ms: 900 },
    ],
    started_at: 10_000,
    speaker: zack,
    ...overrides,
  }
}

const bm25: Match = { term_id: 'bm25', first_word: 2, last_word: 2 }

describe('reduceTranscript', () => {
  it('shows a card for an unknown term, timed to the end of the matched word', () => {
    const next = reduceTranscript(base, transcript(), [bm25])
    expect(next.stack.full).toHaveLength(1)
    expect(next.stack.full[0]).toMatchObject({
      term_id: 'bm25',
      tier: 1,
      utterance_id: 'utt-1',
      spoken_at: 10_900,
      rendered_at: null,
    })
    expect(next.heard.bm25).toBe(1)
  })

  it('does not repeat the card or the count when a later interim has the same word', () => {
    const first = reduceTranscript(base, transcript(), [bm25])
    const second = reduceTranscript(first, transcript({ seq: 1, text: 'It uses BM25 for' }), [bm25])
    expect(second.stack.full).toHaveLength(1)
    expect(second.heard.bm25).toBe(1)
    expect(second.utterances).toHaveLength(1)
  })

  it('shows no card for a term the person already knows, but still counts it', () => {
    const knows = { ...base, knowledge: { bm25: 'known' as const } }
    const next = reduceTranscript(knows, transcript(), [bm25])
    expect(next.stack.full).toHaveLength(0)
    expect(next.heard.bm25).toBe(1)
  })

  it('ignores an update that arrives out of order', () => {
    const newer = reduceTranscript(base, transcript({ seq: 3, text: 'It uses BM25 for keyword' }), [])
    expect(reduceTranscript(newer, transcript({ seq: 2 }), [])).toBe(newer)
  })

  it('ignores anything after the final for that utterance', () => {
    const final = reduceTranscript(base, transcript({ seq: 4, is_final: true }), [])
    expect(reduceTranscript(final, transcript({ seq: 5 }), [bm25])).toBe(final)
  })

  it('gives a viewer captions but no cards of its own', () => {
    const viewer = { ...base, role: 'viewer' as const }
    const next = reduceTranscript(viewer, transcript(), [bm25])
    expect(next.utterances).toHaveLength(1)
    expect(next.stack.full).toHaveLength(0)
  })

  it('keeps only the most recent utterances', () => {
    let state = base
    for (let i = 0; i < MAX_UTTERANCES + 5; i += 1) {
      state = reduceTranscript(state, transcript({ utterance_id: `utt-${i}` }), [])
    }
    expect(state.utterances).toHaveLength(MAX_UTTERANCES)
    expect(state.utterances[0]?.utterance_id).toBe('utt-5')
  })

  it('splits the text into words when the recogniser sent no timings', () => {
    const next = reduceTranscript(base, transcript({ words: [], text: 'hello there' }), [])
    expect(next.utterances[0]?.words.map((w) => w.w)).toEqual(['hello', 'there'])
  })
})

describe('reduceServerCard', () => {
  const term: Term = {
    id: 'ebpf',
    term: 'eBPF',
    aliases: [],
    say: 'ee-bee-pee-EFF',
    category: 'cloud-native',
    level: 4,
    simple_def: 'A safe way to run small programs inside the operating system.',
    prereqs: [],
    source: 'llm',
  }
  const event: ServerCardEvent = { type: 'card', tier: 3, term, utterance_id: 'utt-9', spoken_at: 5000 }

  it('learns the new term and shows its card with the server tier', () => {
    const next = reduceServerCard(base, event)
    expect(next.terms.ebpf).toEqual(term)
    expect(next.stack.full[0]).toMatchObject({ term_id: 'ebpf', tier: 3, spoken_at: 5000 })
  })

  it('does not show the same term twice', () => {
    const once = reduceServerCard(base, event)
    expect(reduceServerCard(once, event).stack.full).toHaveLength(1)
  })
})

describe('reduceCardShown', () => {
  const shown: CardShownEvent = {
    type: 'card.shown',
    card_id: 'utt-1:bm25',
    term_id: 'bm25',
    tier: 1,
    utterance_id: 'utt-1',
    spoken_at: 10_900,
    rendered_at: 11_180,
    word_to_card_ms: 280,
    user: zack,
  }

  it('files the card under the phone that showed it and records the latency', () => {
    const next = reduceCardShown(base, shown)
    expect(next.shownByUser['u-zack']).toEqual([shown])
    expect(next.latencies).toEqual([280])
  })

  it('ignores a duplicate report of the same card', () => {
    const once = reduceCardShown(base, shown)
    expect(reduceCardShown(once, shown)).toBe(once)
  })
})
