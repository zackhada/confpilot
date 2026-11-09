// Mock room server: `pnpm mock`. It stands in for the API on port 8000 so the phone app and
// the stage view can be built and demoed with no backend and no microphone.
//
//   GET  /api/health            -> Health
//   GET  /api/glossary          -> the sample glossary fixture (or content/glossary.json)
//   POST /api/session           -> { user_id, session, expires_at }, any opaque string
//   POST /api/token             -> 503, there is no speech-to-text in mock mode
//   POST /api/mock/replay?room= -> restart the scripted conversation
//   WS   /ws/rooms/{room}?session=&name=&role=
//
// Set MOCK_LOOP=1 to replay the conversation forever, and PORT to move off 8000.
import { randomUUID } from 'node:crypto'
import { existsSync } from 'node:fs'
import { readFile } from 'node:fs/promises'
import { createServer, type IncomingMessage, type ServerResponse } from 'node:http'
import { fileURLToPath } from 'node:url'
import { WebSocketServer } from 'ws'
import type { Health, KnowledgePatch, Role, Term } from '../../contracts/types.ts'
import { KnowledgeStore, probeFor, recapFor, searchMoments } from './api.ts'
import { MockRoom } from './room.ts'

const PORT = Number(process.env.PORT ?? 8000)
const LOOP = process.env.MOCK_LOOP === '1'
const HEARTBEAT_INTERVAL_MS = 20_000
const SESSION_TTL_MS = 12 * 60 * 60 * 1000
const ROOM_PATH = /^\/ws\/rooms\/([a-z0-9-]{1,32})$/i

const repoRoot = new URL('../../', import.meta.url)
const realGlossary = fileURLToPath(new URL('content/glossary.json', repoRoot))
const sampleGlossary = fileURLToPath(new URL('contracts/fixtures/glossary.sample.json', repoRoot))
const glossaryPath = process.env.GLOSSARY_PATH ?? (existsSync(realGlossary) ? realGlossary : sampleGlossary)

const rooms = new Map<string, MockRoom>()
/** session string -> user id. Lost on restart, which exercises the client's renew path. */
const sessions = new Map<string, string>()
const knowledge = new KnowledgeStore()
const PROBE_DELAY_MS = 1200

function roomFor(code: string): MockRoom {
  const key = code.toLowerCase()
  const existing = rooms.get(key)
  if (existing) return existing
  const room = new MockRoom(key, LOOP)
  rooms.set(key, room)
  return room
}

function sendJson(res: ServerResponse, status: number, body: unknown): void {
  res.writeHead(status, { 'content-type': 'application/json', 'cache-control': 'no-store' })
  res.end(JSON.stringify(body))
}

async function handleHttp(req: IncomingMessage, res: ServerResponse): Promise<void> {
  const url = new URL(req.url ?? '/', `http://${req.headers.host ?? 'localhost'}`)
  const route = `${req.method ?? 'GET'} ${url.pathname}`
  if (route === 'GET /api/health') {
    const health: Health = { status: 'ok', version: 'mock' }
    return sendJson(res, 200, health)
  }
  if (route === 'GET /api/glossary') {
    const body = await readFile(glossaryPath, 'utf8')
    res.writeHead(200, { 'content-type': 'application/json' })
    res.end(body)
    return
  }
  if (route === 'POST /api/session') {
    const userId = randomUUID()
    const session = `mock-${randomUUID()}`
    sessions.set(session, userId)
    return sendJson(res, 200, { user_id: userId, session, expires_at: Date.now() + SESSION_TTL_MS })
  }
  if (route === 'POST /api/token') {
    return sendJson(res, 503, { code: 'stt_unavailable', message: 'The mock server has no speech-to-text.' })
  }
  if (route === 'POST /api/mock/replay') {
    roomFor(url.searchParams.get('room') ?? 'demo').restartReplay()
    return sendJson(res, 202, { status: 'restarting' })
  }
  return handleData(req, res, url, route)
}

async function readBody(req: IncomingMessage): Promise<Record<string, unknown>> {
  let raw = ''
  for await (const chunk of req) raw += String(chunk)
  try {
    const parsed: unknown = JSON.parse(raw || '{}')
    return typeof parsed === 'object' && parsed !== null ? (parsed as Record<string, unknown>) : {}
  } catch {
    return {}
  }
}

/** Knowledge, recap, search and probe. All of them need a session the mock issued. */
async function handleData(req: IncomingMessage, res: ServerResponse, url: URL, route: string): Promise<void> {
  const bearer = (req.headers.authorization ?? '').replace(/^Bearer /, '')
  const userId = sessions.get(bearer)
  if (!userId) return sendJson(res, 401, { code: 'unauthorized', message: 'Unknown session.' })

  const knowledgePath = /^\/api\/users\/[^/]+\/knowledge(?:\/([^/]+))?$/.exec(url.pathname)
  if (knowledgePath && req.method === 'GET') return sendJson(res, 200, { items: knowledge.list(userId) })
  if (knowledgePath?.[1] && req.method === 'PUT') {
    const patch = (await readBody(req)) as KnowledgePatch
    return sendJson(res, 200, knowledge.put(userId, decodeURIComponent(knowledgePath[1]), patch))
  }
  const recapPath = /^\/api\/rooms\/([^/]+)\/recap$/.exec(url.pathname)
  if (recapPath?.[1] && req.method === 'GET') {
    const room = roomFor(recapPath[1])
    return sendJson(res, 200, recapFor(room.code, room.shownTo(userId), room.heard))
  }
  if (route === 'GET /api/search') {
    const room = roomFor(url.searchParams.get('room') ?? 'demo')
    const limit = Number(url.searchParams.get('limit') ?? 8)
    const hits = searchMoments(url.searchParams.get('q') ?? '', room.moments, await glossaryTerms(), limit)
    return sendJson(res, 200, { hits })
  }
  if (route === 'POST /api/probe') {
    const body = await readBody(req)
    // The real endpoint waits on an LLM; a short pause lets the progress state be seen.
    await new Promise((resolve) => setTimeout(resolve, PROBE_DELAY_MS))
    return sendJson(res, 200, probeFor(String(body.transcript ?? ''), await glossaryTerms()))
  }
  sendJson(res, 404, { code: 'not_found', message: `No mock route for ${route}.` })
}

let cachedTerms: Term[] | null = null
async function glossaryTerms(): Promise<Term[]> {
  if (cachedTerms) return cachedTerms
  const parsed = JSON.parse(await readFile(glossaryPath, 'utf8')) as { terms: Term[] }
  cachedTerms = parsed.terms
  return cachedTerms
}

const server = createServer((req, res) => {
  handleHttp(req, res).catch((error: unknown) => {
    const message = error instanceof Error ? error.message : 'Unexpected error'
    sendJson(res, 500, { code: 'mock_error', message })
  })
})

const wss = new WebSocketServer({ noServer: true })

server.on('upgrade', (req, socket, head) => {
  const url = new URL(req.url ?? '/', `http://${req.headers.host ?? 'localhost'}`)
  const match = ROOM_PATH.exec(url.pathname)
  if (!match?.[1]) {
    socket.write('HTTP/1.1 400 Bad Request\r\n\r\n')
    socket.destroy()
    return
  }
  const userId = sessions.get(url.searchParams.get('session') ?? '')
  if (!userId) {
    // Accept, explain, close: a browser cannot read a 401 on the handshake itself.
    wss.handleUpgrade(req, socket, head, (ws) => {
      ws.send(JSON.stringify({ type: 'error', code: 'unauthorized', message: 'Unknown session.' }))
      ws.close(4401, 'unauthorized')
    })
    return
  }
  const room = roomFor(match[1])
  const role: Role = url.searchParams.get('role') === 'viewer' ? 'viewer' : 'speaker'
  const name = (url.searchParams.get('name') ?? 'Guest').slice(0, 40)
  wss.handleUpgrade(req, socket, head, (ws) => {
    room.join(ws, { user_id: userId, name, role })
    ws.on('message', (data) => room.handle(ws, data.toString()))
    ws.on('close', () => {
      room.leave(ws)
      if (room.size === 0) rooms.delete(room.code)
    })
    ws.on('error', () => ws.terminate())
  })
})

// The real API resends room.state every 20 seconds as its heartbeat; so does the mock.
const pinger = setInterval(() => {
  rooms.forEach((room) => room.heartbeat())
}, HEARTBEAT_INTERVAL_MS)

server.listen(PORT, () => {
  process.stdout.write(`ConfPilot mock room server on http://localhost:${PORT} (glossary: ${glossaryPath})\n`)
})

function shutdown(): void {
  clearInterval(pinger)
  rooms.forEach((room) => room.stopReplay())
  wss.close()
  server.close(() => process.exit(0))
}

process.on('SIGINT', shutdown)
process.on('SIGTERM', shutdown)
