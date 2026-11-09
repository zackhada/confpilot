import { describe, expect, it } from 'vitest';
import type { Term, TermLevel } from '../../../contracts/types';
import type { ProbeAnswers } from './frontier';
import { DEFAULT_MAX_PROBE_QUESTIONS, answersToKnowledge, classify, nextProbeTerm } from './frontier';

const term = (id: string, level: TermLevel, prereqs: string[] = []): Term => ({
  id,
  term: id,
  aliases: [],
  say: id,
  category: 'test',
  level,
  simple_def: 'A test term.',
  prereqs,
  source: 'seed',
});

// a1 <- b2 <- d3 <- f4      c2 <- e3      g1 (no links)
const terms: Term[] = [
  term('a1', 1),
  term('b2', 2, ['a1']),
  term('c2', 2),
  term('d3', 3, ['b2']),
  term('e3', 3, ['c2']),
  term('f4', 4, ['d3']),
  term('g1', 1),
];

describe('classify', () => {
  it('puts every term in exactly one group, in glossary order', () => {
    expect(classify(terms, { a1: 'known', b2: 'known', c2: 'learning' })).toEqual({
      known: ['a1', 'b2'],
      frontier: ['c2', 'd3', 'g1'],
      beyond: ['e3', 'f4'],
    });
  });

  it('treats terms without prereqs as frontier for a new user', () => {
    expect(classify(terms, {})).toEqual({
      known: [],
      frontier: ['a1', 'c2', 'g1'],
      beyond: ['b2', 'd3', 'e3', 'f4'],
    });
  });

  it('keeps a known term known even when its prereqs are not', () => {
    expect(classify(terms, { f4: 'known' }).known).toEqual(['f4']);
  });

  it('ignores prereqs that are not in the glossary', () => {
    expect(classify([term('x', 2, ['missing'])], {})).toEqual({ known: [], frontier: ['x'], beyond: [] });
  });
});

describe('nextProbeTerm', () => {
  it('starts at the middle level with the best-connected term', () => {
    expect(nextProbeTerm(terms, {})).toBe('b2');
  });

  it('jumps to a harder dependent after "explain"', () => {
    expect(nextProbeTerm(terms, { b2: 'explain' })).toBe('d3');
    expect(nextProbeTerm(terms, { b2: 'explain', d3: 'explain' })).toBe('f4');
  });

  it('moves to the highest level left when there is no dependent', () => {
    expect(nextProbeTerm(terms, { b2: 'explain', d3: 'explain', f4: 'explain' })).toBe('e3');
  });

  it('steps down to a prereq after "new"', () => {
    expect(nextProbeTerm(terms, { b2: 'new' })).toBe('a1');
  });

  it('steps down a level after "new" when no prereq is left to ask', () => {
    expect(nextProbeTerm(terms, { b2: 'explain', d3: 'new' })).toBe('c2');
    expect(nextProbeTerm(terms, { b2: 'new', a1: 'new' })).toBe('g1');
  });

  it('stays on the same level after "heard"', () => {
    expect(nextProbeTerm(terms, { b2: 'heard' })).toBe('c2');
  });

  it('never asks about a term whose answer is already implied', () => {
    // b2 explained implies a1 is known; b2 new implies d3 and f4 are beyond.
    const asked = (answers: ProbeAnswers): string[] => {
      const next = nextProbeTerm(terms, answers);
      return next === null ? [] : [next, ...asked({ ...answers, [next]: 'heard' })];
    };
    expect(asked({ b2: 'explain' })).not.toContain('a1');
    expect(asked({ b2: 'new' })).toEqual(['a1', 'g1', 'c2', 'e3']);
  });

  it('stops after maxQuestions answers', () => {
    expect(DEFAULT_MAX_PROBE_QUESTIONS).toBe(9);
    expect(nextProbeTerm(terms, { b2: 'heard', c2: 'heard' }, 2)).toBeNull();
    expect(nextProbeTerm(terms, { b2: 'heard' }, 2)).toBe('c2');
    const many = Array.from({ length: 20 }, (_, i) => term(`t${i}`, 2));
    const nine: ProbeAnswers = Object.fromEntries(many.slice(0, 9).map((t) => [t.id, 'heard' as const]));
    expect(nextProbeTerm(many, nine)).toBeNull();
  });

  it('returns null when nothing is left to ask', () => {
    expect(nextProbeTerm([], {})).toBeNull();
    expect(nextProbeTerm([term('only', 2)], { only: 'heard' })).toBeNull();
    expect(nextProbeTerm(terms, { f4: 'explain', e3: 'explain', g1: 'heard' })).toBeNull();
  });

  it('starts over from the middle when the last answer is not in the glossary', () => {
    expect(nextProbeTerm(terms, { ghost: 'explain' })).toBe('b2');
  });

  it('is deterministic and does not mutate its inputs', () => {
    const answers: ProbeAnswers = { b2: 'explain' };
    expect(nextProbeTerm(terms, answers)).toBe(nextProbeTerm(terms, answers));
    expect(answers).toEqual({ b2: 'explain' });
  });
});

describe('answersToKnowledge', () => {
  it('maps explain, heard and new to known, learning and unknown', () => {
    expect(answersToKnowledge({ c2: 'explain', g1: 'heard', e3: 'new' })).toEqual({
      c2: 'known',
      g1: 'learning',
      e3: 'unknown',
    });
  });

  it('infers that every prereq of an explained term is known', () => {
    expect(answersToKnowledge({ f4: 'explain' }, terms)).toEqual({
      f4: 'known',
      d3: 'known',
      b2: 'known',
      a1: 'known',
    });
  });

  it('lets an explicit answer beat an inferred one', () => {
    expect(answersToKnowledge({ d3: 'explain', a1: 'new', b2: 'heard' }, terms)).toEqual({
      d3: 'known',
      a1: 'unknown',
      b2: 'learning',
    });
  });

  it('feeds classify', () => {
    const knowledge = answersToKnowledge({ b2: 'explain', c2: 'heard' }, terms);
    expect(classify(terms, knowledge)).toEqual({
      known: ['a1', 'b2'],
      frontier: ['c2', 'd3', 'g1'],
      beyond: ['e3', 'f4'],
    });
  });
});
