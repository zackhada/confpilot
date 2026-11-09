import type { Recap } from '@contracts'
import { useEffect, useMemo, useState } from 'react'
import { fetchRecap } from '@/room/api'
import { useRoom } from '@/room/store'
import { localRecap } from './localRecap'

export interface RecapView {
  recap: Recap
  /** Where the numbers came from: the API, or counted on this phone as a fallback. */
  source: 'api' | 'local'
}

/**
 * The recap for this person and room. The phone's own count is ready at once; the API's
 * recap replaces it when it arrives. If the API is unreachable, or has nothing while the
 * phone has, the phone's count stays.
 */
export function useRecap(): RecapView {
  const room = useRoom((s) => s.room)
  const me = useRoom((s) => s.me)
  const ready = useRoom((s) => s.status === 'open' && s.members.some((m) => m.user_id === s.me?.user_id))
  const heard = useRoom((s) => s.heard)
  const heardCount = Object.keys(heard).length
  const shownTermIds = useRoom((s) => s.stack.shownTermIds)
  const terms = useRoom((s) => s.terms)
  const knowledge = useRoom((s) => s.knowledge)
  const [result, setResult] = useState<{ userId: string; recap: Recap } | null>(null)
  const remote = result && result.recap.room === room && result.userId === me?.user_id ? result.recap : null

  const local = useMemo(
    () => localRecap({ room: room ?? '', heard, shownTermIds, terms: Object.values(terms), knowledge }),
    [room, heard, shownTermIds, terms, knowledge],
  )

  useEffect(() => {
    if (!room || !me || !ready) return
    let current = true
    fetchRecap(me.name, room, me.user_id)
      .then((recap) => {
        if (current) setResult({ userId: me.user_id, recap })
      })
      .catch(() => {
        if (current) setResult(null)
      })
    return () => {
      current = false
    }
    // Refetch when the phone has heard a new distinct term, so the screen stays fresh while it is open.
  }, [room, me, ready, heardCount])

  const useRemote = remote !== null && (remote.heard.length > 0 || local.heard.length === 0)
  return useRemote ? { recap: remote, source: 'api' } : { recap: local, source: 'local' }
}
