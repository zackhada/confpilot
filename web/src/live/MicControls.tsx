import { LoaderCircle, Mic, MicOff } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { cn } from '@/shared/cn'
import { startListening, stopListening, useMic, type MicState } from '@/stt/mic'

const ACTIVE: ReadonlySet<MicState> = new Set(['starting', 'listening', 'reconnecting'])

function toggleMic(state: MicState): void {
  if (ACTIVE.has(state)) stopListening()
  else void startListening()
}

/** Compact mic toggle for the header. Filled while the mic is on; the icon changes too. */
export function MicButton() {
  const state = useMic((s) => s.state)
  const on = ACTIVE.has(state)
  const busy = state === 'starting' || state === 'reconnecting'
  const Icon = busy ? LoaderCircle : on ? Mic : MicOff
  return (
    <Button
      variant="ghost"
      size="icon"
      onClick={() => toggleMic(state)}
      aria-pressed={on}
      aria-label={on ? 'Turn off your microphone' : 'Turn on your microphone'}
      className={cn(on && 'bg-ink text-hall hover:text-hall')}
    >
      <Icon className={cn(busy && 'animate-spin')} aria-hidden="true" />
    </Button>
  )
}

const NOTICES: Partial<Record<MicState, { text: string; retry: boolean }>> = {
  reconnecting: { text: 'Lost the speech connection. Reconnecting now.', retry: false },
  denied: {
    text: 'Microphone access is blocked. Allow it for this site in your browser settings, then try again.',
    retry: true,
  },
  unsupported: {
    text: 'This browser cannot use the microphone here. Open ConfPilot over HTTPS in Safari or Chrome.',
    retry: false,
  },
  unavailable: {
    text: 'Speech-to-text is not reachable right now. Captions from other people in the room still work.',
    retry: true,
  },
  error: { text: 'The microphone did not start. Check that no other app is using it.', retry: true },
}

/** Plain-language mic problems, with a way forward. Renders nothing when all is well. */
export function MicNotice() {
  const state = useMic((s) => s.state)
  const notice = NOTICES[state]
  if (!notice) return null
  return (
    <div
      role={state === 'reconnecting' ? 'status' : 'alert'}
      className="px-safe flex items-center gap-3 pb-3 text-(length:--text-note) leading-snug"
    >
      <p className="min-w-0 flex-1 font-semibold text-ink">{notice.text}</p>
      {notice.retry && (
        <Button className="shrink-0" onClick={() => useMic.setState({ state: 'off' })}>
          Dismiss
        </Button>
      )}
    </div>
  )
}

/** Shown in the thumb zone before the first card: the one action that starts everything. */
export function StartPanel() {
  const state = useMic((s) => s.state)
  const on = ACTIVE.has(state)
  return (
    <div className="px-safe pb-4">
      <p className="pb-3 text-(length:--text-note) text-ink-soft">
        {on
          ? 'Your mic is on. Cards appear here for words that are new to you.'
          : 'Cards appear here for words that are new to you. Turn on your mic if you are speaking too.'}
      </p>
      {!on && (
        <Button variant="primary" size="lg" className="w-full" onClick={() => toggleMic(state)}>
          <Mic aria-hidden="true" />
          Turn on my mic
        </Button>
      )}
    </div>
  )
}
