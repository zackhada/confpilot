import { useRoom } from '@/room/store'

const SPOKEN_HISTORY = 3

/**
 * Screen reader feed. The visible captions change several times a second, which would
 * flood a screen reader, so these two polite live regions carry only finished sentences
 * and newly shown cards.
 */
export function Announcer() {
  const meId = useRoom((s) => s.me?.user_id)
  const finals = useRoom((s) => s.utterances).filter((u) => u.is_final).slice(-SPOKEN_HISTORY)
  const newest = useRoom((s) => s.stack.full[0])
  const term = useRoom((s) => (newest ? s.terms[newest.term_id] : undefined))

  return (
    <div className="sr-only">
      <div role="log" aria-live="polite" aria-label="Captions">
        {finals.map((u) => (
          <p key={u.utterance_id}>
            {u.speaker.user_id === meId ? 'You' : u.speaker.name}: {u.words.map((w) => w.w).join(' ')}
          </p>
        ))}
      </div>
      <div aria-live="polite" aria-atomic="true">
        {newest && term ? `New term: ${term.term}. ${term.simple_def}` : ''}
      </div>
    </div>
  )
}
