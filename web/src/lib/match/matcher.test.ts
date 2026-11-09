import { describe, expect, it } from 'vitest';
import type { Glossary, Term } from '../../../../contracts/types';
import glossaryJson from '../../../../contracts/fixtures/glossary.sample.json';
import casesJson from '../../../../contracts/fixtures/matcher_cases.json';
import { createMatcher } from './matcher';

interface MatcherCase {
  text: string;
  expect: string[];
  note?: string;
}

const glossary = glossaryJson as unknown as Glossary;
const cases: MatcherCase[] = casesJson;
const sorted = (ids: string[]): string[] => [...new Set(ids)].sort();

function makeTerm(id: string, extra: Partial<Term> = {}): Term {
  return {
    id,
    term: id,
    aliases: [],
    say: id,
    category: 'test',
    level: 2,
    simple_def: 'A test term.',
    prereqs: [],
    source: 'seed',
    ...extra,
  };
}

describe('createMatcher against the shared fixtures', () => {
  const match = createMatcher(glossary.terms);

  it.each(cases)('"$text"', ({ text, expect: expected }) => {
    const found = match(text.split(' ')).map((m) => m.term_id);
    expect(sorted(found)).toEqual(sorted(expected));
  });
});

describe('createMatcher', () => {
  const match = createMatcher(glossary.terms);

  it('reports word indexes in the caller\'s words, not in tokens', () => {
    const words = 'and r r f to rank with bm twenty five'.split(' ');
    expect(match(words)).toEqual([
      { term_id: 'rrf', first_word: 1, last_word: 3 },
      { term_id: 'bm25', first_word: 7, last_word: 9 },
    ]);
  });

  it('prefers the longest term and never overlaps', () => {
    const words = 'root cause analysis of the crash loop back off'.split(' ');
    expect(match(words)).toEqual([
      { term_id: 'root-cause', first_word: 0, last_word: 2 },
      { term_id: 'crashloopbackoff', first_word: 5, last_word: 8 },
    ]);
  });

  it('matches whole words only', () => {
    expect(match('the podcast was about ragtime'.split(' '))).toEqual([]);
  });

  it('matches an ambiguous term only within five words of a context word', () => {
    const near = 'kubernetes really does need this service'.split(' ');
    const far = 'kubernetes really does need all this service'.split(' ');
    expect(match(near).map((m) => m.term_id)).toEqual(['kubernetes', 'service']);
    expect(match(far).map((m) => m.term_id)).toEqual(['kubernetes']);
  });

  it('accepts a context word after the ambiguous term', () => {
    expect(match('the service behind the ingress'.split(' ')).map((m) => m.term_id)).toEqual(['service']);
  });

  it('returns matches in spoken order, including repeats', () => {
    const ids = match('pods and vectors and more pods'.split(' ')).map((m) => m.term_id);
    expect(ids).toEqual(['pod', 'vector', 'pod']);
  });

  it('keeps earlier matches stable as an interim transcript grows', () => {
    const words = 'we do SRE for Kubernetes clusters and RAG with embeddings'.split(' ');
    let previous: string[] = [];
    for (let end = 1; end <= words.length; end += 1) {
      const current = match(words.slice(0, end)).map((m) => `${m.term_id}@${m.first_word}`);
      expect(current.slice(0, previous.length)).toEqual(previous);
      previous = current;
    }
    expect(previous).toHaveLength(5);
  });

  it('gives the same answer every time and leaves its inputs alone', () => {
    const words = 'expose the pod with a Kubernetes service'.split(' ');
    const copy = [...words];
    expect(match(words)).toEqual(match(words));
    expect(words).toEqual(copy);
  });

  it('lets the earlier glossary term win when two terms share a phrase', () => {
    const tie = createMatcher([makeTerm('first', { aliases: ['shared phrase'] }), makeTerm('second', { aliases: ['shared phrase'] })]);
    expect(tie(['shared', 'phrase']).map((m) => m.term_id)).toEqual(['first']);
  });

  it('handles an empty glossary and empty input', () => {
    expect(createMatcher([])(['anything'])).toEqual([]);
    expect(match([])).toEqual([]);
  });

  it('matches a 30-word utterance against 200 terms in well under 1 ms', () => {
    const many: Term[] = Array.from({ length: 200 }, (_, i) =>
      makeTerm(`term-${i}`, { term: `widget${i}`, aliases: [`gadget${i} mark two`, `wid get${i}`] }),
    );
    const fast = createMatcher([...glossary.terms, ...many]);
    const utterance = (
      'so we expose the pod with a Kubernetes service and it uses bm twenty five plus r r f ' +
      'for hybrid search while widget42 and gadget7 mark two keep running'
    ).split(' ');
    expect(utterance).toHaveLength(30);
    for (let i = 0; i < 200; i += 1) fast(utterance);

    const runs = 2000;
    const started = performance.now();
    for (let i = 0; i < runs; i += 1) fast(utterance);
    const perCallMs = (performance.now() - started) / runs;

    expect(fast(utterance).map((m) => m.term_id)).toContain('term-42');
    expect(perCallMs).toBeLessThan(0.5);
  });
});
