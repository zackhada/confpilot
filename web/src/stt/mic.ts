// Microphone to speech-to-text. Audio goes from the phone straight to Deepgram as 16 kHz
// 16-bit PCM and never touches our servers; the API only hands out a short-lived token.
import type { TokenRequest, TokenResponse, TranscriptEvent } from '@contracts'
import { create } from 'zustand'
import { apiFetch } from '@/room/auth'
import { publishTranscript, serverNow } from '@/room/session'
import { backoffDelayMs } from '@/room/socket'
import { useRoom } from '@/room/store'
import { createTranscriptAssembler, deepgramProtocols, type TranscriptAssembler } from './deepgram'
import { createDownsampler, TARGET_SAMPLE_RATE, type Downsampler } from './pcm'

export type MicState =
  | 'off'
  | 'starting'
  | 'listening'
  | 'reconnecting'
  | 'denied' // the person or the browser refused microphone access
  | 'unsupported' // no microphone API here (old browser, or not HTTPS)
  | 'unavailable' // the token endpoint or the speech service said no
  | 'error'

export const useMic = create<{ state: MicState }>(() => ({ state: 'off' }))

const WORKLET_URL = '/worklets/pcm-capture.js'
const MAX_RECONNECTS = 6

class SttUnavailableError extends Error {}

/** Where transcripts go. Live sends them to the room; the onboarding probe keeps them local. */
export type TranscriptSink = (event: TranscriptEvent) => void

interface MicSession {
  userId: string
  name: string
  sink: TranscriptSink
  context: AudioContext
  stream: MediaStream | null
  downsample: Downsampler | null
  socket: WebSocket | null
  assemble: TranscriptAssembler | null
  connectionNumber: number
  reconnects: number
  retryTimer: ReturnType<typeof setTimeout> | null
  wakeLock: WakeLockSentinel | null
  stopped: boolean
}

let session: MicSession | null = null

function setState(state: MicState): void {
  useMic.setState({ state })
}

function isTokenResponse(value: unknown): value is TokenResponse {
  if (typeof value !== 'object' || value === null) return false
  const v = value as Record<string, unknown>
  return typeof v.token === 'string' && typeof v.ws_url === 'string' && v.ws_url.startsWith('wss://')
}

/** The token lives about a minute and only has to be valid as the socket opens, so every
 * connection, including each reconnect, fetches a fresh one. */
async function fetchToken(userId: string, name: string): Promise<TokenResponse> {
  const body: TokenRequest = { user_id: userId }
  const response = await apiFetch('/api/token', name, {
    method: 'POST',
    headers: { 'content-type': 'application/json' },
    body: JSON.stringify(body),
  })
  if (!response.ok) throw new SttUnavailableError(`Token request failed (${response.status}).`)
  const token: unknown = await response.json()
  if (!isTokenResponse(token)) throw new SttUnavailableError('The token response had an unexpected shape.')
  return token
}

function onAudio(current: MicSession, samples: Float32Array): void {
  const { socket, downsample } = current
  if (!downsample || socket?.readyState !== WebSocket.OPEN) return
  if (!current.assemble) {
    // This is the first audio on this connection, so its start is the stream's time zero.
    const chunkMs = (samples.length / current.context.sampleRate) * 1000
    current.assemble = createTranscriptAssembler({
      idPrefix: `${current.userId.slice(0, 8)}-${Date.now().toString(36)}-${current.connectionNumber}`,
      streamStartedAt: serverNow() - chunkMs,
    })
  }
  socket.send(downsample(samples))
}

function onResult(current: MicSession, data: unknown): void {
  if (typeof data !== 'string' || !current.assemble) return
  try {
    const event = current.assemble(JSON.parse(data))
    if (event) current.sink(event)
  } catch {
    // A message that is not JSON is not a transcript; skip it.
  }
}

/** Open the speech-to-text socket. Resolves once it is open; rejects if it cannot open. */
async function connect(current: MicSession): Promise<void> {
  const token = await fetchToken(current.userId, current.name)
  if (current.stopped) return
  await new Promise<void>((resolve, reject) => {
    const socket = new WebSocket(token.ws_url, deepgramProtocols(token.token))
    socket.binaryType = 'arraybuffer'
    current.socket = socket
    current.assemble = null
    current.connectionNumber += 1
    let opened = false
    socket.onopen = () => {
      opened = true
      current.reconnects = 0
      setState('listening')
      resolve()
    }
    socket.onmessage = (message: MessageEvent) => onResult(current, message.data)
    socket.onclose = () => {
      if (current.socket !== socket) return
      current.socket = null
      // Never opened: the caller decides what to do. Dropped later: reconnect by ourselves.
      if (!opened) reject(new SttUnavailableError('The speech-to-text connection could not open.'))
      else if (!current.stopped) scheduleReconnect(current)
    }
  })
}

function scheduleReconnect(current: MicSession): void {
  if (current.reconnects >= MAX_RECONNECTS) {
    stopListening()
    setState('unavailable')
    return
  }
  setState('reconnecting')
  const delay = backoffDelayMs(current.reconnects)
  current.reconnects += 1
  current.retryTimer = setTimeout(() => {
    connect(current).catch(() => {
      if (!current.stopped) scheduleReconnect(current)
    })
  }, delay)
}

async function holdWakeLock(current: MicSession): Promise<void> {
  if (!('wakeLock' in navigator) || current.stopped || document.visibilityState !== 'visible') return
  try {
    current.wakeLock = await navigator.wakeLock.request('screen')
  } catch {
    // Low battery or a browser policy can refuse; listening still works, the screen may dim.
  }
}

function onVisible(): void {
  if (session && document.visibilityState === 'visible') void holdWakeLock(session)
}

async function wireAudio(current: MicSession, stream: MediaStream): Promise<void> {
  const { context } = current
  await context.audioWorklet.addModule(WORKLET_URL)
  await context.resume()
  current.downsample = createDownsampler(context.sampleRate, TARGET_SAMPLE_RATE)
  const capture = new AudioWorkletNode(context, 'pcm-capture')
  capture.port.onmessage = (message: MessageEvent<Float32Array>) => onAudio(current, message.data)
  // A silent path to the output keeps the graph running on Safari without playing the mic back.
  const silent = context.createGain()
  silent.gain.value = 0
  context.createMediaStreamSource(stream).connect(capture).connect(silent).connect(context.destination)
}

function micSupported(): boolean {
  return (
    window.isSecureContext &&
    typeof navigator.mediaDevices?.getUserMedia === 'function' &&
    typeof AudioWorkletNode === 'function'
  )
}

/** Call from a tap: browsers only start audio from a user gesture. */
export async function startListening(sink: TranscriptSink = publishTranscript): Promise<void> {
  if (session) return
  if (!micSupported()) return setState('unsupported')
  // No identity yet means the room is not connected, so there is nowhere to send captions.
  const me = useRoom.getState().me
  if (!me) return setState('unavailable')
  const current: MicSession = {
    userId: me.user_id,
    name: me.name,
    sink,
    context: new AudioContext(),
    stream: null,
    downsample: null,
    socket: null,
    assemble: null,
    connectionNumber: 0,
    reconnects: 0,
    retryTimer: null,
    wakeLock: null,
    stopped: false,
  }
  session = current
  setState('starting')
  try {
    current.stream = await navigator.mediaDevices.getUserMedia({
      audio: { channelCount: 1, echoCancellation: true, noiseSuppression: true, autoGainControl: true },
    })
  } catch (error) {
    if (current.stopped) return
    const refused = error instanceof DOMException && ['NotAllowedError', 'SecurityError'].includes(error.name)
    stopListening()
    return setState(refused ? 'denied' : 'error')
  }
  if (current.stopped) {
    current.stream.getTracks().forEach((track) => track.stop())
    return
  }
  try {
    await wireAudio(current, current.stream)
    await connect(current)
    if (current.stopped) return
    document.addEventListener('visibilitychange', onVisible)
    void holdWakeLock(current)
  } catch (error) {
    if (current.stopped) return
    stopListening()
    setState(error instanceof SttUnavailableError ? 'unavailable' : 'error')
  }
}

export function stopListening(): void {
  const current = session
  if (!current) return
  session = null
  current.stopped = true
  if (current.retryTimer) clearTimeout(current.retryTimer)
  document.removeEventListener('visibilitychange', onVisible)
  if (current.socket?.readyState === WebSocket.OPEN) {
    current.socket.send(JSON.stringify({ type: 'CloseStream' }))
  }
  current.socket?.close()
  current.stream?.getTracks().forEach((track) => track.stop())
  void current.context.close().catch(() => undefined)
  void current.wakeLock?.release().catch(() => undefined)
  setState('off')
}
