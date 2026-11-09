import type { ClientEvent, ServerEvent } from '@contracts'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { backoffDelayMs, createRoomSocket, parseServerEvent, type SocketStatus } from './socket'

class FakeSocket {
  static instances: FakeSocket[] = []
  readyState: number = WebSocket.CONNECTING
  sent: string[] = []
  onopen: (() => void) | null = null
  onclose: (() => void) | null = null
  onerror: (() => void) | null = null
  onmessage: ((message: { data: unknown }) => void) | null = null

  readonly url: string

  constructor(url: string) {
    this.url = url
    FakeSocket.instances.push(this)
  }
  send(data: string): void {
    this.sent.push(data)
  }
  close(): void {
    this.readyState = WebSocket.CLOSED
    this.onclose?.()
  }
  open(): void {
    this.readyState = WebSocket.OPEN
    this.onopen?.()
  }
}

function setup() {
  const events: ServerEvent[] = []
  const statuses: SocketStatus[] = []
  const socket = createRoomSocket({
    url: 'ws://test/ws/rooms/slc1',
    onEvent: (event) => events.push(event),
    onStatus: (status) => statuses.push(status),
    createSocket: (url) => new FakeSocket(url) as unknown as WebSocket,
  })
  return { socket, events, statuses }
}

const latest = (): FakeSocket => FakeSocket.instances[FakeSocket.instances.length - 1]!

beforeEach(() => {
  FakeSocket.instances = []
  vi.useFakeTimers()
})
afterEach(() => vi.useRealTimers())

describe('parseServerEvent', () => {
  it('accepts a known event type', () => {
    expect(parseServerEvent('{"type":"time.pong","t0":1,"server_ts":2}')).toEqual({
      type: 'time.pong',
      t0: 1,
      server_ts: 2,
    })
  })

  it.each(['not json', '42', '{"type":"mystery"}', '{}'])('rejects %s', (raw) => {
    expect(parseServerEvent(raw)).toBeNull()
  })
})

describe('backoffDelayMs', () => {
  it('grows with each attempt and stops at five seconds', () => {
    expect(backoffDelayMs(0, () => 1)).toBe(400)
    expect(backoffDelayMs(2, () => 1)).toBe(1600)
    expect(backoffDelayMs(10, () => 1)).toBe(5000)
  })
})

describe('createRoomSocket', () => {
  it('delivers parsed events and drops malformed ones', () => {
    const { events } = setup()
    latest().open()
    latest().onmessage?.({ data: '{"type":"room.state","members":[]}' })
    latest().onmessage?.({ data: 'garbage' })
    expect(events).toEqual([{ type: 'room.state', members: [] }])
  })

  it('reconnects after the connection drops', () => {
    const { statuses } = setup()
    latest().open()
    latest().close()
    expect(statuses).toEqual(['connecting', 'open', 'reconnecting'])
    vi.advanceTimersByTime(5000)
    expect(FakeSocket.instances).toHaveLength(2)
    latest().open()
    expect(statuses[statuses.length - 1]).toBe('open')
  })

  it('queues card reports while offline, but drops stale interim transcripts', () => {
    const { socket } = setup()
    const interim: ClientEvent = { type: 'transcript', utterance_id: 'u', seq: 0, is_final: false, text: 'hi', words: [], started_at: 1 }
    expect(socket.send(interim)).toBe(false)
    expect(socket.send({ type: 'knowledge.set', term_id: 'rrf', status: 'known' })).toBe(true)
    latest().open()
    expect(latest().sent).toEqual(['{"type":"knowledge.set","term_id":"rrf","status":"known"}'])
  })

  it('stops reconnecting once closed on purpose', () => {
    const { socket, statuses } = setup()
    latest().open()
    socket.close()
    vi.advanceTimersByTime(10_000)
    expect(FakeSocket.instances).toHaveLength(1)
    expect(statuses[statuses.length - 1]).toBe('closed')
  })
})
