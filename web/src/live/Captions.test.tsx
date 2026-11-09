import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import type { Utterance } from '@/room/store'
import { Captions } from './Captions'
import { groupTurns } from './turns'

const zack = { user_id: 'u-zack', name: 'Zack' }
const me = { user_id: 'u-me', name: 'Clayton' }

function utterance(id: string, speaker: typeof zack, text: string, matches: Utterance['matches'] = []): Utterance {
  return {
    utterance_id: id,
    speaker,
    words: text.split(' ').map((w, i) => ({ w, start_ms: i * 300, end_ms: i * 300 + 250 })),
    matches,
    is_final: true,
    seq: 1,
    started_at: 0,
    first_seen_at: 0,
  }
}

describe('groupTurns', () => {
  it('joins consecutive utterances from one speaker into a single turn', () => {
    const turns = groupTurns([
      utterance('a', zack, 'Great question!'),
      utterance('b', zack, 'It uses BM25.'),
      utterance('c', me, 'Oh, makes sense!'),
    ])
    expect(turns.map((t) => [t.speaker.name, t.utterances.length])).toEqual([
      ['Zack', 2],
      ['Clayton', 1],
    ])
  })
})

describe('Captions', () => {
  const bm25 = { term_id: 'bm25', first_word: 2, last_word: 2 }

  it('labels each turn with the speaker, and the reader as You', () => {
    render(
      <Captions
        utterances={[utterance('a', zack, 'It uses BM25,'), utterance('b', me, 'Makes sense.')]}
        knowledge={{}}
        meId="u-me"
        emptyHint="Waiting"
      />,
    )
    expect(screen.getByText('Zack')).toBeInTheDocument()
    expect(screen.getByText('You')).toBeInTheDocument()
  })

  it('highlights a matched term without its trailing punctuation', () => {
    render(<Captions utterances={[utterance('a', zack, 'It uses BM25,', [bm25])]} knowledge={{}} emptyHint="Waiting" />)
    const mark = screen.getByText('BM25')
    expect(mark.tagName).toBe('MARK')
    expect(mark.className).toContain('decoration-fresh')
  })

  it('gives a known term a dotted underline instead of the new-term highlight', () => {
    render(
      <Captions
        utterances={[utterance('a', zack, 'It uses BM25,', [bm25])]}
        knowledge={{ bm25: 'known' }}
        emptyHint="Waiting"
      />,
    )
    expect(screen.getByText('BM25').className).toContain('decoration-dotted')
  })

  it('shows the hint when nobody has spoken yet', () => {
    render(<Captions utterances={[]} knowledge={{}} emptyHint="Waiting for someone to speak." />)
    expect(screen.getByText('Waiting for someone to speak.')).toBeInTheDocument()
  })
})
