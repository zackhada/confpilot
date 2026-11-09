// The demo conversation from docs/CONFPILOT_PLAN.md, turned into timed speech-to-text
// frames. Pure functions only, so the timing can be unit tested.
import type { Word } from '../../contracts/types.ts'

export type ScriptSpeaker = 'Clayton' | 'Zack'

export interface ScriptLine {
  speaker: ScriptSpeaker
  text: string
}

export const CONVERSATION: readonly ScriptLine[] = [
  { speaker: 'Clayton', text: 'I work at Radar, we do SRE for Kubernetes clusters. What do you do?' },
  {
    speaker: 'Zack',
    text: 'I work at Elasticsearch, we do managed hybrid search, including RAG and keyword search.',
  },
  {
    speaker: 'Clayton',
    text: 'Nice. On our side, when a pod goes into CrashLoopBackOff, our AI SRE finds the root cause before the on-call engineer wakes up.',
  },
  {
    speaker: 'Clayton',
    text: "So that will help power apps' search engines, or what are customers trying to do with your technology?",
  },
  {
    speaker: 'Zack',
    text: 'Yeah, for sure! Wikipedia is one of our customers. Nowadays, a lot of our customers are using our product to embed thousands of documents into a knowledge base the agent can pull from.',
  },
  {
    speaker: 'Clayton',
    text: "Interesting, so those documents are turned into vectors that can be retrieved easily. How does your search service determine what is most relevant to the agent or user's query?",
  },
  {
    speaker: 'Zack',
    text: 'Great question! It uses BM25 for keyword matches, while the embeddings handle meaning, and RRF to rank the results to return to the user or agent.',
  },
  {
    speaker: 'Clayton',
    text: 'Oh, makes sense! At Radar, we have some internal search service use cases. Can I get your LinkedIn?',
  },
]

const BASE_WORD_MS = 130
const PER_CHAR_MS = 42
const MAX_WORD_MS = 520
const WORD_GAP_MS = 45
const CLAUSE_PAUSE_MS = 180
const FINAL_AFTER_MS = 380
const MIN_FRAME_SPACING_MS = 60

/** Split a spoken turn into sentences; speech-to-text finalises roughly once per sentence. */
export function splitSentences(text: string): string[] {
  return (text.match(/[^.!?]+[.!?]+|[^.!?]+$/g) ?? []).map((s) => s.trim()).filter(Boolean)
}

/** Give each word a start and end offset, at a natural speaking pace. */
export function timeWords(sentence: string): Word[] {
  const tokens = sentence.split(/\s+/).filter(Boolean)
  let cursor = 0
  return tokens.map((w) => {
    const spoken = Math.min(MAX_WORD_MS, BASE_WORD_MS + PER_CHAR_MS * w.replace(/\W/g, '').length)
    const word: Word = { w, start_ms: cursor, end_ms: cursor + spoken }
    cursor = word.end_ms + WORD_GAP_MS + (/[,;:]$/.test(w) ? CLAUSE_PAUSE_MS : 0)
    return word
  })
}

/** Deterministic stand-in for recogniser delay: 140 to 320 ms, varying per word. */
export function sttDelayMs(wordIndex: number): number {
  return 140 + ((wordIndex * 73) % 181)
}

export interface Frame {
  /** Milliseconds after the utterance's audio began. */
  at_ms: number
  /** How many words the recogniser has produced so far. */
  word_count: number
  is_final: boolean
}

/** Interim frames that grow word by word, then one final frame with every word. */
export function framesFor(words: readonly Word[]): Frame[] {
  const frames: Frame[] = []
  words.forEach((word, i) => {
    const at = word.end_ms + sttDelayMs(i)
    const last = frames[frames.length - 1]
    if (last && at - last.at_ms < MIN_FRAME_SPACING_MS) {
      frames[frames.length - 1] = { ...last, word_count: i + 1 }
      return
    }
    frames.push({ at_ms: Math.max(at, last ? last.at_ms : 0), word_count: i + 1, is_final: false })
  })
  const lastWord = words[words.length - 1]
  const lastFrame = frames[frames.length - 1]
  if (!lastWord || !lastFrame) return frames
  const finalAt = Math.max(lastWord.end_ms + FINAL_AFTER_MS, lastFrame.at_ms + MIN_FRAME_SPACING_MS)
  return [...frames, { at_ms: finalAt, word_count: words.length, is_final: true }]
}

export interface TimedUtterance {
  speaker: ScriptSpeaker
  /** Milliseconds after the replay began. */
  starts_at_ms: number
  words: Word[]
  frames: Frame[]
}

const SENTENCE_GAP_MS = 320
const TURN_GAP_MS = 750

/** Lay the whole conversation out on one timeline, one utterance per sentence. */
export function buildTimeline(lines: readonly ScriptLine[] = CONVERSATION): TimedUtterance[] {
  const timeline: TimedUtterance[] = []
  let cursor = 0
  for (const line of lines) {
    for (const sentence of splitSentences(line.text)) {
      const words = timeWords(sentence)
      const frames = framesFor(words)
      timeline.push({ speaker: line.speaker, starts_at_ms: cursor, words, frames })
      const end = frames[frames.length - 1]?.at_ms ?? 0
      cursor += end + SENTENCE_GAP_MS
    }
    cursor += TURN_GAP_MS
  }
  return timeline
}
