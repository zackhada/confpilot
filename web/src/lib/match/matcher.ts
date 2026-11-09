// STUB written by the UI slice so the app compiles and runs. The pure-logic owner replaces
// this file with the real matcher (number words, spelled-out letters, the shared fixture).
// This stand-in only lowercases, strips punctuation and matches whole words, longest first.
import type { Term } from '@contracts'

export interface Match {
  term_id: string
  /** Index of the first matched word in `words`. */
  first_word: number
  /** Index of the last matched word in `words`. */
  last_word: number
}

const CONTEXT_WINDOW = 5

function normalize(word: string): string {
  return word.toLowerCase().replace(/[^a-z0-9]/g, '')
}

interface Pattern {
  term: Term
  tokens: string[]
}

function patternsFor(terms: Term[]): Pattern[] {
  return terms
    .flatMap((term) =>
      [term.term, ...term.aliases].flatMap((form) => {
        const tokens = form.split(/[\s-]+/).map(normalize).filter(Boolean)
        // "on-call" can arrive as one word or two, so match the joined form as well.
        return form.includes('-') ? [{ term, tokens }, { term, tokens: [tokens.join('')] }] : [{ term, tokens }]
      }),
    )
    .filter((p) => p.tokens.length > 0)
    .sort((a, b) => b.tokens.length - a.tokens.length)
}

function hasContext(term: Term, words: string[], first: number, last: number): boolean {
  if (!term.ambiguous) return true
  const context = new Set((term.context ?? []).map(normalize))
  const from = Math.max(0, first - CONTEXT_WINDOW)
  const to = Math.min(words.length - 1, last + CONTEXT_WINDOW)
  for (let i = from; i <= to; i += 1) {
    if ((i < first || i > last) && context.has(words[i] ?? '')) return true
  }
  return false
}

export function createMatcher(terms: Term[]): (words: string[]) => Match[] {
  const patterns = patternsFor(terms)
  return (rawWords) => {
    const words = rawWords.map(normalize)
    const taken = new Array<boolean>(words.length).fill(false)
    const matches: Match[] = []
    for (const { term, tokens } of patterns) {
      for (let start = 0; start + tokens.length <= words.length; start += 1) {
        const end = start + tokens.length - 1
        const fits = tokens.every((token, k) => words[start + k] === token && !taken[start + k])
        if (!fits || !hasContext(term, words, start, end)) continue
        for (let k = start; k <= end; k += 1) taken[k] = true
        matches.push({ term_id: term.id, first_word: start, last_word: end })
      }
    }
    return matches.sort((a, b) => a.first_word - b.first_word)
  }
}
