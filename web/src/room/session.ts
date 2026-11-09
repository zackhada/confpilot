// The live room session: one socket, one clock, one matcher. React components read the
// zustand store; they call the functions here to act on the room.
import type { Lang, Role, ServerEvent, Speaker, Term, TranscriptEvent } from '@contracts'
import { createClock } from '@/lib/clock'
import { wordToCardMs } from '@/lib/latency'
import { createMatcher, type Match } from '@/lib/match/matcher'
import { cachedGlossary, indexTerms, loadGlossary } from './glossary'
import { loadKnowledge, loadSaved, storeKnowledge, storeSaved } from './identity'
import { seedKnowledge, type Persona } from './personas'
import { createRoomSocket, type RoomSocket } from './socket'
import { allCards, useRoom, wordsOf } from './store'

const TIME_SYNC_INTERVAL_MS = 30_000

export interface JoinOptions {
  room: string
  role: Role
  me: Speaker
  lang?: Lang | null
  /** Seeds the terms this person already knows. Omitted for the stage view. */
  persona?: Persona
}

const clock = createClock()
let socket: RoomSocket | null = null
let matcher: (words: string[]) => Match[] = () => []
let syncTimer: ReturnType<typeof setInterval> | null = null
let joinToken = 0

/** The current time in server milliseconds. Every timestamp on the wire uses this. */
export function serverNow(): number {
  return clock.now()
}

function roomUrl({ room, role, me }: JoinOptions): string {
  const scheme = window.location.protocol === 'https:' ? 'wss' : 'ws'
  const query = new URLSearchParams({ user_id: me.user_id, name: me.name, role })
  return `${scheme}://${window.location.host}/ws/rooms/${encodeURIComponent(room)}?${query}`
}

function applyTerms(terms: readonly Term[], persona: Persona | undefined): void {
  matcher = createMatcher([...terms])
  const seeded = persona ? seedKnowledge(persona, terms) : {}
  // Taps made on this phone win over the persona's starting point.
  useRoom.getState().patch({
    terms: indexTerms(terms),
    knowledge: { ...seeded, ...loadKnowledge() },
    glossaryError: null,
  })
}

function sendPing(): void {
  socket?.send({ type: 'time.ping', t0: Date.now() })
}

function handleEvent(event: ServerEvent): void {
  const room = useRoom.getState()
  switch (event.type) {
    case 'transcript':
      room.applyTranscript(event, matcher(wordsOf(event).map((word) => word.w)))
      return
    case 'card':
      room.applyServerCard(event)
      return
    case 'card.shown':
      room.applyCardShown(event)
      return
    case 'time.pong':
      clock.sample(event.t0, Date.now(), event.server_ts)
      return
    case 'room.state':
      room.patch({ members: event.members })
      return
    case 'error':
      room.patch({ notice: event.message })
      return
  }
}

function wake(): void {
  if (document.visibilityState === 'visible') socket?.nudge()
}

export function joinRoom(options: JoinOptions): void {
  leaveRoom()
  joinToken += 1
  const token = joinToken
  useRoom.getState().reset({
    status: 'connecting',
    room: options.room,
    role: options.role,
    me: options.me,
    lang: options.lang ?? null,
    saved: options.role === 'speaker' ? loadSaved() : [],
  })

  // The copy saved on the phone makes the matcher ready before any network round trip.
  const cached = cachedGlossary()
  if (cached) applyTerms(cached.terms, options.persona)
  loadGlossary()
    .then((glossary) => {
      if (token === joinToken) applyTerms(glossary.terms, options.persona)
    })
    .catch((error: unknown) => {
      if (token !== joinToken) return
      const message = error instanceof Error ? error.message : 'The glossary could not be loaded.'
      useRoom.getState().patch({ glossaryError: message })
    })

  socket = createRoomSocket({
    url: roomUrl(options),
    onEvent: handleEvent,
    onStatus: (status) => {
      if (token !== joinToken) return
      useRoom.getState().patch({ status })
      if (status === 'open') sendPing()
    },
  })
  syncTimer = setInterval(sendPing, TIME_SYNC_INTERVAL_MS)
  document.addEventListener('visibilitychange', wake)
  window.addEventListener('online', wake)
}

export function leaveRoom(): void {
  joinToken += 1
  if (syncTimer) clearInterval(syncTimer)
  syncTimer = null
  socket?.close()
  socket = null
  document.removeEventListener('visibilitychange', wake)
  window.removeEventListener('online', wake)
}

/** Call right after a card's first paint. Stamps rendered_at and reports card.shown. */
export function cardPainted(cardId: string): void {
  const room = useRoom.getState()
  const card = allCards(room.stack).find((c) => c.card_id === cardId)
  if (!card || card.rendered_at !== null) return
  const renderedAt = clock.now()
  const ms = wordToCardMs(card.spoken_at, renderedAt)
  room.markPainted(cardId, renderedAt)
  socket?.send({
    type: 'card.shown',
    card_id: card.card_id,
    term_id: card.term_id,
    tier: card.tier,
    utterance_id: card.utterance_id,
    spoken_at: card.spoken_at,
    rendered_at: renderedAt,
    word_to_card_ms: ms,
  })
}

/** "I know this": the card leaves and the term never gets a card again. */
export function markKnown(termId: string): void {
  const room = useRoom.getState()
  room.setKnowledge(termId, 'known')
  storeKnowledge(useRoom.getState().knowledge)
  socket?.send({ type: 'knowledge.set', term_id: termId, status: 'known' })
}

/** "Save": keep the term for the flashcards. Tapping again removes it. */
export function toggleSave(termId: string): void {
  const room = useRoom.getState()
  const nowSaved = room.toggleSaved(termId)
  storeSaved(useRoom.getState().saved)
  if (!nowSaved) return
  room.setKnowledge(termId, 'learning')
  storeKnowledge(useRoom.getState().knowledge)
  socket?.send({ type: 'knowledge.set', term_id: termId, status: 'learning' })
}

/** Tapping a chip brings its card back into the stack. */
export function reopenCard(cardId: string): void {
  useRoom.getState().reopenCard(cardId)
}

/** A transcript from this phone's own microphone: show it here and relay it to the room. */
export function publishTranscript(event: TranscriptEvent): void {
  socket?.send(event)
  useRoom.getState().applyTranscript(event, matcher(wordsOf(event).map((word) => word.w)))
}
