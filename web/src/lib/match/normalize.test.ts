import { describe, expect, it } from 'vitest';
import { normalizeWords } from './normalize';

const tokensOf = (text: string): string[] => normalizeWords(text.split(' ')).tokens;

describe('normalizeWords', () => {
  it('lowercases and strips punctuation', () => {
    expect(tokensOf('Can I get your LinkedIn?')).toEqual(['can', 'i', 'get', 'your', 'linkedin']);
  });

  it('keeps one origin pair per token', () => {
    const { tokens, origin } = normalizeWords(['It', 'uses', 'BM25']);
    expect(tokens).toEqual(['it', 'uses', 'bm25']);
    expect(origin).toEqual([[0, 0], [1, 1], [2, 2]]);
  });

  it('collapses punctuation inside a term', () => {
    expect(tokensOf('and R.R.F. to rank')).toEqual(['and', 'rrf', 'to', 'rank']);
  });

  it('joins spelled-out letters and tracks the words they came from', () => {
    const { tokens, origin } = normalizeWords(['and', 'r', 'r', 'f', 'to', 'rank']);
    expect(tokens).toEqual(['and', 'rrf', 'to', 'rank']);
    expect(origin).toEqual([[0, 0], [1, 3], [4, 4], [5, 5]]);
  });

  it('joins a short letter run with the number after it', () => {
    expect(tokensOf('it uses BM 25 for that')).toEqual(['it', 'uses', 'bm25', 'for', 'that']);
  });

  it('reads number words and joins them', () => {
    const { tokens, origin } = normalizeWords(['uses', 'bm', 'twenty', 'five', 'for']);
    expect(tokens).toEqual(['uses', 'bm25', 'for']);
    expect(origin).toEqual([[0, 0], [1, 3], [4, 4]]);
  });

  it('reads teens, tens and compound number words', () => {
    expect(tokensOf('p ninety nine')).toEqual(['p99']);
    expect(tokensOf('port eighty')).toEqual(['port', '80']);
    expect(tokensOf('thirteen nodes')).toEqual(['13', 'nodes']);
  });

  it('joins letter, number, letter runs such as k 8 s', () => {
    expect(tokensOf('a k eight s cluster')).toEqual(['a', 'k8s', 'cluster']);
  });

  it('splits hyphenated and slashed words, pointing both tokens at the same word', () => {
    const { tokens, origin } = normalizeWords(['retrieval-augmented', 'generation']);
    expect(tokens).toEqual(['retrieval', 'augmented', 'generation']);
    expect(origin).toEqual([[0, 0], [0, 0], [1, 1]]);
    expect(tokensOf('CI/CD')).toEqual(['ci', 'cd']);
  });

  it('does not glue ordinary words to numbers', () => {
    expect(tokensOf('pod 3 crashed')).toEqual(['pod', '3', 'crashed']);
    expect(tokensOf('this is a zero trust model')).toEqual(['this', 'is', 'a', '0', 'trust', 'model']);
    expect(tokensOf('we run it in 2 clusters')).toEqual(['we', 'run', 'it', 'in', '2', 'clusters']);
  });

  it('does not join two short words', () => {
    expect(tokensOf('the vm ip changed')).toEqual(['the', 'vm', 'ip', 'changed']);
  });

  it('drops words that are only punctuation', () => {
    const { tokens, origin } = normalizeWords(['pods', '--', 'crash']);
    expect(tokens).toEqual(['pods', 'crash']);
    expect(origin).toEqual([[0, 0], [2, 2]]);
  });

  it('handles empty input and does not mutate its argument', () => {
    expect(normalizeWords([])).toEqual({ tokens: [], origin: [] });
    const words = ['R', 'R', 'F'];
    normalizeWords(words);
    expect(words).toEqual(['R', 'R', 'F']);
  });

  it('is deterministic', () => {
    const words = 'expose the pod with a Kubernetes service'.split(' ');
    expect(normalizeWords(words)).toEqual(normalizeWords(words));
  });
});
