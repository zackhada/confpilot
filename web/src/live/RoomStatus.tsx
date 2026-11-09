import { LoaderCircle, Radio, WifiOff } from 'lucide-react'
import type { ComponentType } from 'react'
import { useRoom, type RoomData } from '@/room/store'
import { cn } from '@/shared/cn'

interface StatusLook {
  label: string
  Icon: ComponentType<{ className?: string; 'aria-hidden'?: 'true' }>
  tone: string
  spin?: boolean
}

const LOOKS: Record<RoomData['status'], StatusLook> = {
  idle: { label: 'Not connected', Icon: WifiOff, tone: 'text-ink-soft' },
  connecting: { label: 'Connecting', Icon: LoaderCircle, tone: 'text-fresh', spin: true },
  open: { label: 'Live', Icon: Radio, tone: 'text-known' },
  reconnecting: { label: 'Reconnecting', Icon: LoaderCircle, tone: 'text-fresh', spin: true },
  closed: { label: 'Disconnected', Icon: WifiOff, tone: 'text-danger' },
}

/** Room code and connection state. The label and icon change, not only the colour. */
export function RoomStatus() {
  const room = useRoom((s) => s.room)
  const status = useRoom((s) => s.status)
  const { label, Icon, tone, spin } = LOOKS[status]
  return (
    <output className="flex min-w-0 items-center gap-2.5">
      <span className="tabular truncate font-display text-xl">
        <span className="sr-only">Room </span>
        {room}
      </span>
      <span className={cn('inline-flex items-center gap-1 text-(length:--text-note) font-bold', tone)}>
        <Icon className={cn('size-4', spin && 'animate-spin')} aria-hidden="true" />
        {label}
      </span>
    </output>
  )
}
