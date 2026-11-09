// STUB written by the UI slice so the app compiles and runs. The pure-logic owner replaces
// this file. The brief fixed only the function names, so the state and action shapes below
// are this slice's assumption; src/room/store.ts is the only caller.
import type { CardTier, KnowledgeStatus } from '@contracts'

export const MAX_FULL_CARDS = 3
export const MAX_CHIPS = 12

export interface LiveCard {
  card_id: string
  term_id: string
  tier: CardTier
  utterance_id: string
  /** Server-time ms when the matched word ended. */
  spoken_at: number
  /** Server-time ms when the card was first painted; null until then. */
  rendered_at: number | null
  word_to_card_ms: number | null
}

export interface CardStackState {
  /** Newest first; at most MAX_FULL_CARDS. */
  full: LiveCard[]
  /** Cards that settled into chips, newest first. */
  chips: LiveCard[]
}

export type CardAction =
  | { type: 'show'; card: LiveCard }
  | { type: 'painted'; card_id: string; rendered_at: number; word_to_card_ms: number }
  | { type: 'dismiss'; term_id: string }
  | { type: 'reset' }

export const EMPTY_CARD_STACK: CardStackState = { full: [], chips: [] }

export function reduceCards(state: CardStackState, action: CardAction): CardStackState {
  switch (action.type) {
    case 'show': {
      const full = [action.card, ...state.full]
      const overflow = full.slice(MAX_FULL_CARDS)
      return {
        full: full.slice(0, MAX_FULL_CARDS),
        chips: [...overflow, ...state.chips].slice(0, MAX_CHIPS),
      }
    }
    case 'painted': {
      const stamp = (card: LiveCard): LiveCard =>
        card.card_id === action.card_id && card.rendered_at === null
          ? { ...card, rendered_at: action.rendered_at, word_to_card_ms: action.word_to_card_ms }
          : card
      return { full: state.full.map(stamp), chips: state.chips.map(stamp) }
    }
    case 'dismiss': {
      const keep = (card: LiveCard): boolean => card.term_id !== action.term_id
      return { full: state.full.filter(keep), chips: state.chips.filter(keep) }
    }
    case 'reset':
      return EMPTY_CARD_STACK
  }
}

/** A card is shown once per session, and never for a term the person already knows. */
export function shouldShowCard(
  termId: string,
  knowledge: Readonly<Record<string, KnowledgeStatus>>,
  shownTermIds: ReadonlySet<string>,
): boolean {
  return knowledge[termId] !== 'known' && !shownTermIds.has(termId)
}
