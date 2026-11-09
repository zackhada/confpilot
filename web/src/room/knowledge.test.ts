import type { Knowledge } from '@contracts'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { initialKnowledge } from '@/lib/sm2'
import { loadKnowledge } from './identity'
import {
  loadServerKnowledge,
  recordStatus,
  resetKnowledge,
  saveReview,
  setSeedKnowledge,
} from './knowledge'
import { INITIAL_ROOM_DATA, useRoom } from './store'

const me = { user_id: 'user-1', name: 'Clayton' }
const session = { user_id: 'user-1', session: 's1', expires_at: Date.now() + 3_600_000, name: 'Clayton' }
let puts: { path: string; body: unknown }[] = []
let serverItems: Knowledge[] = []

beforeEach(() => {
  puts = []
  serverItems = []
  window.localStorage.setItem('confpilot.session', JSON.stringify(session))
  useRoom.setState({ ...INITIAL_ROOM_DATA, me })
  resetKnowledge()
  vi.stubGlobal(
    'fetch',
    vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const path = String(input)
      if (init?.method === 'PUT') {
        const body: unknown = JSON.parse(String(init.body))
        puts.push({ path, body })
        const termId = path.split('/').pop() ?? ''
        return new Response(JSON.stringify({ ...initialKnowledge('user-1', termId), ...(body as object) }))
      }
      return new Response(JSON.stringify({ items: serverItems }))
    }),
  )
})
afterEach(() => vi.unstubAllGlobals())

describe('knowledge layers', () => {
  it('lets the server override the persona seed, and a tap on this phone override both', async () => {
    setSeedKnowledge({ rag: 'known', bm25: 'known', pod: 'known' })
    serverItems = [{ ...initialKnowledge('user-1', 'rag'), status: 'learning' }]
    await loadServerKnowledge(me, () => true)
    expect(useRoom.getState().knowledge).toMatchObject({ rag: 'learning', bm25: 'known' })
    recordStatus('bm25', 'unknown', 'tap')
    expect(useRoom.getState().knowledge.bm25).toBe('unknown')
    expect(useRoom.getState().records.rag?.status).toBe('learning')
  })

  it('keeps the seed when the API cannot be reached', async () => {
    setSeedKnowledge({ rag: 'known' })
    vi.stubGlobal('fetch', vi.fn(async () => new Response('{}', { status: 503 })))
    await loadServerKnowledge(me, () => true)
    expect(useRoom.getState().knowledge).toEqual({ rag: 'known' })
  })

  it('ignores a late answer for a room the person already left', async () => {
    serverItems = [{ ...initialKnowledge('user-1', 'rag'), status: 'known' }]
    await loadServerKnowledge(me, () => false)
    expect(useRoom.getState().knowledge).toEqual({})
  })
})

describe('recordStatus', () => {
  it('saves the tap on the phone and PUTs it to the API', async () => {
    recordStatus('rrf', 'known', 'tap')
    expect(loadKnowledge()).toEqual({ rrf: 'known' })
    await vi.waitFor(() => expect(puts).toHaveLength(1))
    expect(puts[0]).toEqual({ path: '/api/users/user-1/knowledge/rrf', body: { status: 'known', source: 'tap' } })
    await vi.waitFor(() => expect(useRoom.getState().records.rrf?.status).toBe('known'))
  })

  it('still works on the phone when the PUT fails', async () => {
    vi.stubGlobal('fetch', vi.fn(async () => new Response('{}', { status: 500 })))
    recordStatus('rrf', 'learning', 'probe')
    expect(useRoom.getState().knowledge.rrf).toBe('learning')
    expect(loadKnowledge()).toEqual({ rrf: 'learning' })
  })
})

describe('saveReview', () => {
  it('stores the full SM-2 record and sends its review fields', async () => {
    const record: Knowledge = { ...initialKnowledge('user-1', 'rag'), status: 'learning', interval_days: 1, reps: 1, due_at: 99 }
    saveReview(record)
    expect(useRoom.getState().records.rag).toEqual(record)
    await vi.waitFor(() => expect(puts).toHaveLength(1))
    expect(puts[0]?.body).toMatchObject({ status: 'learning', source: 'srs', interval_days: 1, reps: 1, due_at: 99 })
  })
})
