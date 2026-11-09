// Dash0 browser monitoring. It is off unless both VITE_DASH0_RUM_TOKEN and
// VITE_DASH0_RUM_ENDPOINT are set at build time, and the SDK is only downloaded when it is
// on. The token is an ingest-only browser token, which Dash0 treats as public.
//
// The SDK adds trace headers to same-origin requests by itself, so calls to our own
// /api/* join the backend trace with no further configuration.
import type { CardTier } from '@contracts'

type Dash0Sdk = typeof import('@dash0/sdk-web')

export const CARD_PAINTED_EVENT = 'confpilot.card.painted'

let sdk: Dash0Sdk | null = null

interface TelemetryConfig {
  token: string
  url: string
}

function readConfig(): TelemetryConfig | null {
  const token = import.meta.env.VITE_DASH0_RUM_TOKEN
  const url = import.meta.env.VITE_DASH0_RUM_ENDPOINT
  return token && url ? { token, url } : null
}

/** Start monitoring if it is configured. Resolves to whether it is running. */
export async function initTelemetry(): Promise<boolean> {
  const config = readConfig()
  if (!config) return false
  try {
    const loaded = await import('@dash0/sdk-web')
    loaded.init({
      serviceName: 'confpilot-web',
      endpoint: { url: config.url, authToken: config.token },
    })
    sdk = loaded
    return true
  } catch {
    // Monitoring must never break the app; without it the phone works exactly the same.
    return false
  }
}

export interface CardPainted {
  wordToCardMs: number
  tier: CardTier
  room: string | null
}

/** The north-star measurement, sent once per card at its first paint. A no-op when off. */
export function reportCardPainted({ wordToCardMs, tier, room }: CardPainted): void {
  sdk?.sendEvent(CARD_PAINTED_EVENT, {
    attributes: {
      'confpilot.card.word_to_card_ms': wordToCardMs,
      'confpilot.card.tier': tier,
      'confpilot.room': room ?? 'unknown',
    },
  })
}

/** Test hook: forget the loaded SDK. */
export function resetTelemetry(): void {
  sdk = null
}
