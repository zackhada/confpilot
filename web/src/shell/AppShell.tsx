import { useEffect } from 'react'
import { Outlet, useSearchParams } from 'react-router'
import { parseRoomCode } from '@/room/identity'
import { personaById } from '@/room/personas'
import { useProfile } from '@/room/profile'
import { joinRoom, leaveRoom } from '@/room/session'
import { Join } from '@/screens/Join'
import { TermSheet } from '@/shared/TermSheet'
import { stopListening } from '@/stt/mic'
import { TabBar } from './TabBar'

/** Phone frame: the screen fills the space above a fixed bottom tab bar. */
export function AppShell() {
  const [params, setParams] = useSearchParams()
  const room = parseRoomCode(params.get('room'))
  const profile = useProfile((s) => s.profile)
  const join = useProfile((s) => s.join)

  // The room session outlives tab changes, so captions and cards keep flowing in the
  // background while someone looks at Recap or Ask.
  useEffect(() => {
    if (!room || !profile) return
    joinRoom({
      room,
      role: 'speaker',
      name: profile.name,
      lang: profile.lang,
      persona: personaById(profile.persona),
    })
    return () => {
      stopListening()
      leaveRoom()
    }
  }, [room, profile])

  if (!room || !profile) {
    return (
      <Join
        initialRoom={room}
        onJoin={(next, code) => {
          join(next)
          setParams({ room: code }, { replace: true })
        }}
      />
    )
  }

  return (
    <div className="mx-auto flex h-dvh w-full max-w-xl flex-col bg-hall">
      <a
        href="#screen"
        className="sr-only focus:not-sr-only focus:absolute focus:top-2 focus:left-2 focus:z-50 focus:rounded-lg focus:bg-fresh focus:px-4 focus:py-3 focus:font-semibold focus:text-fresh-ink"
      >
        Skip to content
      </a>
      <main id="screen" className="pt-safe flex min-h-0 flex-1 flex-col">
        <Outlet />
      </main>
      <TabBar />
      <TermSheet />
    </div>
  )
}
