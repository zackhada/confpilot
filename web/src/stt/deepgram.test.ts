import { describe, expect, it } from 'vitest'
import { createTranscriptAssembler, deepgramProtocols, isResults } from './deepgram'

function results(transcript: string, start: number, isFinal: boolean, wordStart = start) {
  const tokens = transcript.split(' ').filter(Boolean)
  return {
    type: 'Results',
    start,
    duration: 1,
    is_final: isFinal,
    speech_final: isFinal,
    channel: {
      alternatives: [
        {
          transcript,
          confidence: 0.99,
          words: tokens.map((word, i) => ({
            word: word.toLowerCase().replace(/[^a-z0-9]/g, ''),
            punctuated_word: word,
            start: wordStart + i * 0.4,
            end: wordStart + i * 0.4 + 0.3,
          })),
        },
      ],
    },
  }
}

const options = { idPrefix: 'u1-s1', streamStartedAt: 1_000_000 }

describe('isResults', () => {
  it.each([null, 'text', { type: 'Metadata' }, { type: 'Results', start: 0, is_final: true, channel: {} }])(
    'rejects %j',
    (value) => {
      expect(isResults(value)).toBe(false)
    },
  )
})

describe('createTranscriptAssembler', () => {
  it('keeps one utterance id across interims, with a rising seq, and closes it on the final', () => {
    const assemble = createTranscriptAssembler(options)
    const a = assemble(results('It uses', 2, false))
    const b = assemble(results('It uses BM25', 2, false))
    const c = assemble(results('It uses BM25.', 2, true))
    expect([a?.utterance_id, b?.utterance_id, c?.utterance_id]).toEqual(['u1-s1-0', 'u1-s1-0', 'u1-s1-0'])
    expect([a?.seq, b?.seq, c?.seq]).toEqual([0, 1, 2])
    expect([a?.is_final, b?.is_final, c?.is_final]).toEqual([false, false, true])
  })

  it('starts a new utterance after a final', () => {
    const assemble = createTranscriptAssembler(options)
    assemble(results('First one.', 0, true))
    const next = assemble(results('Second', 3, false))
    expect(next).toMatchObject({ utterance_id: 'u1-s1-1', seq: 0 })
  })

  it('reports started_at in server time and word offsets within the utterance', () => {
    const assemble = createTranscriptAssembler(options)
    const event = assemble(results('It uses BM25', 2, false, 2.1))
    expect(event?.started_at).toBe(1_002_000)
    expect(event?.words).toEqual([
      { w: 'It', start_ms: 100, end_ms: 400 },
      { w: 'uses', start_ms: 500, end_ms: 800 },
      { w: 'BM25', start_ms: 900, end_ms: 1200 },
    ])
  })

  it('skips empty results and messages that are not results', () => {
    const assemble = createTranscriptAssembler(options)
    expect(assemble(results('', 0, false))).toBeNull()
    expect(assemble({ type: 'Metadata', request_id: 'x' })).toBeNull()
    expect(assemble(results('Hello', 0, false))).toMatchObject({ utterance_id: 'u1-s1-0', seq: 0 })
  })
})

describe('deepgramProtocols', () => {
  it('sends the temporary token as a bearer subprotocol', () => {
    expect(deepgramProtocols('aaa.bbb.ccc')).toEqual(['bearer', 'aaa.bbb.ccc'])
  })
})
