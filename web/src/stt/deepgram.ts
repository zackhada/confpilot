// Turns Deepgram streaming results into the room's TranscriptEvent (contracts/types.ts).
// Pure: no sockets and no clocks, so the mapping can be unit tested.
import type { TranscriptEvent, Word } from '@contracts'

interface DeepgramWord {
  word: string
  punctuated_word?: string
  start: number
  end: number
}

interface DeepgramResults {
  type: 'Results'
  /** Seconds from the start of this connection's audio to the start of this segment. */
  start: number
  is_final: boolean
  channel: { alternatives: { transcript: string; words: DeepgramWord[] }[] }
}

function isWord(value: unknown): value is DeepgramWord {
  if (typeof value !== 'object' || value === null) return false
  const v = value as Record<string, unknown>
  return typeof v.word === 'string' && typeof v.start === 'number' && typeof v.end === 'number'
}

/** Deepgram also sends Metadata, SpeechStarted and UtteranceEnd messages; those return false. */
export function isResults(value: unknown): value is DeepgramResults {
  if (typeof value !== 'object' || value === null) return false
  const v = value as Record<string, unknown>
  if (v.type !== 'Results' || typeof v.start !== 'number' || typeof v.is_final !== 'boolean') return false
  const alternatives = (v.channel as { alternatives?: unknown } | undefined)?.alternatives
  if (!Array.isArray(alternatives) || alternatives.length === 0) return false
  const first = alternatives[0] as { transcript?: unknown; words?: unknown }
  return typeof first.transcript === 'string' && Array.isArray(first.words) && first.words.every(isWord)
}

export interface AssemblerOptions {
  /** Makes utterance ids unique to this phone and this speech-to-text connection. */
  idPrefix: string
  /** Server-time ms at which this connection's audio began. */
  streamStartedAt: number
}

export type TranscriptAssembler = (message: unknown) => TranscriptEvent | null

/**
 * One utterance per Deepgram segment: every interim for a segment shares an utterance_id
 * with a rising seq, and the segment's final closes it. Empty results are skipped.
 */
export function createTranscriptAssembler({ idPrefix, streamStartedAt }: AssemblerOptions): TranscriptAssembler {
  let utteranceNumber = 0
  let seq = 0

  return (message) => {
    if (!isResults(message)) return null
    const alternative = message.channel.alternatives[0]
    const text = alternative?.transcript.trim() ?? ''
    if (!alternative || text === '') return null

    const segmentStartMs = message.start * 1000
    const words: Word[] = alternative.words.map((word) => ({
      w: word.punctuated_word ?? word.word,
      start_ms: Math.max(0, Math.round(word.start * 1000 - segmentStartMs)),
      end_ms: Math.max(0, Math.round(word.end * 1000 - segmentStartMs)),
    }))
    const event: TranscriptEvent = {
      type: 'transcript',
      utterance_id: `${idPrefix}-${utteranceNumber}`,
      seq,
      is_final: message.is_final,
      text,
      words,
      started_at: Math.round(streamStartedAt + segmentStartMs),
    }
    if (message.is_final) {
      utteranceNumber += 1
      seq = 0
    } else {
      seq += 1
    }
    return event
  }
}

/**
 * How a browser authenticates a Deepgram WebSocket: it cannot set an Authorization header,
 * so the credential travels as a subprotocol pair. A temporary access token (a JWT from
 * /v1/auth/grant) uses "bearer"; a short-lived API key uses "token". This mirrors what
 * Deepgram's own JavaScript SDK does.
 */
export function deepgramProtocols(token: string): [string, string] {
  const looksLikeJwt = token.split('.').length === 3
  return [looksLikeJwt ? 'bearer' : 'token', token]
}
