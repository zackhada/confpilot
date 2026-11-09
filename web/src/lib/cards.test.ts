import { describe, expect, it } from 'vitest';
import type { CardAction, CardStackState, LiveCard } from './cards';
import { MAX_FULL_CARDS, initialCardStack, reduceCards, shouldShowCard } from './cards';

const card = (termId: string, spokenAt = 1_000): LiveCard => ({
  card_id: `card-${termId}`,
  term_id: termId,
  tier: 1,
  utterance_id: 'utt-1',
  spoken_at: spokenAt,
  rendered_at: null,
});

const run = (actions: CardAction[], from: CardStackState = initialCardStack): CardStackState =>
  actions.reduce(reduceCards, from);

const addAll = (termIds: string[]): CardStackState =>
  run(termIds.map((id): CardAction => ({ type: 'add', card: card(id) })));

const termIds = (cards: LiveCard[]): string[] => cards.map((c) => c.term_id);

describe('reduceCards', () => {
  it('starts empty', () => {
    expect(initialCardStack).toEqual({ full: [], chips: [], shownTermIds: [] });
  });

  it('adds the newest card first', () => {
    const state = addAll(['pod', 'rag']);
    expect(termIds(state.full)).toEqual(['rag', 'pod']);
    expect(state.shownTermIds).toEqual(['pod', 'rag']);
  });

  it('keeps at most three full cards and collapses older ones into chips', () => {
    const state = addAll(['a', 'b', 'c', 'd', 'e']);
    expect(MAX_FULL_CARDS).toBe(3);
    expect(termIds(state.full)).toEqual(['e', 'd', 'c']);
    expect(termIds(state.chips)).toEqual(['b', 'a']);
  });

  it('shows a term at most once per session', () => {
    const once = addAll(['pod']);
    const again = reduceCards(once, { type: 'add', card: { ...card('pod'), card_id: 'card-pod-2' } });
    expect(again).toBe(once);
  });

  it('does not show a term again after its card was dismissed', () => {
    const dismissed = run([{ type: 'dismiss', card_id: 'card-pod' }], addAll(['pod']));
    expect(dismissed.full).toEqual([]);
    expect(dismissed.shownTermIds).toEqual(['pod']);
    expect(reduceCards(dismissed, { type: 'add', card: card('pod') })).toBe(dismissed);
  });

  it('ignores a duplicate card id', () => {
    const state = addAll(['pod']);
    expect(reduceCards(state, { type: 'add', card: { ...card('rag'), card_id: 'card-pod' } })).toBe(state);
  });

  it('records when a card was painted, and only the first time', () => {
    const state = run(
      [
        { type: 'rendered', card_id: 'card-pod', rendered_at: 1_312 },
        { type: 'rendered', card_id: 'card-pod', rendered_at: 9_999 },
      ],
      addAll(['pod', 'rag']),
    );
    expect(state.full.map((c) => c.rendered_at)).toEqual([null, 1_312]);
  });

  it('records a paint for a card that already collapsed into a chip', () => {
    const state = reduceCards(addAll(['a', 'b', 'c', 'd']), { type: 'rendered', card_id: 'card-a', rendered_at: 5 });
    expect(state.chips).toEqual([{ ...card('a'), rendered_at: 5 }]);
  });

  it('dismisses a full card or a chip without promoting chips', () => {
    const state = run(
      [
        { type: 'dismiss', card_id: 'card-d' },
        { type: 'dismiss', card_id: 'card-a' },
      ],
      addAll(['a', 'b', 'c', 'd', 'e']),
    );
    expect(termIds(state.full)).toEqual(['e', 'c']);
    expect(termIds(state.chips)).toEqual(['b']);
  });

  it('returns the same state for unknown card ids', () => {
    const state = addAll(['pod']);
    expect(reduceCards(state, { type: 'dismiss', card_id: 'nope' })).toBe(state);
    expect(reduceCards(state, { type: 'rendered', card_id: 'nope', rendered_at: 1 })).toBe(state);
  });

  it('resets to the empty stack', () => {
    expect(reduceCards(addAll(['a', 'b', 'c', 'd']), { type: 'reset' })).toEqual(initialCardStack);
  });

  it('never mutates the previous state', () => {
    const before = addAll(['a', 'b', 'c']);
    const snapshot = structuredClone(before);
    run(
      [
        { type: 'add', card: card('d') },
        { type: 'rendered', card_id: 'card-a', rendered_at: 7 },
        { type: 'dismiss', card_id: 'card-b' },
      ],
      before,
    );
    expect(before).toEqual(snapshot);
  });
});

describe('shouldShowCard', () => {
  it('shows unknown, learning and never-seen terms', () => {
    expect(shouldShowCard('pod', {}, [])).toBe(true);
    expect(shouldShowCard('pod', { pod: 'unknown' }, [])).toBe(true);
    expect(shouldShowCard('pod', { pod: 'learning' }, [])).toBe(true);
  });

  it('hides terms the user already knows', () => {
    expect(shouldShowCard('pod', { pod: 'known' }, [])).toBe(false);
  });

  it('hides terms already shown this session', () => {
    expect(shouldShowCard('pod', {}, ['rag', 'pod'])).toBe(false);
  });
});
