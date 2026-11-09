import { describe, expect, it } from 'vitest';
import type { Knowledge } from '../../../contracts/types';
import { DAY_MS, initialKnowledge, review } from './sm2';

const NOW = 1_800_000_000_000;
type Grade = 0 | 1 | 2 | 3 | 4 | 5;

const reviewAll = (grades: Grade[], from: Knowledge = initialKnowledge('u1', 'rrf')): Knowledge =>
  grades.reduce((k, grade) => review(k, grade, NOW), from);

describe('initialKnowledge', () => {
  it('starts unknown with the SM-2 defaults', () => {
    expect(initialKnowledge('u1', 'rrf')).toEqual({
      user_id: 'u1',
      term_id: 'rrf',
      status: 'unknown',
      source: 'srs',
      encounters: 0,
      ease: 2.5,
      interval_days: 0,
      reps: 0,
      due_at: null,
      learned: false,
    });
  });
});

describe('review', () => {
  it('schedules the first pass one day out', () => {
    const k = reviewAll([4]);
    expect(k).toMatchObject({ reps: 1, interval_days: 1, ease: 2.5, status: 'learning', learned: false, source: 'srs' });
    expect(k.due_at).toBe(NOW + DAY_MS);
  });

  it('schedules the second pass six days out, which is not yet learned', () => {
    const k = reviewAll([4, 4]);
    expect(k).toMatchObject({ reps: 2, interval_days: 6, status: 'learning', learned: false });
    expect(k.due_at).toBe(NOW + 6 * DAY_MS);
  });

  it('multiplies the interval by ease from the third pass and marks the term learned', () => {
    const k = reviewAll([4, 4, 4]);
    expect(k).toMatchObject({ reps: 3, interval_days: 15, status: 'known', learned: true });
    expect(reviewAll([4, 4, 4, 4]).interval_days).toBe(38);
  });

  it('moves ease by the SM-2 formula', () => {
    expect(reviewAll([5]).ease).toBeCloseTo(2.6, 5);
    expect(reviewAll([4]).ease).toBeCloseTo(2.5, 5);
    expect(reviewAll([3]).ease).toBeCloseTo(2.36, 5);
    expect(reviewAll([0]).ease).toBeCloseTo(1.7, 5);
  });

  it('never lets ease fall below 1.3', () => {
    expect(reviewAll([0, 0, 0, 0]).ease).toBe(1.3);
  });

  it('resets reps and interval to one day on a grade below 3', () => {
    const k = reviewAll([4, 4, 4, 2]);
    expect(k).toMatchObject({ reps: 0, interval_days: 1, status: 'learning', learned: false });
    expect(k.due_at).toBe(NOW + DAY_MS);
  });

  it('counts a term as learned exactly when the interval reaches 7 days', () => {
    const base = initialKnowledge('u1', 'rrf');
    expect(review({ ...base, reps: 2, interval_days: 5, ease: 1.3 }, 3, NOW).interval_days).toBe(7);
    expect(review({ ...base, reps: 2, interval_days: 5, ease: 1.3 }, 3, NOW).learned).toBe(true);
    expect(review({ ...base, reps: 2, interval_days: 4, ease: 1.3 }, 3, NOW).learned).toBe(false);
  });

  it('keeps identity fields and encounters, and does not mutate its input', () => {
    const before: Knowledge = { ...initialKnowledge('u1', 'rrf'), encounters: 4, source: 'probe' };
    const snapshot = { ...before };
    const after = review(before, 5, NOW);
    expect(before).toEqual(snapshot);
    expect(after).not.toBe(before);
    expect(after).toMatchObject({ user_id: 'u1', term_id: 'rrf', encounters: 4, source: 'srs' });
  });
});
