// The live card stack as a reducer: contracts/README.md section 2.
// A card renders the moment it is detected. Nothing is queued: the newest three cards are
// full size, older ones collapse into chips, and a term is shown at most once per session.

import type { CardTier, KnowledgeStatus } from '../../../contracts/types';

export interface LiveCard {
  card_id: string;
  term_id: string;
  tier: CardTier;
  utterance_id: string;
  /** Server-time ms when the matched word ended. */
  spoken_at: number;
  /** Server-time ms when the card was painted; null until then. */
  rendered_at: number | null;
}

export interface CardStackState {
  /** Full-size cards, newest first, at most MAX_FULL_CARDS. */
  full: LiveCard[];
  /** Collapsed cards, newest first. */
  chips: LiveCard[];
  /** Every term shown this session, in the order first shown. */
  shownTermIds: string[];
}

export type CardAction =
  | { type: 'add'; card: LiveCard }
  | { type: 'rendered'; card_id: string; rendered_at: number }
  | { type: 'dismiss'; card_id: string }
  | { type: 'reset' };

export const MAX_FULL_CARDS = 3;

export const initialCardStack: CardStackState = { full: [], chips: [], shownTermIds: [] };

const hasCard = (state: CardStackState, cardId: string): boolean =>
  [...state.full, ...state.chips].some((card) => card.card_id === cardId);

function addCard(state: CardStackState, card: LiveCard): CardStackState {
  if (state.shownTermIds.includes(card.term_id) || hasCard(state, card.card_id)) return state;
  const stacked = [card, ...state.full];
  return {
    full: stacked.slice(0, MAX_FULL_CARDS),
    chips: [...stacked.slice(MAX_FULL_CARDS), ...state.chips],
    shownTermIds: [...state.shownTermIds, card.term_id],
  };
}

function markRendered(state: CardStackState, cardId: string, renderedAt: number): CardStackState {
  const pending = (card: LiveCard): boolean => card.card_id === cardId && card.rendered_at === null;
  if (![...state.full, ...state.chips].some(pending)) return state;
  // The first paint is the honest one; later repaints must not change the latency.
  const mark = (card: LiveCard): LiveCard => (pending(card) ? { ...card, rendered_at: renderedAt } : card);
  return { ...state, full: state.full.map(mark), chips: state.chips.map(mark) };
}

function dismissCard(state: CardStackState, cardId: string): CardStackState {
  if (!hasCard(state, cardId)) return state;
  const keep = (card: LiveCard): boolean => card.card_id !== cardId;
  return { ...state, full: state.full.filter(keep), chips: state.chips.filter(keep) };
}

export function reduceCards(state: CardStackState, action: CardAction): CardStackState {
  switch (action.type) {
    case 'add':
      return addCard(state, action.card);
    case 'rendered':
      return markRendered(state, action.card_id, action.rendered_at);
    case 'dismiss':
      return dismissCard(state, action.card_id);
    case 'reset':
      return initialCardStack;
  }
}

/** A card is worth showing only for a term the user does not know and has not seen today. */
export function shouldShowCard(
  termId: string,
  knowledge: Record<string, KnowledgeStatus>,
  shownTermIds: string[],
): boolean {
  return knowledge[termId] !== 'known' && !shownTermIds.includes(termId);
}
