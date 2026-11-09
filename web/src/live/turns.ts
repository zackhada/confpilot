import type { Speaker } from '@contracts'
import type { Utterance } from '@/room/store'

export interface Turn {
  speaker: Speaker
  utterances: Utterance[]
}

/** Consecutive utterances from one speaker read as one paragraph. */
export function groupTurns(utterances: readonly Utterance[]): Turn[] {
  return utterances.reduce<Turn[]>((turns, utterance) => {
    const last = turns[turns.length - 1]
    if (last && last.speaker.user_id === utterance.speaker.user_id) {
      return [...turns.slice(0, -1), { ...last, utterances: [...last.utterances, utterance] }]
    }
    return [...turns, { speaker: utterance.speaker, utterances: [utterance] }]
  }, [])
}
