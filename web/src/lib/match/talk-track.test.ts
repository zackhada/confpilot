// The on-device matcher against the real glossary and the demo conversation.
import { describe, expect, it } from 'vitest';
import type { Glossary } from '../../../../contracts/types';
import glossaryJson from '../../../../content/glossary.json';
import talkTrack from '../../../../content/stt-fixtures/talk_track.txt?raw';
import { createMatcher } from './matcher';

const MUST_CATCH = ['sre', 'rag', 'embedding', 'bm25', 'rrf'];

const glossary = glossaryJson as unknown as Glossary;
const match = createMatcher(glossary.terms);
const wordsOf = (text: string): string[] => text.trim().split(/\s+/);
const idsIn = (text: string): string[] => match(wordsOf(text)).map((m) => m.term_id);
const sentences = talkTrack.trim().split(/(?<=[.?!])\s+/);

describe('matcher on content/glossary.json and the demo talk track', () => {
  it('loads the 200-term glossary, including terms with no pronunciation hint', () => {
    expect(glossary.terms).toHaveLength(200);
    expect(glossary.terms.some((t) => t.say === null)).toBe(true);
    expect(sentences.length).toBeGreaterThan(5);
  });

  it('catches every must-catch term, sentence by sentence', () => {
    const found = new Set(sentences.flatMap(idsIn));
    expect(MUST_CATCH.filter((id) => !found.has(id))).toEqual([]);
  });

  it('catches every must-catch term when the whole talk is one utterance', () => {
    const found = new Set(idsIn(talkTrack));
    expect(MUST_CATCH.filter((id) => !found.has(id))).toEqual([]);
  });

  it('does not read "search service" as a Kubernetes Service', () => {
    expect(talkTrack).toContain('search service');
    expect(sentences.flatMap(idsIn)).not.toContain('k8s-service');
    expect(idsIn(talkTrack)).not.toContain('k8s-service');
    expect(idsIn('we have some internal search service use cases')).not.toContain('k8s-service');
  });

  it('still finds a Kubernetes Service next to cloud terms', () => {
    expect(idsIn('expose it with a Kubernetes service')).toEqual(['kubernetes', 'k8s-service']);
  });

  it('finds the agent beside the knowledge base, but not on its own', () => {
    expect(idsIn('into a knowledge base the agent can pull from')).toEqual(['knowledge-base', 'ai-agent']);
    expect(idsIn('my travel agent booked the flights')).toEqual([]);
  });

  it('matches 30 words of the talk against the real glossary in well under 1 ms', () => {
    const utterance = wordsOf(talkTrack).slice(0, 30);
    expect(utterance).toHaveLength(30);
    for (let i = 0; i < 200; i += 1) match(utterance);

    const runs = 2000;
    const started = performance.now();
    for (let i = 0; i < runs; i += 1) match(utterance);
    const perCallMs = (performance.now() - started) / runs;

    expect(match(utterance).map((m) => m.term_id)).toContain('sre');
    expect(perCallMs).toBeLessThan(0.5);
  });
});
