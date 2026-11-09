import { describe, expect, it } from 'vitest';
import { p95, wordToCardMs } from './latency';

describe('wordToCardMs', () => {
  it('is rendered_at minus spoken_at', () => {
    expect(wordToCardMs(1_000, 1_312)).toBe(312);
  });

  it('rounds to whole milliseconds', () => {
    expect(wordToCardMs(1_000, 1_312.6)).toBe(313);
    expect(wordToCardMs(1_000.4, 1_312)).toBe(312);
  });

  it('clamps at zero when clocks disagree', () => {
    expect(wordToCardMs(2_000, 1_900)).toBe(0);
  });

  it('returns 0 for values that are not numbers', () => {
    expect(wordToCardMs(Number.NaN, 1_000)).toBe(0);
    expect(wordToCardMs(1_000, Number.POSITIVE_INFINITY)).toBe(0);
  });
});

describe('p95', () => {
  it('is 0 for an empty list', () => {
    expect(p95([])).toBe(0);
  });

  it('is the value itself for one sample', () => {
    expect(p95([420])).toBe(420);
  });

  it('uses the nearest-rank method', () => {
    const oneToHundred = Array.from({ length: 100 }, (_, i) => i + 1);
    expect(p95(oneToHundred)).toBe(95);
    expect(p95([100, 200, 300, 400, 500, 600, 700, 800, 900, 1_000])).toBe(1_000);
    expect(p95(Array.from({ length: 20 }, (_, i) => (i + 1) * 10))).toBe(190);
  });

  it('does not depend on input order and does not mutate the input', () => {
    const values = [900, 100, 500, 300, 700];
    expect(p95(values)).toBe(900);
    expect(values).toEqual([900, 100, 500, 300, 700]);
  });

  it('ignores values that are not finite numbers', () => {
    expect(p95([Number.NaN, 250, Number.POSITIVE_INFINITY])).toBe(250);
  });
});
