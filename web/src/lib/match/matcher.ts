// On-device glossary matcher (tier 1 cards). Behaviour: contracts/README.md section 6.
// Whole words, longest phrase first, no overlaps; ambiguous terms need a context word nearby.

import type { Term } from '../../../../contracts/types';
import { normalizeWords } from './normalize';

export interface Match {
  term_id: string;
  /** Index of the first input word of the match. */
  first_word: number;
  /** Index of the last input word of the match (inclusive). */
  last_word: number;
}

export type Matcher = (words: string[]) => Match[];

interface Entry {
  readonly termId: string;
  readonly tokens: readonly string[];
  /** null for ordinary terms; the allowed context words for ambiguous ones. */
  readonly context: ReadonlySet<string> | null;
  readonly order: number;
}

type Index = ReadonlyMap<string, readonly Entry[]>;

export const CONTEXT_WINDOW_WORDS = 5;

const phraseTokens = (phrase: string): string[] => normalizeWords(phrase.split(/\s+/)).tokens;

function entriesFor(term: Term, termOrder: number): Entry[] {
  const context = term.ambiguous ? new Set((term.context ?? []).flatMap(phraseTokens)) : null;
  const phrases = [term.term, ...term.aliases].map(phraseTokens).filter((tokens) => tokens.length > 0);
  const unique = new Map(phrases.map((tokens) => [tokens.join(' '), tokens] as const));
  return [...unique.values()].map((tokens) => ({ termId: term.id, tokens, context, order: termOrder }));
}

/** Entries bucketed by first token, longest first, then in glossary order. */
function buildIndex(terms: readonly Term[]): Index {
  const buckets = new Map<string, Entry[]>();
  terms.flatMap(entriesFor).forEach((entry) => {
    const key = entry.tokens[0] as string;
    buckets.set(key, [...(buckets.get(key) ?? []), entry]);
  });
  return new Map(
    [...buckets].map(([key, entries]) => [
      key,
      [...entries].sort((a, b) => b.tokens.length - a.tokens.length || a.order - b.order),
    ]),
  );
}

function phraseAt(tokens: readonly string[], start: number, phrase: readonly string[]): boolean {
  if (start + phrase.length > tokens.length) return false;
  for (let k = 0; k < phrase.length; k += 1) {
    if (tokens[start + k] !== phrase[k]) return false;
  }
  return true;
}

function hasContextNearby(tokens: readonly string[], start: number, end: number, context: ReadonlySet<string>): boolean {
  const from = Math.max(0, start - CONTEXT_WINDOW_WORDS);
  const to = Math.min(tokens.length - 1, end + CONTEXT_WINDOW_WORDS);
  for (let j = from; j <= to; j += 1) {
    const outsideMatch = j < start || j > end;
    if (outsideMatch && context.has(tokens[j] as string)) return true;
  }
  return false;
}

function entryAt(index: Index, tokens: readonly string[], start: number): Entry | undefined {
  const candidates = index.get(tokens[start] as string) ?? [];
  return candidates.find((entry) => {
    if (!phraseAt(tokens, start, entry.tokens)) return false;
    const end = start + entry.tokens.length - 1;
    return entry.context === null || hasContextNearby(tokens, start, end, entry.context);
  });
}

/** Builds the index once; the returned function is pure and safe to call on every interim. */
export function createMatcher(terms: Term[]): Matcher {
  const index = buildIndex(terms);
  return (words: string[]): Match[] => {
    const { tokens, origin } = normalizeWords(words);
    const matches: Match[] = [];
    let i = 0;
    while (i < tokens.length) {
      const entry = entryAt(index, tokens, i);
      if (entry) {
        const end = i + entry.tokens.length - 1;
        const [firstWord] = origin[i] as [number, number];
        const [, lastWord] = origin[end] as [number, number];
        matches.push({ term_id: entry.termId, first_word: firstWord, last_word: lastWord });
        i = end + 1;
      } else {
        i += 1;
      }
    }
    return matches;
  };
}
