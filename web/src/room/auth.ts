// Server-issued sessions. The phone asks the API who it is (POST /api/session) instead of
// inventing its own user id, then presents the session on every API call and on the room
// socket. A session is not a login: switching persona simply asks for a new one.
import { readStoredJson, removeStored, writeStored } from '@/shared/storage'

// TODO(contracts): these two shapes are not in contracts/types.ts yet. Import them from
// there, and delete these, as soon as the session contract lands.
export interface SessionRequest {
  name: string
}
export interface SessionResponse {
  user_id: string
  session: string
  expires_at: number // epoch milliseconds
}

interface StoredSession extends SessionResponse {
  name: string
}

const SESSION_KEY = 'confpilot.session'
/** The stage view joins under this name and keeps its own session, apart from a phone's. */
export const STAGE_NAME = 'Stage'

function keyFor(name: string): string {
  return name === STAGE_NAME ? `${SESSION_KEY}.stage` : SESSION_KEY
}
const EXPIRY_MARGIN_MS = 60_000

function isSessionResponse(value: unknown): value is SessionResponse {
  if (typeof value !== 'object' || value === null) return false
  const v = value as Record<string, unknown>
  return typeof v.user_id === 'string' && typeof v.session === 'string' && v.session.length > 0
}

function isStoredSession(value: unknown): value is StoredSession {
  return isSessionResponse(value) && typeof (value as { name?: unknown }).name === 'string'
}

/** `expires_at` may arrive as epoch ms, epoch seconds or an ISO string; normalise to ms. */
function expiryMs(raw: unknown): number {
  if (typeof raw === 'number') return raw < 1e12 ? raw * 1000 : raw
  const parsed = typeof raw === 'string' ? Date.parse(raw) : Number.NaN
  return Number.isFinite(parsed) ? parsed : Date.now() + 3_600_000
}

export function storedSession(name: string): StoredSession | null {
  const stored = readStoredJson(keyFor(name), isStoredSession)
  return stored?.name === name ? stored : null
}

/** Forget the phone's session (the stage keeps its own). */
export function clearSession(): void {
  removeStored(SESSION_KEY)
}

const pending = new Map<string, Promise<StoredSession>>()

async function createSession(name: string): Promise<StoredSession> {
  const body: SessionRequest = { name }
  const response = await fetch('/api/session', {
    method: 'POST',
    headers: { 'content-type': 'application/json' },
    body: JSON.stringify(body),
  })
  if (!response.ok) throw new Error(`Could not start a session (${response.status}).`)
  const data: unknown = await response.json()
  if (!isSessionResponse(data)) throw new Error('The session response had an unexpected shape.')
  const session: StoredSession = {
    user_id: data.user_id,
    session: data.session,
    expires_at: expiryMs((data as { expires_at?: unknown }).expires_at),
    name,
  }
  writeStored(keyFor(name), JSON.stringify(session))
  return session
}

/**
 * The current session for `name`, creating one when there is none, it belongs to another
 * name, or it is about to expire. Pass `fresh` after the server rejected the stored one.
 */
export function ensureSession(name: string, fresh = false): Promise<StoredSession> {
  const stored = storedSession(name)
  const usable = stored && stored.expires_at - EXPIRY_MARGIN_MS > Date.now()
  if (usable && !fresh) return Promise.resolve(stored)
  // Concurrent callers share one request, so a burst of 401s creates one session, not five.
  const inFlight = pending.get(name)
  if (inFlight) return inFlight
  const request = createSession(name).finally(() => pending.delete(name))
  pending.set(name, request)
  return request
}

/**
 * fetch for /api/* with the session attached. On a 401 it creates a new session once and
 * retries; a second 401 is returned to the caller.
 */
export async function apiFetch(path: string, name: string, init: RequestInit = {}): Promise<Response> {
  const attempt = async (fresh: boolean): Promise<Response> => {
    const session = await ensureSession(name, fresh)
    const headers = new Headers(init.headers)
    headers.set('authorization', `Bearer ${session.session}`)
    return fetch(path, { ...init, headers })
  }
  const first = await attempt(false)
  return first.status === 401 ? attempt(true) : first
}
