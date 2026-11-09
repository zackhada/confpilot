// In-memory room hub for the mock server. It follows contracts/README.md: transcripts are
// relayed to the rest of the room, card.shown goes to viewers, time.ping gets a time.pong.
import type { WebSocket } from 'ws'
import type {
  ClientEvent,
  Role,
  RoomState,
  ServerEvent,
  Speaker,
  TranscriptEvent,
} from '../../contracts/types.ts'
import type { Moment } from './api.ts'
import { buildTimeline, type ScriptSpeaker, type TimedUtterance } from './script.ts'

export interface Member extends Speaker {
  role: Role
}

const OPEN = 1
const REPLAY_START_DELAY_MS = 2500
const REPLAY_LOOP_PAUSE_MS = 8000

function send(socket: WebSocket, event: ServerEvent): void {
  if (socket.readyState === OPEN) socket.send(JSON.stringify(event))
}

function isClientEvent(value: unknown): value is ClientEvent {
  if (typeof value !== 'object' || value === null) return false
  const type = (value as { type?: unknown }).type
  return (
    type === 'transcript' || type === 'card.shown' || type === 'knowledge.set' || type === 'time.ping'
  )
}

export class MockRoom {
  readonly code: string
  private readonly loop: boolean
  private readonly members = new Map<WebSocket, Member>()
  private timers: NodeJS.Timeout[] = []
  private startTimer: NodeJS.Timeout | null = null
  private replayRun = 0
  /** Final sentences said in this room, for the mock search. */
  readonly moments: Moment[] = []
  /** How many phones were shown each term, for the mock recap. */
  readonly heard = new Map<string, number>()
  private readonly shown = new Map<string, string[]>()

  constructor(code: string, loop: boolean) {
    this.code = code
    this.loop = loop
  }

  get size(): number {
    return this.members.size
  }

  join(socket: WebSocket, member: Member): void {
    this.members.set(socket, member)
    this.broadcastState()
    // Restart the countdown on every join so two phones opened together both see line one.
    if (member.role === 'speaker' && this.timers.length === 0) this.scheduleReplay(REPLAY_START_DELAY_MS)
  }

  leave(socket: WebSocket): void {
    this.members.delete(socket)
    if (this.members.size === 0) this.stopReplay()
    else this.broadcastState()
  }

  handle(socket: WebSocket, raw: string): void {
    const member = this.members.get(socket)
    if (!member) return
    let event: unknown
    try {
      event = JSON.parse(raw)
    } catch {
      send(socket, { type: 'error', code: 'bad_json', message: 'The message was not valid JSON.' })
      return
    }
    if (!isClientEvent(event)) {
      send(socket, { type: 'error', code: 'bad_event', message: 'Unknown event type.' })
      return
    }
    switch (event.type) {
      case 'time.ping':
        send(socket, { type: 'time.pong', t0: event.t0, server_ts: Date.now() })
        return
      case 'transcript':
        this.remember({ ...event, speaker: { user_id: member.user_id, name: member.name } })
        this.relay(
          { ...event, speaker: { user_id: member.user_id, name: member.name } },
          (_other, otherSocket) => otherSocket !== socket,
        )
        return
      case 'card.shown':
        this.shown.set(member.user_id, [...this.shownTo(member.user_id), event.term_id])
        this.heard.set(event.term_id, (this.heard.get(event.term_id) ?? 0) + 1)
        this.relay(
          { ...event, user: { user_id: member.user_id, name: member.name } },
          (other) => other.role === 'viewer',
        )
        return
      case 'knowledge.set':
        return
    }
  }

  /** Term ids this user's phone reported through card.shown, oldest first. */
  shownTo(userId: string): string[] {
    return this.shown.get(userId) ?? []
  }

  private remember(event: TranscriptEvent): void {
    if (!event.is_final || !event.speaker) return
    this.moments.push({
      utterance_id: event.utterance_id,
      speaker: event.speaker,
      spoken_at: event.started_at,
      text: event.text,
    })
  }

  /** Resend room.state; clients treat 45 s of silence as a dead socket. */
  heartbeat(): void {
    this.broadcastState()
  }

  /** Start the scripted conversation again from the top. */
  restartReplay(): void {
    this.stopReplay()
    this.scheduleReplay(500)
  }

  stopReplay(): void {
    if (this.startTimer) clearTimeout(this.startTimer)
    this.startTimer = null
    this.timers.forEach(clearTimeout)
    this.timers = []
  }

  private relay(event: ServerEvent, to: (member: Member, socket: WebSocket) => boolean): void {
    for (const [socket, member] of this.members) {
      if (to(member, socket)) send(socket, event)
    }
  }

  private broadcastState(): void {
    const state: RoomState = { type: 'room.state', members: [...this.members.values()] }
    this.relay(state, () => true)
  }

  private scheduleReplay(delayMs: number): void {
    if (this.startTimer) clearTimeout(this.startTimer)
    this.startTimer = setTimeout(() => {
      this.startTimer = null
      this.startReplay()
    }, delayMs)
  }

  private startReplay(): void {
    const timeline = buildTimeline()
    const origin = Date.now()
    this.replayRun += 1
    const run = this.replayRun
    timeline.forEach((utterance, index) => this.scheduleUtterance(utterance, index, origin, run))
    const last = timeline[timeline.length - 1]
    const totalMs = last ? last.starts_at_ms + (last.frames[last.frames.length - 1]?.at_ms ?? 0) : 0
    this.timers.push(
      setTimeout(() => {
        this.timers = []
        if (this.loop && this.members.size > 0) this.scheduleReplay(REPLAY_LOOP_PAUSE_MS)
      }, totalMs + 50),
    )
  }

  private scheduleUtterance(utterance: TimedUtterance, index: number, origin: number, run: number): void {
    const startedAt = origin + utterance.starts_at_ms
    utterance.frames.forEach((frame, seq) => {
      const fire = () => {
        const words = utterance.words.slice(0, frame.word_count)
        const event: TranscriptEvent = {
          type: 'transcript',
          utterance_id: `mock-${run}-${index}`,
          seq,
          is_final: frame.is_final,
          text: words.map((w) => w.w).join(' '),
          words,
          started_at: startedAt,
          speaker: this.speakerFor(utterance.speaker),
        }
        // There is no microphone in mock mode, so the speaker's own phone gets its lines too.
        this.remember(event)
        this.relay(event, () => true)
      }
      this.timers.push(setTimeout(fire, Math.max(0, startedAt + frame.at_ms - Date.now())))
    })
  }

  /** Attribute a scripted line to a connected phone with the same name, if there is one. */
  private speakerFor(name: ScriptSpeaker): Speaker {
    for (const member of this.members.values()) {
      if (member.role === 'speaker' && member.name.trim().toLowerCase() === name.toLowerCase()) {
        return { user_id: member.user_id, name: member.name }
      }
    }
    return { user_id: `mock-${name.toLowerCase()}`, name }
  }
}
