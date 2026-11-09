import type {
  CardShownEvent,
  KnowledgeStatus,
  Lang,
  Role,
  RoomState,
  ServerCardEvent,
  Speaker,
  Term,
  TranscriptEvent,
  Word,
} from '@contracts'
import { create } from 'zustand'
import {
  EMPTY_CARD_STACK,
  reduceCards,
  shouldShowCard,
  type CardStackState,
  type LiveCard,
} from '@/lib/cards'
import type { Match } from '@/lib/match/matcher'
import type { SocketStatus } from './socket'

export const MAX_UTTERANCES = 12
const MAX_LATENCIES = 500
const MAX_STAGE_CARDS = 12
const UNKNOWN_SPEAKER: Speaker = { user_id: 'unknown', name: 'Speaker' }

export interface Utterance {
  utterance_id: string
  speaker: Speaker
  words: Word[]
  matches: Match[]
  is_final: boolean
  seq: number
  started_at: number
}

export interface RoomData {
  status: 'idle' | SocketStatus
  room: string | null
  role: Role
  me: Speaker | null
  lang: Lang | null
  members: RoomState['members']
  terms: Record<string, Term>
  glossaryError: string | null
  knowledge: Record<string, KnowledgeStatus>
  saved: string[]
  /** How many times each term was heard this session. */
  heard: Record<string, number>
  /** `${utterance_id}:${term_id}` pairs already counted, so interims do not double count. */
  seenPairs: Record<string, true>
  shownTermIds: string[]
  utterances: Utterance[]
  stack: CardStackState
  latencies: number[]
  /** Stage view only: the cards each speaker's phone reported, newest first. */
  shownByUser: Record<string, CardShownEvent[]>
  notice: string | null
}

export const INITIAL_ROOM_DATA: RoomData = {
  status: 'idle',
  room: null,
  role: 'speaker',
  me: null,
  lang: null,
  members: [],
  terms: {},
  glossaryError: null,
  knowledge: {},
  saved: [],
  heard: {},
  seenPairs: {},
  shownTermIds: [],
  utterances: [],
  stack: EMPTY_CARD_STACK,
  latencies: [],
  shownByUser: {},
  notice: null,
}

/** Word list for a transcript; falls back to splitting the text when timings are missing. */
export function wordsOf(event: TranscriptEvent): Word[] {
  if (event.words.length > 0 || event.text.trim() === '') return event.words
  return event.text.trim().split(/\s+/).map((w) => ({ w, start_ms: 0, end_ms: 0 }))
}

function showCard(state: RoomData, card: LiveCard): Pick<RoomData, 'stack' | 'shownTermIds'> {
  return {
    stack: reduceCards(state.stack, { type: 'show', card }),
    shownTermIds: [...state.shownTermIds, card.term_id],
  }
}

/** Fold one interim or final transcript into the room: captions, heard counts and new cards. */
export function reduceTranscript(state: RoomData, event: TranscriptEvent, matches: Match[]): RoomData {
  const previous = state.utterances.find((u) => u.utterance_id === event.utterance_id)
  if (previous && (previous.is_final || event.seq <= previous.seq)) return state
  const words = wordsOf(event)
  const utterance: Utterance = {
    utterance_id: event.utterance_id,
    speaker: event.speaker ?? state.me ?? UNKNOWN_SPEAKER,
    words,
    matches,
    is_final: event.is_final,
    seq: event.seq,
    started_at: event.started_at,
  }
  const utterances = previous
    ? state.utterances.map((u) => (u.utterance_id === utterance.utterance_id ? utterance : u))
    : [...state.utterances, utterance].slice(-MAX_UTTERANCES)

  let next: RoomData = { ...state, utterances }
  for (const match of matches) {
    const pair = `${event.utterance_id}:${match.term_id}`
    if (next.seenPairs[pair]) continue
    next = {
      ...next,
      seenPairs: { ...next.seenPairs, [pair]: true },
      heard: { ...next.heard, [match.term_id]: (next.heard[match.term_id] ?? 0) + 1 },
    }
    if (next.role !== 'speaker') continue
    if (!shouldShowCard(match.term_id, next.knowledge, new Set(next.shownTermIds))) continue
    const card: LiveCard = {
      card_id: pair,
      term_id: match.term_id,
      tier: 1,
      utterance_id: event.utterance_id,
      spoken_at: event.started_at + (words[match.last_word]?.end_ms ?? 0),
      rendered_at: null,
      word_to_card_ms: null,
    }
    next = { ...next, ...showCard(next, card) }
  }
  return next
}

/** A tier 2 or 3 card from the server: a term the phone's own matcher could not have found. */
export function reduceServerCard(state: RoomData, event: ServerCardEvent): RoomData {
  const terms = state.terms[event.term.id] ? state.terms : { ...state.terms, [event.term.id]: event.term }
  const withTerm: RoomData = { ...state, terms }
  if (state.role !== 'speaker') return withTerm
  if (!shouldShowCard(event.term.id, state.knowledge, new Set(state.shownTermIds))) return withTerm
  const card: LiveCard = {
    card_id: `${event.utterance_id}:${event.term.id}`,
    term_id: event.term.id,
    tier: event.tier,
    utterance_id: event.utterance_id,
    spoken_at: event.spoken_at,
    rendered_at: null,
    word_to_card_ms: null,
  }
  return { ...withTerm, ...showCard(withTerm, card) }
}

export function reduceCardShown(state: RoomData, event: CardShownEvent): RoomData {
  const userId = event.user?.user_id ?? UNKNOWN_SPEAKER.user_id
  const existing = state.shownByUser[userId] ?? []
  if (existing.some((c) => c.card_id === event.card_id)) return state
  return {
    ...state,
    shownByUser: { ...state.shownByUser, [userId]: [event, ...existing].slice(0, MAX_STAGE_CARDS) },
    latencies: [...state.latencies, event.word_to_card_ms].slice(-MAX_LATENCIES),
  }
}

interface RoomActions {
  patch: (partial: Partial<RoomData>) => void
  reset: (partial: Partial<RoomData>) => void
  applyTranscript: (event: TranscriptEvent, matches: Match[]) => void
  applyServerCard: (event: ServerCardEvent) => void
  applyCardShown: (event: CardShownEvent) => void
  markPainted: (cardId: string, renderedAt: number, wordToCardMs: number) => void
  setKnowledge: (termId: string, status: KnowledgeStatus) => void
  toggleSaved: (termId: string) => boolean
}

export const useRoom = create<RoomData & RoomActions>((set, get) => ({
  ...INITIAL_ROOM_DATA,
  patch: (partial) => set(partial),
  reset: (partial) => set({ ...INITIAL_ROOM_DATA, ...partial }),
  applyTranscript: (event, matches) => set((s) => reduceTranscript(s, event, matches)),
  applyServerCard: (event) => set((s) => reduceServerCard(s, event)),
  applyCardShown: (event) => set((s) => reduceCardShown(s, event)),
  markPainted: (cardId, renderedAt, wordToCardMs) =>
    set((s) => ({
      stack: reduceCards(s.stack, {
        type: 'painted',
        card_id: cardId,
        rendered_at: renderedAt,
        word_to_card_ms: wordToCardMs,
      }),
      latencies: [...s.latencies, wordToCardMs].slice(-MAX_LATENCIES),
    })),
  setKnowledge: (termId, status) =>
    set((s) => ({
      knowledge: { ...s.knowledge, [termId]: status },
      stack: status === 'known' ? reduceCards(s.stack, { type: 'dismiss', term_id: termId }) : s.stack,
    })),
  toggleSaved: (termId) => {
    const wasSaved = get().saved.includes(termId)
    set((s) => ({
      saved: wasSaved ? s.saved.filter((id) => id !== termId) : [...s.saved, termId],
    }))
    return !wasSaved
  },
}))
