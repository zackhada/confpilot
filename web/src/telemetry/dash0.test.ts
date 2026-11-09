import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

const { init, sendEvent } = vi.hoisted(() => ({ init: vi.fn(), sendEvent: vi.fn() }))
vi.mock('@dash0/sdk-web', () => ({ init, sendEvent }))

const { CARD_PAINTED_EVENT, initTelemetry, reportCardPainted, resetTelemetry } = await import('./dash0')

beforeEach(() => {
  init.mockReset()
  sendEvent.mockReset()
  resetTelemetry()
})
afterEach(() => vi.unstubAllEnvs())

describe('Dash0 browser monitoring', () => {
  it('stays off, and sends nothing, when it is not configured', async () => {
    vi.stubEnv('VITE_DASH0_RUM_TOKEN', '')
    vi.stubEnv('VITE_DASH0_RUM_ENDPOINT', '')
    expect(await initTelemetry()).toBe(false)
    reportCardPainted({ wordToCardMs: 312, tier: 1, room: 'slc1' })
    expect(init).not.toHaveBeenCalled()
    expect(sendEvent).not.toHaveBeenCalled()
  })

  it('needs both the token and the endpoint', async () => {
    vi.stubEnv('VITE_DASH0_RUM_TOKEN', 'browser-token')
    vi.stubEnv('VITE_DASH0_RUM_ENDPOINT', '')
    expect(await initTelemetry()).toBe(false)
  })

  it('initialises the SDK from the environment', async () => {
    vi.stubEnv('VITE_DASH0_RUM_TOKEN', 'browser-token')
    vi.stubEnv('VITE_DASH0_RUM_ENDPOINT', 'https://ingress.example/otlp')
    expect(await initTelemetry()).toBe(true)
    expect(init).toHaveBeenCalledWith({
      serviceName: 'confpilot-web',
      endpoint: { url: 'https://ingress.example/otlp', authToken: 'browser-token' },
    })
  })

  it('sends one event per painted card with the latency, tier and room', async () => {
    vi.stubEnv('VITE_DASH0_RUM_TOKEN', 'browser-token')
    vi.stubEnv('VITE_DASH0_RUM_ENDPOINT', 'https://ingress.example/otlp')
    await initTelemetry()
    reportCardPainted({ wordToCardMs: 312, tier: 2, room: 'slc1' })
    expect(sendEvent).toHaveBeenCalledWith(CARD_PAINTED_EVENT, {
      attributes: {
        'confpilot.card.word_to_card_ms': 312,
        'confpilot.card.tier': 2,
        'confpilot.room': 'slc1',
      },
    })
  })

  it('does not break the app when the SDK fails to start', async () => {
    vi.stubEnv('VITE_DASH0_RUM_TOKEN', 'browser-token')
    vi.stubEnv('VITE_DASH0_RUM_ENDPOINT', 'https://ingress.example/otlp')
    init.mockImplementation(() => {
      throw new Error('blocked')
    })
    expect(await initTelemetry()).toBe(false)
    expect(() => reportCardPainted({ wordToCardMs: 1, tier: 1, room: null })).not.toThrow()
  })
})
