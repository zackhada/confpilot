// Typed calls to the ConfPilot API. Every call carries the session bearer (see auth.ts)
// and treats the response as untrusted until a guard has checked its shape.
import type {
  AskEvent,
  AskRequest,
  Knowledge,
  KnowledgePatch,
  KnowledgeStatus,
  ProbeRequest,
  ProbeResponse,
  Recap,
  SearchHit,
  SearchResponse,
} from '@contracts'
import { apiFetch } from './auth'

type Guard<T> = (value: unknown) => value is T

const isObject = (value: unknown): value is Record<string, unknown> =>
  typeof value === 'object' && value !== null
const isStringList = (value: unknown): value is string[] =>
  Array.isArray(value) && value.every((v) => typeof v === 'string')
const isStatus = (value: unknown): value is KnowledgeStatus =>
  value === 'known' || value === 'learning' || value === 'unknown'

export function isKnowledge(value: unknown): value is Knowledge {
  return isObject(value) && typeof value.term_id === 'string' && isStatus(value.status)
}

const isKnowledgeList: Guard<{ items: Knowledge[] }> = (value): value is { items: Knowledge[] } =>
  isObject(value) && Array.isArray(value.items) && value.items.every(isKnowledge)

export const isRecap: Guard<Recap> = (value): value is Recap =>
  isObject(value) &&
  typeof value.new_term_count === 'number' &&
  isStringList(value.learn_next) &&
  Array.isArray(value.heard) &&
  value.heard.every((h) => isObject(h) && typeof h.term_id === 'string' && typeof h.count === 'number')

const isHit = (value: unknown): value is SearchHit =>
  isObject(value) &&
  typeof value.utterance_id === 'string' &&
  typeof value.text === 'string' &&
  typeof value.highlight === 'string' &&
  isStringList(value.term_ids) &&
  typeof value.spoken_at === 'number' &&
  isObject(value.speaker) &&
  typeof value.speaker.name === 'string'

export const isSearchResponse: Guard<SearchResponse> = (value): value is SearchResponse =>
  isObject(value) && Array.isArray(value.hits) && value.hits.every(isHit)

export const isProbeResponse: Guard<ProbeResponse> = (value): value is ProbeResponse =>
  isObject(value) && isStringList(value.known_term_ids)

interface CallOptions {
  method?: 'GET' | 'PUT' | 'POST'
  body?: unknown
  timeoutMs?: number
}

/** Calls the API as `name` and returns the checked body. Throws on any failure. */
async function call<T>(name: string, path: string, guard: Guard<T>, options: CallOptions = {}): Promise<T> {
  const response = await apiFetch(path, name, {
    method: options.method ?? 'GET',
    headers: options.body === undefined ? undefined : { 'content-type': 'application/json' },
    body: options.body === undefined ? undefined : JSON.stringify(options.body),
    signal: options.timeoutMs ? AbortSignal.timeout(options.timeoutMs) : undefined,
  })
  if (!response.ok) throw new Error(`${path} failed (${response.status}).`)
  const body: unknown = await response.json()
  if (!guard(body)) throw new Error(`${path} returned an unexpected shape.`)
  return body
}

const user = (userId: string): string => `/api/users/${encodeURIComponent(userId)}/knowledge`

export async function fetchKnowledge(name: string, userId: string): Promise<Knowledge[]> {
  return (await call(name, user(userId), isKnowledgeList)).items
}

export function putKnowledge(name: string, userId: string, termId: string, patch: KnowledgePatch): Promise<Knowledge> {
  return call(name, `${user(userId)}/${encodeURIComponent(termId)}`, isKnowledge, { method: 'PUT', body: patch })
}

export function fetchRecap(name: string, room: string, userId: string): Promise<Recap> {
  const query = new URLSearchParams({ user_id: userId })
  return call(name, `/api/rooms/${encodeURIComponent(room)}/recap?${query}`, isRecap, { timeoutMs: 6000 })
}

export async function askRoom(
  name: string,
  body: AskRequest,
  onEvent: (event: AskEvent) => void,
  signal: AbortSignal,
): Promise<void> {
  const response = await apiFetch('/api/ask', name, {
    method: 'POST',
    headers: { 'content-type': 'application/json', accept: 'text/event-stream' },
    body: JSON.stringify(body),
    signal,
  })
  if (!response.ok || !response.body) throw new Error(`Ask failed (${response.status}).`)
  const reader = response.body.pipeThrough(new TextDecoderStream()).getReader()
  let pending = ''
  try {
    for (;;) {
      const { value, done } = await reader.read()
      if (done) throw new Error('Ask ended before an answer arrived.')
      const frames = (pending + value).split('\n\n')
      pending = frames.pop() ?? ''
      for (const frame of frames) {
        if (!frame.startsWith('data: ')) continue
        const data: unknown = JSON.parse(frame.slice(6))
        if (!isObject(data)) continue
        if (data.type === 'moments' && isSearchResponse(data)) {
          onEvent({ type: 'moments', hits: data.hits })
        } else if (data.type === 'answer' && (typeof data.answer === 'string' || data.answer === null)) {
          onEvent({ type: 'answer', answer: data.answer })
          return
        }
      }
    }
  } finally {
    await reader.cancel().catch(() => undefined)
    reader.releaseLock()
  }
}

/** The API allows the probe up to eight seconds. */
export function probe(name: string, userId: string, transcript: string): Promise<ProbeResponse> {
  const body: ProbeRequest = { user_id: userId, transcript }
  return call(name, '/api/probe', isProbeResponse, { method: 'POST', body, timeoutMs: 9000 })
}
