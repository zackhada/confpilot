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
  readonly key: string;
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

interface Index {
  readonly entries: ReadonlyMap<string, readonly Entry[]>;
  readonly prefixes: ReadonlySet<string>;
}
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
  const unique = new Set(phrases.map((tokens) => tokens.join('')));
  return [...unique].map((key) => ({ ...shared, key }));
}

/** Entries indexed by their glued form, with prefixes for efficient token-run matching. */
function buildIndex(terms: readonly Term[]): Index {
  const buckets = new Map<string, Entry[]>();
  terms.flatMap(entriesFor).forEach((entry) => {
    buckets.set(entry.key, [...(buckets.get(entry.key) ?? []), entry]);
  });
  const prefixes = new Set<string>();
  for (const key of buckets.keys()) {
    for (let end = 1; end <= key.length; end += 1) prefixes.add(key.slice(0, end));
  }
  return {
    entries: new Map(
      [...buckets].map(([key, entries]) => [key, [...entries].sort((a, b) => a.order - b.order)]),
    ),
    prefixes,
  };
}

function hasContextWordNearby(
  tokens: readonly string[],
  origin: readonly [number, number][],
  hit: Hit,
  context: ReadonlySet<string>,
): boolean {
  const [hitFirst] = origin[hit.start] as [number, number];
  const [, hitLast] = origin[hit.end] as [number, number];
  for (let j = 0; j < tokens.length; j += 1) {
    const outsideMatch = j < hit.start || j > hit.end;
    const [wordFirst, wordLast] = origin[j] as [number, number];
    const nearby = wordLast >= hitFirst - CONTEXT_WINDOW_WORDS && wordFirst <= hitLast + CONTEXT_WINDOW_WORDS;
    if (outsideMatch && nearby && context.has(tokens[j] as string)) return true;
  }
  return false;
}

function hasAnchorNearby(hit: Hit, anchors: readonly Hit[], origin: readonly [number, number][]): boolean {
  const [hitFirst] = origin[hit.start] as [number, number];
  const [, hitLast] = origin[hit.end] as [number, number];
  return anchors.some((anchor) => {
    const [anchorFirst] = origin[anchor.start] as [number, number];
    const [, anchorLast] = origin[anchor.end] as [number, number];
    return (
      anchor.entry.category === hit.entry.category &&
      anchorFirst <= hitLast + CONTEXT_WINDOW_WORDS &&
      anchorLast >= hitFirst - CONTEXT_WINDOW_WORDS
    );
  });
}

/** Left to right, longest accepted phrase first, never overlapping. */
function scan(index: Index, tokens: readonly string[], accept: Accept): Hit[] {
  const hits: Hit[] = [];
  let i = 0;
  while (i < tokens.length) {
    const start = i;
    let key = '';
    let best: Hit | undefined;
    for (let end = start; end < tokens.length; end += 1) {
      key += tokens[end] as string;
      if (!index.prefixes.has(key)) break;
      const candidates = index.entries.get(key);
      const hit = candidates
        ?.map((entry): Hit => ({ entry, start, end }))
        .find(accept);
      if (hit) best = hit;
    }
    if (best) hits.push(best);
    i = best ? best.end + 1 : i + 1;
  }
  return hits;
}

function findHits(index: Index, tokens: readonly string[], origin: readonly [number, number][]): Hit[] {
  const passesOwnContext: Accept = (hit) =>
    !hit.entry.ambiguous || hit.entry.context === null || hasContextWordNearby(tokens, origin, hit, hit.entry.context);
  // First pass: ambiguous terms with no context list are let through, to find the anchors.
  const tentative = scan(index, tokens, passesOwnContext);
  const needsAnchor = (hit: Hit): boolean => hit.entry.ambiguous && hit.entry.context === null;
  if (!tentative.some(needsAnchor)) return tentative;
  // Second pass: those terms now need a non-ambiguous term of their category nearby. Scanning
  // again (rather than filtering) lets a shorter term match where a longer one was rejected.
  const anchors = tentative.filter((hit) => !hit.entry.ambiguous);
  return scan(index, tokens, (hit) => passesOwnContext(hit) && (!needsAnchor(hit) || hasAnchorNearby(hit, anchors, origin)));
}

/** Builds the index once; the returned function is pure and safe to call on every interim. */
export function createMatcher(terms: Term[]): Matcher {
  const index = buildIndex(terms);
  return (words: string[]): Match[] => {
    const { tokens, origin } = normalizeWords(words);
    return findHits(index, tokens, origin).map((hit) => {
      const [firstWord] = origin[hit.start] as [number, number];
      const [, lastWord] = origin[hit.end] as [number, number];
      return { term_id: hit.entry.termId, first_word: firstWord, last_word: lastWord };
    });
  };
}
