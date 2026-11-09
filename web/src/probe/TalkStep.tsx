import type { TranscriptEvent } from '@contracts'
import { LoaderCircle, Mic, Square } from 'lucide-react'
import { useEffect, useId, useState } from 'react'
import { Button } from '@/components/ui/button'
import { MicNotice } from '@/live/MicControls'
import { startListening, stopListening, useMic } from '@/stt/mic'

interface TalkStepProps {
  /** True while /api/probe is reading the text (an LLM call of a few seconds). */
  busy: boolean
  note: string | null
  onContinue: (text: string) => void
  onSkip: () => void
}

/**
 * Step one of "Tune it to me": say or type what you do. Speech goes through the same mic
 * pipeline as Live, but stays on this screen; it is never sent to the room.
 */
export function TalkStep({ busy, note, onContinue, onSkip }: TalkStepProps) {
  const fieldId = useId()
  const [text, setText] = useState('')
  const [interim, setInterim] = useState('')
  const micState = useMic((s) => s.state)
  const listening = micState === 'listening' || micState === 'starting' || micState === 'reconnecting'

  // Leaving this step always turns the mic off.
  useEffect(() => stopListening, [])

  const hear = (event: TranscriptEvent): void => {
    if (!event.is_final) return setInterim(event.text)
    setInterim('')
    setText((previous) => `${previous} ${event.text}`.trim())
  }

  const toggleMic = (): void => {
    if (listening) stopListening()
    else void startListening(hear)
  }

  const finish = (): void => {
    stopListening()
    onContinue(`${text} ${interim}`.trim())
  }

  return (
    <div className="px-safe flex min-h-0 flex-1 flex-col pb-5">
      <h1 className="max-w-[12ch] pt-2 font-display text-(length:--text-title) leading-[1.05]">
        What do you do?
      </h1>
      <label htmlFor={fieldId} className="block max-w-[32ch] pt-3 pb-4 text-(length:--text-lead) text-ink-soft">
        Talk for half a minute, or type. The words you already use will not get cards.
      </label>
      <textarea
        id={fieldId}
        value={interim ? `${text} ${interim}`.trim() : text}
        onChange={(e) => setText(e.target.value)}
        readOnly={listening || busy}
        placeholder="I work on the platform team. We run Kubernetes clusters and I am on call for…"
        className="min-h-36 w-full flex-1 resize-none rounded-(--radius-card) border border-rule bg-hall-raised p-4 text-(length:--text-lead) leading-snug text-ink placeholder:text-ink-soft/70"
      />
      <div className="pt-3">
        <MicNotice />
        <output className="block min-h-6 pb-2 text-(length:--text-note) text-ink-soft">
          {busy ? 'Reading what you said. This takes a few seconds.' : note}
        </output>
        <div className="flex gap-2">
          <Button size="lg" onClick={toggleMic} disabled={busy} aria-pressed={listening} className="px-5">
            {listening ? <Square aria-hidden="true" /> : <Mic aria-hidden="true" />}
            {listening ? 'Stop' : 'Speak'}
          </Button>
          <Button variant="primary" size="lg" className="flex-1" onClick={finish} disabled={busy}>
            {busy && <LoaderCircle className="animate-spin" aria-hidden="true" />}
            {busy ? 'Reading' : 'Continue'}
          </Button>
        </div>
        <Button variant="ghost" className="mt-1 w-full" onClick={onSkip} disabled={busy}>
          Skip, use a persona
        </Button>
      </div>
    </div>
  )
}
