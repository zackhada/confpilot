import type { AskEvent, AskRequest } from '@contracts'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { askRoom } from './api'

const session = {
  user_id: 'user-1',
  session: 's1',
  expires_at: Date.now() + 3_600_000,
  name: 'Clayton',
}

function eventStream(chunks: string[]): Response {
  const encoder = new TextEncoder()
  const body = new ReadableStream<Uint8Array>({
    start(controller) {
      for (const chunk of chunks) controller.enqueue(encoder.encode(chunk))
      controller.close()
    },
  })
  return new Response(body, { headers: { 'content-type': 'text/event-stream' } })
}

beforeEach(() => {
  window.localStorage.setItem('confpilot.session', JSON.stringify(session))
})
afterEach(() => vi.unstubAllGlobals())

describe('askRoom', () => {
  it('parses frames split across chunks and emits a null answer', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(async () =>
        eventStream([
          'data: {"type":"moments","hits":[]}\n',
          '\ndata: {"type":"answer","answer":null}\n\n',
        ]),
      ),
    )
    const events: AskEvent[] = []
    const request: AskRequest = { room: 'demo', question: 'What happened?' }

    await askRoom('Clayton', request, (event) => events.push(event), new AbortController().signal)

    expect(events).toEqual([
      { type: 'moments', hits: [] },
      { type: 'answer', answer: null },
    ])
  })

  it('rejects when the stream ends before an answer arrives', async () => {
    vi.stubGlobal('fetch', vi.fn(async () => eventStream(['data: {"type":"moments","hits":[]}\n\n'])))

    await expect(
      askRoom('Clayton', { room: 'demo', question: 'What happened?' }, vi.fn(), new AbortController().signal),
    ).rejects.toThrow('Ask ended before an answer arrived.')
  })

  it('rejects an unsuccessful response', async () => {
    vi.stubGlobal('fetch', vi.fn(async () => new Response(null, { status: 503 })))

    await expect(
      askRoom('Clayton', { room: 'demo', question: 'What happened?' }, vi.fn(), new AbortController().signal),
    ).rejects.toThrow('Ask failed (503).')
  })
})
