import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { applyDemoLink } from './demo'
import { loadKnowledge, loadProfile, loadSaved } from './identity'
import { loadServerKnowledge } from './knowledge'

let puts: string[] = []

function visit(search: string): void {
  window.history.replaceState(null, '', `/${search}`)
}

beforeEach(() => {
  puts = []
  window.localStorage.clear()
  vi.stubGlobal(
    'fetch',
    vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const path = String(input)
      if (path === '/api/session') {
        return Response.json({ user_id: 'priya-1', session: 's1', expires_at: Date.now() + 3_600_000 })
      }
      if (init?.method === 'PUT') {
        puts.push(path)
        const termId = path.split('/').pop() ?? ''
        return Response.json({ ...JSON.parse(String(init.body)), user_id: 'priya-1', term_id: termId })
      }
      return new Response('not found', { status: 404 })
    }),
  )
})

afterEach(() => {
  vi.unstubAllGlobals()
})

describe('applyDemoLink', () => {
  it('does nothing without a demo parameter', async () => {
    window.localStorage.setItem('confpilot.profile', JSON.stringify({ name: 'Zack', persona: 'zack', lang: null }))
    visit('?room=slc1')
    await applyDemoLink()
    expect(loadProfile()?.name).toBe('Zack')
    expect(puts).toHaveLength(0)
  })

  it('loads Priya with a known map, terms in progress, saved cards and review history', async () => {
    visit('?room=slc1&demo=returning')
    await applyDemoLink()
    expect(loadProfile()).toEqual({ name: 'Priya', persona: 'ana', lang: 'es' })
    const knowledge = loadKnowledge()
    expect(knowledge.kubernetes).toBe('known')
    expect(knowledge.slo).toBe('learning')
    expect(knowledge.bm25).toBeUndefined()
    expect(loadSaved()).toContain('rag')
    await vi.waitFor(() => {
      expect(puts.some((p) => p.endsWith('/api/users/priya-1/knowledge/kubernetes'))).toBe(true)
    })
    expect(window.location.search).toBe('?room=slc1')
  })

  it('waits for returning demo reviews before fetching server knowledge', async () => {
    const releaseWrites: Array<() => void> = []
    let knowledgeReads = 0
    vi.stubGlobal(
      'fetch',
      vi.fn((input: RequestInfo | URL, init?: RequestInit): Promise<Response> => {
        const path = String(input)
        if (path === '/api/session') {
          return Promise.resolve(Response.json({ user_id: 'priya-1', session: 's1', expires_at: Date.now() + 3_600_000 }))
        }
        if (init?.method === 'PUT') {
          return new Promise((resolve) => {
            releaseWrites.push(() => resolve(Response.json({})))
          })
        }
        knowledgeReads += 1
        return Promise.resolve(Response.json({ items: [] }))
      }),
    )
    visit('?room=slc1&demo=returning')
    await applyDemoLink()

    const loading = loadServerKnowledge({ user_id: 'priya-1', name: 'Priya' }, () => true)
    await vi.waitFor(() => expect(releaseWrites).toHaveLength(7))
    expect(knowledgeReads).toBe(0)
    releaseWrites.forEach((release) => release())
    await loading
    expect(knowledgeReads).toBe(1)
  })

  it('seeds Priya locally without waiting for server writes', async () => {
    vi.stubGlobal('fetch', vi.fn(() => new Promise<Response>(() => {})))
    visit('?room=slc1&demo=returning')
    await applyDemoLink()
    expect(loadProfile()).toEqual({ name: 'Priya', persona: 'ana', lang: 'es' })
    expect(loadKnowledge().kubernetes).toBe('known')
    expect(loadSaved()).toContain('rag')
  }, 1000)

  it('wipes the phone for a new person', async () => {
    window.localStorage.setItem('confpilot.profile', JSON.stringify({ name: 'Zack', persona: 'zack', lang: null }))
    window.localStorage.setItem('confpilot.knowledge', JSON.stringify({ rag: 'known' }))
    visit('?room=slc1&demo=new')
    await applyDemoLink()
    expect(loadProfile()).toBeNull()
    expect(loadKnowledge()).toEqual({})
    expect(window.location.search).toBe('?room=slc1')
  })
})
