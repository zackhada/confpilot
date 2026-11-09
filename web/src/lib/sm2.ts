// SM-2 spaced repetition for flashcards. It runs on the phone and is saved through
// PUT /api/users/{id}/knowledge/{term_id}. A term counts as learned once its interval is 7+ days.

import type { Knowledge } from '../../../contracts/types';

export type Sm2Grade = 0 | 1 | 2 | 3 | 4 | 5;

export const DAY_MS = 86_400_000;
export const INITIAL_EASE = 2.5;
export const MIN_EASE = 1.3;
export const PASSING_GRADE = 3;
export const LEARNED_INTERVAL_DAYS = 7;

const FIRST_INTERVAL_DAYS = 1;
const SECOND_INTERVAL_DAYS = 6;

export function initialKnowledge(userId: string, termId: string): Knowledge {
  return {
    user_id: userId,
    term_id: termId,
    status: 'unknown',
    source: 'srs',
    encounters: 0,
    ease: INITIAL_EASE,
    interval_days: 0,
    reps: 0,
    due_at: null,
    learned: false,
  };
}

function nextEase(ease: number, grade: Sm2Grade): number {
  const miss = 5 - grade;
  const moved = ease + (0.1 - miss * (0.08 + miss * 0.02));
  return Math.max(MIN_EASE, Math.round(moved * 100) / 100);
}

function nextIntervalDays(k: Knowledge, grade: Sm2Grade): number {
  if (grade < PASSING_GRADE || k.reps === 0) return FIRST_INTERVAL_DAYS;
  if (k.reps === 1) return SECOND_INTERVAL_DAYS;
  return Math.max(FIRST_INTERVAL_DAYS, Math.round(k.interval_days * k.ease));
}

/** One flashcard review. `now` is epoch ms (server time); returns a new Knowledge record. */
export function review(k: Knowledge, grade: Sm2Grade, now: number): Knowledge {
  const passed = grade >= PASSING_GRADE;
  const intervalDays = nextIntervalDays(k, grade);
  const learned = intervalDays >= LEARNED_INTERVAL_DAYS;
  return {
    ...k,
    status: learned ? 'known' : 'learning',
    source: 'srs',
    ease: nextEase(k.ease, grade),
    interval_days: intervalDays,
    reps: passed ? k.reps + 1 : 0,
    due_at: now + intervalDays * DAY_MS,
    learned,
  };
}
