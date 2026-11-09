import { describe, expect, it } from 'vitest'
import { buildTimeline, CONVERSATION, framesFor, splitSentences, timeWords } from './script.ts'

describe('splitSentences', () => {
  it('keeps the punctuation with each sentence', () => {
    expect(splitSentences('Great question! It uses BM25. Why?')).toEqual([
      'Great question!',
      'It uses BM25.',
      'Why?',
    ])
  })

  it('returns text with no end punctuation as one sentence', () => {
    expect(splitSentences('managed hybrid search')).toEqual(['managed hybrid search'])
  })
})

describe('timeWords', () => {
  it('gives every word an increasing, non-overlapping window', () => {
    const words = timeWords('It uses BM25 for keyword matches, while the embeddings handle meaning')
    expect(words.map((w) => w.w)).toContain('BM25')
    words.forEach((word, i) => {
      expect(word.end_ms).toBeGreaterThan(word.start_ms)
      if (i > 0) expect(word.start_ms).toBeGreaterThan(words[i - 1]!.end_ms)
    })
  })
})

describe('framesFor', () => {
  const words = timeWords('we do SRE for Kubernetes clusters.')
  const frames = framesFor(words)

  it('grows word by word and ends with exactly one final frame', () => {
    const counts = frames.map((f) => f.word_count)
    expect([...counts].sort((a, b) => a - b)).toEqual(counts)
    expect(frames.filter((f) => f.is_final)).toHaveLength(1)
    expect(frames[frames.length - 1]).toMatchObject({ is_final: true, word_count: words.length })
  })

  it('never emits a word before it was spoken', () => {
    for (const frame of frames) {
      expect(frame.at_ms).toBeGreaterThan(words[frame.word_count - 1]!.end_ms)
    }
  })

  it('keeps frame times strictly increasing', () => {
    frames.forEach((frame, i) => {
      if (i > 0) expect(frame.at_ms).toBeGreaterThan(frames[i - 1]!.at_ms)
    })
  })
})

describe('buildTimeline', () => {
  const timeline = buildTimeline()

  it('alternates between the two speakers and never overlaps utterances', () => {
    expect(new Set(timeline.map((u) => u.speaker))).toEqual(new Set(['Clayton', 'Zack']))
    timeline.forEach((utterance, i) => {
      if (i === 0) return
      const prev = timeline[i - 1]!
      const prevEnd = prev.starts_at_ms + prev.frames[prev.frames.length - 1]!.at_ms
      expect(utterance.starts_at_ms).toBeGreaterThan(prevEnd)
    })
  })

  it('covers every sentence of the script in about a minute', () => {
    const sentences = CONVERSATION.flatMap((line) => splitSentences(line.text))
    expect(timeline).toHaveLength(sentences.length)
    const last = timeline[timeline.length - 1]!
    const total = last.starts_at_ms + last.frames[last.frames.length - 1]!.at_ms
    expect(total).toBeGreaterThan(40_000)
    expect(total).toBeLessThan(90_000)
  })
})
