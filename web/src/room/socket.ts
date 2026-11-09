import type { ClientEvent, ServerEvent } from '@contracts'

export type SocketStatus = 'connecting' | 'open' | 'reconnecting' | 'closed'

export interface RoomSocket {
  /** Returns false when the event could not be sent or queued. */
  send(event: ClientEvent): boolean
  /** Reconnect now instead of waiting for the backoff timer (e.g. the phone woke up). */
  nudge(): void
  close(): void
}

export interface RoomSocketOptions {
  url: string
  onEvent: (event: ServerEvent) => void
  onStatus: (status: SocketStatus) => void
  createSocket?: (url: string) => WebSocket
}

const SERVER_EVENT_TYPES: ReadonlySet<string> = new Set([
  'transcript',
  'card',
  'card.shown',
  'time.pong',
  'room.state',
  'error',
])
const BASE_DELAY_MS = 400
const MAX_DELAY_MS = 5000
const MAX_QUEUE = 50
/** The server resends room.state every 20 s; this much silence means the socket is dead. */
export const STALE_AFTER_MS = 45_000
const WATCHDOG_INTERVAL_MS = 5000

/** Server data is untrusted until it is at least an object with a known `type`. */
export function parseServerEvent(raw: unknown): ServerEvent | null {
  if (typeof raw !== 'string') return null
  try {
    const value: unknown = JSON.parse(raw)
    if (typeof value !== 'object' || value === null) return null
    const type = (value as { type?: unknown }).type
    return typeof type === 'string' && SERVER_EVENT_TYPES.has(type) ? (value as ServerEvent) : null
  } catch {
    return null
  }
}

export function backoffDelayMs(attempt: number, random: () => number = Math.random): number {
  const ceiling = Math.min(MAX_DELAY_MS, BASE_DELAY_MS * 2 ** attempt)
  return Math.round(ceiling / 2 + (ceiling / 2) * random())
}

/**
 * One WebSocket per phone that reconnects by itself. Interim transcripts are dropped while
 * offline (they would be stale); everything else waits in a small queue.
 */
export function createRoomSocket(options: RoomSocketOptions): RoomSocket {
  const create = options.createSocket ?? ((url: string) => new WebSocket(url))
  let socket: WebSocket | null = null
  let attempt = 0
  let timer: ReturnType<typeof setTimeout> | null = null
  let closedByUs = false
  let queue: ClientEvent[] = []
  let lastHeardAt = Date.now()

  // A phone that changes network can keep a socket that looks open but carries nothing.
  const watchdog = setInterval(() => {
    const silentMs = Date.now() - lastHeardAt
    if (socket?.readyState === WebSocket.OPEN && silentMs > STALE_AFTER_MS) socket.close()
  }, WATCHDOG_INTERVAL_MS)

  const connect = (): void => {
    if (closedByUs) return
    options.onStatus(attempt === 0 ? 'connecting' : 'reconnecting')
    const next = create(options.url)
    socket = next
    next.onopen = () => {
      lastHeardAt = Date.now()
      attempt = 0
      options.onStatus('open')
      const pending = queue
      queue = []
      pending.forEach((event) => next.send(JSON.stringify(event)))
    }
    next.onmessage = (message: MessageEvent) => {
      lastHeardAt = Date.now()
      const event = parseServerEvent(message.data)
      if (event) options.onEvent(event)
    }
    next.onclose = () => {
      if (socket !== next) return
      socket = null
      if (closedByUs) return
      options.onStatus('reconnecting')
      timer = setTimeout(connect, backoffDelayMs(attempt))
      attempt += 1
    }
    next.onerror = () => next.close()
  }

  connect()

  return {
    send(event) {
      if (socket?.readyState === WebSocket.OPEN) {
        socket.send(JSON.stringify(event))
        return true
      }
      const isInterim = event.type === 'transcript' && !event.is_final
      if (closedByUs || isInterim || event.type === 'time.ping' || queue.length >= MAX_QUEUE) return false
      queue = [...queue, event]
      return true
    },
    nudge() {
      if (closedByUs || socket) return
      if (timer) clearTimeout(timer)
      connect()
    },
    close() {
      closedByUs = true
      clearInterval(watchdog)
      if (timer) clearTimeout(timer)
      socket?.close()
      socket = null
      options.onStatus('closed')
    },
  }
}
