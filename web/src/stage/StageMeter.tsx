import { Hourglass, Zap } from 'lucide-react'
import { QRCodeSVG } from 'qrcode.react'
import { LATENCY_TARGET_MS } from '@/live/LatencyBadge'
import { p95 } from '@/lib/latency'
import { useRoom } from '@/room/store'

interface StageMeterProps {
  room: string
  joinUrl: string
}

/** Centre column of the stage: how to join, and the live word-to-card promise. */
export function StageMeter({ room, joinUrl }: StageMeterProps) {
  const latencies = useRoom((s) => s.latencies)
  const value = latencies.length > 0 ? p95(latencies) : null
  const onTarget = value !== null && value <= LATENCY_TARGET_MS
  const Icon = onTarget ? Zap : Hourglass

  return (
    <div className="flex w-[19rem] flex-col items-center justify-between self-stretch py-2 text-center">
      <div>
        <div className="on-lit inline-block rounded-(--radius-card) bg-[#f6f0e2] p-4">
          <QRCodeSVG value={joinUrl} size={196} bgColor="#f6f0e2" fgColor="#131a30" level="M" title={`Join room ${room}`} />
        </div>
        <p className="mt-4 text-(length:--text-lead) text-ink-soft">Join on your phone</p>
        <p className="tabular font-display text-4xl">{room}</p>
      </div>

      <div aria-live="polite" aria-atomic="true">
        <p className="text-(length:--text-lead) text-ink-soft">Word spoken to card on screen</p>
        <p className="tabular font-display text-[5.5rem] leading-none">
          {value ?? '–'}
          <span className="pl-2 font-sans text-3xl font-semibold text-ink-soft">ms</span>
        </p>
        <p className="mt-3 text-(length:--text-lead) text-ink-soft">
          95th percentile of {latencies.length} {latencies.length === 1 ? 'card' : 'cards'}
        </p>
        {value !== null && (
          <p
            className={`mt-3 inline-flex items-center gap-2 text-(length:--text-lead) font-bold ${onTarget ? 'text-known' : 'text-fresh'}`}
          >
            <Icon className="size-5" aria-hidden="true" />
            {onTarget ? `Inside the ${LATENCY_TARGET_MS} ms target` : `Over the ${LATENCY_TARGET_MS} ms target`}
          </p>
        )}
      </div>
    </div>
  )
}
