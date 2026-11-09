import { MotionConfig } from 'motion/react'
import { useEffect } from 'react'
import { useSearchParams } from 'react-router'
import { RoomStatus } from '@/live/RoomStatus'
import { STAGE_NAME } from '@/room/auth'
import { parseRoomCode } from '@/room/identity'
import { joinRoom, leaveRoom } from '@/room/session'
import { useRoom } from '@/room/store'
import { ThemeToggle } from '@/shell/ThemeToggle'
import { StageMeter } from './StageMeter'
import { StagePhone } from './StagePhone'

/** Projector view: both speakers' phones side by side, a join code, and live p95 latency. */
export function StageView() {
  const [params] = useSearchParams()
  const room = parseRoomCode(params.get('room'))
  const members = useRoom((s) => s.members)
  const speakers = members.filter((member) => member.role === 'speaker')

  useEffect(() => {
    if (!room) return
    joinRoom({ room, role: 'viewer', name: STAGE_NAME })
    return leaveRoom
  }, [room])

  if (!room) {
    return (
      <main className="grid min-h-dvh place-items-center bg-hall-sunk p-8 text-center">
        <div>
          <h1 className="font-display text-(length:--text-title)">This stage has no room yet</h1>
          <p className="mt-3 text-(length:--text-lead) text-ink-soft">
            Add a room code to the address, for example <span className="tabular font-bold text-ink">/stage?room=slc1</span>
          </p>
        </div>
      </main>
    )
  }

  const joinUrl = `${window.location.origin}/?room=${room}`
  return (
    <MotionConfig reducedMotion="user">
      <div className="flex h-dvh min-h-[40rem] flex-col bg-hall-sunk">
        <header className="flex items-center justify-between px-10 pt-6 pb-4">
          <div className="flex items-baseline gap-5">
            <p className="font-display text-3xl">ConfPilot</p>
            <h1 className="text-(length:--text-lead) text-ink-soft">Stop nodding along.</h1>
          </div>
          <div className="flex items-center gap-2">
            <RoomStatus />
            <ThemeToggle />
          </div>
        </header>
        <main className="flex min-h-0 flex-1 items-stretch justify-center gap-12 px-10 pb-8">
          <StagePhone owner={speakers[0]} side="left" />
          <StageMeter room={room} joinUrl={joinUrl} />
          <StagePhone owner={speakers[1]} side="right" />
        </main>
      </div>
    </MotionConfig>
  )
}
