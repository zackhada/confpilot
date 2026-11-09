// Mock room server: `pnpm mock`. It stands in for the API on port 8000 so the phone app and
// the stage view can be built and demoed with no backend and no microphone.
//
//   GET  /api/health            -> Health
//   GET  /api/glossary          -> the sample glossary fixture (or content/glossary.json)
//   POST /api/token             -> 503, there is no speech-to-text in mock mode
//   POST /api/mock/replay?room= -> restart the scripted conversation
//   WS   /ws/rooms/{room}?user_id=&name=&role=
//
// Set MOCK_LOOP=1 to replay the conversation forever, and PORT to move off 8000.
import { existsSync } from 'node:fs'
import { readFile } from 'node:fs/promises'
import { createServer, type IncomingMessage, type ServerResponse } from 'node:http'
import { fileURLToPath } from 'node:url'
import { WebSocketServer } from 'ws'
import type { Health, Role } from '../../contracts/types.ts'
import { MockRoom } from './room.ts'

const PORT = Number(process.env.PORT ?? 8000)
const LOOP = process.env.MOCK_LOOP === '1'
const PING_INTERVAL_MS = 20_000
const ROOM_PATH = /^\/ws\/rooms\/([a-z0-9-]{1,32})$/i

const repoRoot = new URL('../../', import.meta.url)
const realGlossary = fileURLToPath(new URL('content/glossary.json', repoRoot))
const sampleGlossary = fileURLToPath(new URL('contracts/fixtures/glossary.sample.json', repoRoot))
const glossaryPath = process.env.GLOSSARY_PATH ?? (existsSync(realGlossary) ? realGlossary : sampleGlossary)

const rooms = new Map<string, MockRoom>()

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
  if (route === 'POST /api/token') {
    return sendJson(res, 503, { code: 'stt_unavailable', message: 'The mock server has no speech-to-text.' })
  }
  if (route === 'POST /api/mock/replay') {
    roomFor(url.searchParams.get('room') ?? 'demo').restartReplay()
    return sendJson(res, 202, { status: 'restarting' })
  }
  if (req.method === 'GET' && /^\/api\/users\/[^/]+\/knowledge$/.test(url.pathname)) {
    return sendJson(res, 200, { items: [] })
  }
  sendJson(res, 404, { code: 'not_found', message: `No mock route for ${route}.` })
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
  const userId = url.searchParams.get('user_id')
  if (!match?.[1] || !userId) {
    socket.write('HTTP/1.1 400 Bad Request\r\n\r\n')
    socket.destroy()
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

// The real API pings every 20 seconds so load balancers keep the socket open; so does the mock.
const pinger = setInterval(() => {
  for (const client of wss.clients) client.ping()
}, PING_INTERVAL_MS)

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
