import { afterEach, describe, expect, it, vi } from 'vitest'
import { apiFetch, clearSession, ensureSession, STAGE_NAME, storedSession } from './auth'

function json(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), { status, headers: { 'content-type': 'application/json' } })
}

/** A fake API: issues numbered sessions and answers other routes with `respond`. */
function fakeApi(respond: (auth: string | null) => Response = () => json({ ok: true })) {
  let issued = 0
  const calls: { path: string; auth: string | null }[] = []
  const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
    const path = String(input)
    const auth = new Headers(init?.headers).get('authorization')
    calls.push({ path, auth })
    if (path === '/api/session') {
      issued += 1
      return json({ user_id: `user-${issued}`, session: `s${issued}`, expires_at: Date.now() + 3_600_000 })
    }
    return respond(auth)
  })
  vi.stubGlobal('fetch', fetchMock)
  return { calls, issued: () => issued }
}

afterEach(() => vi.unstubAllGlobals())

describe('ensureSession', () => {
  it('asks the server once, then reuses the stored session', async () => {
    const api = fakeApi()
    const first = await ensureSession('Clayton')
    const second = await ensureSession('Clayton')
    expect(first).toMatchObject({ user_id: 'user-1', session: 's1', name: 'Clayton' })
    expect(second.session).toBe('s1')
    expect(api.issued()).toBe(1)
    expect(storedSession('Clayton')?.user_id).toBe('user-1')
  })

  it('shares one request between callers that ask at the same moment', async () => {
    const api = fakeApi()
    const [a, b] = await Promise.all([ensureSession('Clayton'), ensureSession('Clayton')])
    expect(a.session).toBe(b.session)
    expect(api.issued()).toBe(1)
  })

  it('creates a new session when the name changes or the stored one was cleared', async () => {
    const api = fakeApi()
    await ensureSession('Clayton')
    expect((await ensureSession('Zack')).user_id).toBe('user-2')
    clearSession()
    expect((await ensureSession('Zack')).user_id).toBe('user-3')
    expect(api.issued()).toBe(3)
  })

  it('replaces a session that is about to expire', async () => {
    vi.useFakeTimers({ toFake: ['Date'] })
    fakeApi()
    await ensureSession('Clayton')
    vi.setSystemTime(Date.now() + 3_590_000)
    expect((await ensureSession('Clayton')).session).toBe('s2')
    vi.useRealTimers()
  })

  it('keeps the stage session apart from the phone session', async () => {
    fakeApi()
    await ensureSession('Clayton')
    await ensureSession(STAGE_NAME)
    expect(storedSession('Clayton')?.session).toBe('s1')
    expect(storedSession(STAGE_NAME)?.session).toBe('s2')
  })

  it('reports a failed session request', async () => {
    vi.stubGlobal('fetch', vi.fn(async () => json({}, 503)))
    await expect(ensureSession('Clayton')).rejects.toThrow(/Could not start a session \(503\)/)
  })
})

describe('apiFetch', () => {
  it('sends the session as a bearer token', async () => {
    const api = fakeApi()
    await apiFetch('/api/token', 'Clayton', { method: 'POST' })
    expect(api.calls[api.calls.length - 1]).toEqual({ path: '/api/token', auth: 'Bearer s1' })
  })

  it('creates a new session once after a 401 and retries', async () => {
    const api = fakeApi((auth) => (auth === 'Bearer s1' ? json({}, 401) : json({ ok: true })))
    const response = await apiFetch('/api/token', 'Clayton', { method: 'POST' })
    expect(response.status).toBe(200)
    expect(api.issued()).toBe(2)
  })

  it('gives up after the second 401 instead of looping', async () => {
    const api = fakeApi(() => json({}, 401))
    const response = await apiFetch('/api/token', 'Clayton', { method: 'POST' })
    expect(response.status).toBe(401)
    expect(api.issued()).toBe(2)
  })
})
