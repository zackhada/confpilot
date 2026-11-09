// Both phones may hear both voices, so the same sentence can arrive twice under two
// speakers (contracts/README.md section 5). The first to arrive stays; the echo is hidden.
import { normalizeWords } from '@/lib/match/normalize'
import type { Utterance } from '@/room/store'

export const DUPLICATE_WINDOW_MS = 3000
export const DUPLICATE_MIN_WORDS = 4
export const DUPLICATE_OVERLAP = 0.8

function tokensOf(utterance: Utterance): string[] {
  return normalizeWords(utterance.words.map((word) => word.w)).tokens
}

/** How many words two utterances share, counting repeats (a multiset intersection). */
function wordsInCommon(a: readonly string[], b: readonly string[]): number {
  const remaining = new Map<string, number>()
  for (const token of a) remaining.set(token, (remaining.get(token) ?? 0) + 1)
  let common = 0
  for (const token of b) {
    const left = remaining.get(token) ?? 0
    if (left === 0) continue
    remaining.set(token, left - 1)
    common += 1
  }
  return common
}

function isEchoOf(later: Utterance, laterTokens: string[], earlier: Utterance): boolean {
  if (later.speaker.user_id === earlier.speaker.user_id) return false
  if (later.first_seen_at - earlier.first_seen_at > DUPLICATE_WINDOW_MS) return false
  const earlierTokens = tokensOf(earlier)
  if (laterTokens.length < DUPLICATE_MIN_WORDS || earlierTokens.length < DUPLICATE_MIN_WORDS) return false
  const longer = Math.max(laterTokens.length, earlierTokens.length)
  return wordsInCommon(earlierTokens, laterTokens) >= DUPLICATE_OVERLAP * longer
}

/**
 * Utterances to show, in arrival order. An utterance is hidden when it arrived within three
 * seconds after a visible one from a different speaker, both have at least four words, and
 * the words in common are at least 80% of the longer one. The decision goes by arrival
 * order only, so a caption that is already on screen is never the one removed.
 */
export function withoutEchoes(utterances: readonly Utterance[]): Utterance[] {
  const shown: Utterance[] = []
  for (const utterance of utterances) {
    const tokens = tokensOf(utterance)
    if (!shown.some((earlier) => isEchoOf(utterance, tokens, earlier))) shown.push(utterance)
  }
  return shown
}
