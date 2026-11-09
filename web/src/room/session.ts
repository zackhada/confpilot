// The live room session: one socket, one clock, one matcher. React components read the
// zustand store; they call the functions here to act on the room.
import type { Lang, Role, ServerEvent, Term, TranscriptEvent } from '@contracts'
import { createClock } from '@/lib/clock'
import { wordToCardMs } from '@/lib/latency'
import { createMatcher, type Match } from '@/lib/match/matcher'
import { ensureSession, sessionRejected, storedSession } from './auth'
import { cachedGlossary, indexTerms, loadGlossary } from './glossary'
import { loadSaved, storeSaved } from './identity'
import { loadServerKnowledge, recordStatus, resetKnowledge, setSeedKnowledge } from './knowledge'
import { seedKnowledge, type Persona } from './personas'
import { createRoomSocket, type RoomSocket, type SocketStatus } from './socket'
import { reportCardPainted } from '@/telemetry/dash0'
import { allCards, useRoom, wordsOf } from './store'

const TIME_SYNC_INTERVAL_MS = 30_000
const SESSION_RETRY_MS = 3000
/** After every this many failed connection attempts in a row, check the session over HTTP. */
const FAILURES_BEFORE_RENEW = 2

export interface JoinOptions {
  room: string
  role: Role
  /** Display name. The user id comes from the server-issued session. */
  name: string
  lang?: Lang | null
  /** Seeds the terms this person already knows. Omitted for the stage view. */
  persona?: Persona
}

const clock = createClock()
let socket: RoomSocket | null = null
let matcher: (words: string[]) => Match[] = () => []
let syncTimer: ReturnType<typeof setInterval> | null = null
let retryTimer: ReturnType<typeof setTimeout> | null = null
let joinToken = 0
let failures = 0
let renewed = false
let lastStatus: SocketStatus | null = null

/** The current time in server milliseconds. Every timestamp on the wire uses this. */
export function serverNow(): number {
  return clock.now()
}

function roomUrl(options: JoinOptions, session: string): string {
  const scheme = window.location.protocol === 'https:' ? 'wss' : 'ws'
  const query = new URLSearchParams({ session, name: options.name, role: options.role })
  return `${scheme}://${window.location.host}/ws/rooms/${encodeURIComponent(options.room)}?${query}`
}

function applyTerms(terms: readonly Term[], persona: Persona | undefined): void {
  matcher = createMatcher([...terms])
  useRoom.getState().patch({ terms: indexTerms(terms), glossaryError: null })
  setSeedKnowledge(persona ? seedKnowledge(persona, terms) : {})
}

function sendPing(): void {
  socket?.send({ type: 'time.ping', t0: Date.now() })
}

/** The server rejected the session: get a new one, once, and reconnect with it. */
function renewSession(options: JoinOptions, token: number): void {
  if (renewed || token !== joinToken) return
  renewed = true
  socket?.close()
  socket = null
  void openSocket(options, token, true)
}

function handleEvent(event: ServerEvent, options: JoinOptions, token: number): void {
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
      if (event.code === 'unauthorized') renewSession(options, token)
      else room.patch({ notice: event.message })
      return
  }
}

function handleStatus(status: SocketStatus, options: JoinOptions, token: number): void {
  if (token !== joinToken) return
  const repeated = status === lastStatus
  lastStatus = status
  useRoom.getState().patch({ status })
  if (status === 'open') {
    failures = 0
    renewed = false
    sendPing()
  }
  if (status === 'reconnecting' && !repeated) {
    // A browser cannot see a 401 on a WebSocket handshake. After repeated failures, ask the
    // API over HTTP; a plain network drop must not cost the phone its identity.
    failures += 1
    if (failures % FAILURES_BEFORE_RENEW !== 0) return
    void sessionRejected(options.name).then((rejected) => {
      if (rejected) renewSession(options, token)
    })
  }
}

async function openSocket(options: JoinOptions, token: number, fresh: boolean): Promise<void> {
  try {
    const session = await ensureSession(options.name, fresh)
    if (token !== joinToken) return
    const me = { user_id: session.user_id, name: options.name }
    useRoom.getState().patch({ me })
    if (options.role === 'speaker') void loadServerKnowledge(me, () => token === joinToken)
    socket = createRoomSocket({
      url: roomUrl(options, session.session),
      onEvent: (event) => handleEvent(event, options, token),
      onStatus: (status) => handleStatus(status, options, token),
    })
  } catch {
    if (token !== joinToken) return
    // No session means no network or no API yet; keep trying quietly.
    useRoom.getState().patch({ status: 'reconnecting' })
    retryTimer = setTimeout(() => void openSocket(options, token, fresh), SESSION_RETRY_MS)
  }
}

function wake(): void {
  if (document.visibilityState === 'visible') socket?.nudge()
}

function loadTerms(persona: Persona | undefined, token: number): void {
  // The copy saved on the phone makes the matcher ready before any network round trip.
  const cached = cachedGlossary()
  if (cached) applyTerms(cached.terms, persona)
  loadGlossary()
    .then((glossary) => {
      if (token === joinToken) applyTerms(glossary.terms, persona)
    })
    .catch((error: unknown) => {
      if (token !== joinToken) return
      const message = error instanceof Error ? error.message : 'The glossary could not be loaded.'
      useRoom.getState().patch({ glossaryError: message })
    })
}

export function joinRoom(options: JoinOptions): void {
  leaveRoom()
  joinToken += 1
  const token = joinToken
  failures = 0
  renewed = false
  lastStatus = null
  resetKnowledge()
  const known = storedSession(options.name)
  useRoom.getState().reset({
    status: 'connecting',
    room: options.room,
    role: options.role,
    me: known ? { user_id: known.user_id, name: options.name } : null,
    lang: options.lang ?? null,
    saved: options.role === 'speaker' ? loadSaved() : [],
  })
  loadTerms(options.persona, token)
  void openSocket(options, token, false)
  syncTimer = setInterval(sendPing, TIME_SYNC_INTERVAL_MS)
  document.addEventListener('visibilitychange', wake)
  window.addEventListener('online', wake)
}

export function leaveRoom(): void {
  joinToken += 1
  if (syncTimer) clearInterval(syncTimer)
  if (retryTimer) clearTimeout(retryTimer)
  syncTimer = null
  retryTimer = null
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
  reportCardPainted({ wordToCardMs: ms, tier: card.tier, room: room.room })
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
  recordStatus(termId, 'known', 'tap')
  socket?.send({ type: 'knowledge.set', term_id: termId, status: 'known' })
}

/** "Save": keep the term for the flashcards. Tapping again removes it. */
export function toggleSave(termId: string): void {
  const room = useRoom.getState()
  const nowSaved = room.toggleSaved(termId)
  storeSaved(useRoom.getState().saved)
  if (!nowSaved) return
  recordStatus(termId, 'learning', 'tap')
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
