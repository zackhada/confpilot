// On-device glossary matcher (tier 1 cards). Behaviour: contracts/README.md section 6.
// Whole words, longest phrase first, no overlaps. An ambiguous term needs tech context within
// five words: one of its `context` words, or (with no list) a matched, non-ambiguous term of
// the same category.

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
  readonly category: string;
  readonly ambiguous: boolean;
  /** The term's own context words; null when it has none. */
  readonly context: ReadonlySet<string> | null;
  readonly order: number;
}

/** A matched entry and its inclusive token span. */
interface Hit {
  readonly entry: Entry;
  readonly start: number;
  readonly end: number;
}

type Index = ReadonlyMap<string, readonly Entry[]>;
type Accept = (hit: Hit) => boolean;

export const CONTEXT_WINDOW_WORDS = 5;

// "Service (Kubernetes)" is spoken as "service": the bracketed part only labels the card.
const BRACKETED = /\s*\([^)]*\)\s*/g;

const phraseTokens = (phrase: string): string[] => normalizeWords(phrase.split(/\s+/)).tokens;

function entriesFor(term: Term, termOrder: number): Entry[] {
  const contextWords = (term.context ?? []).flatMap(phraseTokens);
  const shared = {
    termId: term.id,
    category: term.category,
    ambiguous: term.ambiguous === true,
    context: contextWords.length > 0 ? new Set(contextWords) : null,
    order: termOrder,
  };
  const spoken = [term.term.replace(BRACKETED, ' '), ...term.aliases];
  const phrases = spoken.map(phraseTokens).filter((tokens) => tokens.length > 0);
  const unique = new Map(phrases.map((tokens) => [tokens.join(' '), tokens] as const));
  return [...unique.values()].map((tokens) => ({ ...shared, tokens }));
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

function hasContextWordNearby(tokens: readonly string[], hit: Hit, context: ReadonlySet<string>): boolean {
  const from = Math.max(0, hit.start - CONTEXT_WINDOW_WORDS);
  const to = Math.min(tokens.length - 1, hit.end + CONTEXT_WINDOW_WORDS);
  for (let j = from; j <= to; j += 1) {
    const outsideMatch = j < hit.start || j > hit.end;
    if (outsideMatch && context.has(tokens[j] as string)) return true;
  }
  return false;
}

function hasAnchorNearby(hit: Hit, anchors: readonly Hit[]): boolean {
  return anchors.some(
    (anchor) =>
      anchor.entry.category === hit.entry.category &&
      anchor.start <= hit.end + CONTEXT_WINDOW_WORDS &&
      anchor.end >= hit.start - CONTEXT_WINDOW_WORDS,
  );
}

/** Left to right, longest accepted phrase first, never overlapping. */
function scan(index: Index, tokens: readonly string[], accept: Accept): Hit[] {
  const hits: Hit[] = [];
  let i = 0;
  while (i < tokens.length) {
    const start = i;
    const hit = (index.get(tokens[start] as string) ?? [])
      .filter((entry) => phraseAt(tokens, start, entry.tokens))
      .map((entry): Hit => ({ entry, start, end: start + entry.tokens.length - 1 }))
      .find(accept);
    if (hit) hits.push(hit);
    i = hit ? hit.end + 1 : i + 1;
  }
  return hits;
}

function findHits(index: Index, tokens: readonly string[]): Hit[] {
  const passesOwnContext: Accept = (hit) =>
    !hit.entry.ambiguous || hit.entry.context === null || hasContextWordNearby(tokens, hit, hit.entry.context);
  // First pass: ambiguous terms with no context list are let through, to find the anchors.
  const tentative = scan(index, tokens, passesOwnContext);
  const needsAnchor = (hit: Hit): boolean => hit.entry.ambiguous && hit.entry.context === null;
  if (!tentative.some(needsAnchor)) return tentative;
  // Second pass: those terms now need a non-ambiguous term of their category nearby. Scanning
  // again (rather than filtering) lets a shorter term match where a longer one was rejected.
  const anchors = tentative.filter((hit) => !hit.entry.ambiguous);
  return scan(index, tokens, (hit) => passesOwnContext(hit) && (!needsAnchor(hit) || hasAnchorNearby(hit, anchors)));
}

/** Builds the index once; the returned function is pure and safe to call on every interim. */
export function createMatcher(terms: Term[]): Matcher {
  const index = buildIndex(terms);
  return (words: string[]): Match[] => {
    const { tokens, origin } = normalizeWords(words);
    return findHits(index, tokens).map((hit) => {
      const [firstWord] = origin[hit.start] as [number, number];
      const [, lastWord] = origin[hit.end] as [number, number];
      return { term_id: hit.entry.termId, first_word: firstWord, last_word: lastWord };
    });
  };
}
