import { useMemo } from 'react'
import { useRoom, type Utterance } from '@/room/store'
import { withoutEchoes } from './dedupe'

/** The utterances to caption: everything heard in the room, minus cross-phone echoes. */
export function useCaptions(): Utterance[] {
  const utterances = useRoom((s) => s.utterances)
  return useMemo(() => withoutEchoes(utterances), [utterances])
}
