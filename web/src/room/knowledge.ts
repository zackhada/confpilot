// What this person knows, from three layers. Later layers win:
//   seed   the persona's starting point (by glossary category)
//   server what the API has stored for this user (taps and reviews from any earlier visit)
//   local  taps and probe answers made on this phone, kept in localStorage
// Every change is also PUT to the API. If that fails the local layer still has it, so the
// app keeps working offline and the next successful write carries the newer value.
import type { Knowledge, KnowledgePatch, KnowledgeStatus, Speaker } from '@contracts'
import { fetchKnowledge, putKnowledge } from './api'
import { loadKnowledge, storeKnowledge } from './identity'
import { demoSeeding } from './demo'
import { useRoom } from './store'

type Statuses = Record<string, KnowledgeStatus>

let seed: Statuses = {}
let server: Statuses = {}
let local: Statuses = {}

function publish(): void {
  useRoom.getState().patch({ knowledge: { ...seed, ...server, ...local } })
}

/** Start a fresh room session: forget the server layer and re-read this phone's taps. */
export function resetKnowledge(): void {
  seed = {}
  server = {}
  local = loadKnowledge()
}

export function setSeedKnowledge(statuses: Statuses): void {
  seed = statuses
  publish()
}

/** Load what the API has for this user. A failure leaves the seed and local layers in charge. */
export async function loadServerKnowledge(me: Speaker, isCurrent: () => boolean): Promise<void> {
  await demoSeeding
  try {
    const items = await fetchKnowledge(me.name, me.user_id)
    if (!isCurrent()) return
    server = Object.fromEntries(items.map((item) => [item.term_id, item.status]))
    useRoom.getState().patch({ records: Object.fromEntries(items.map((item) => [item.term_id, item])) })
    publish()
  } catch {
    // Offline or the API is not up yet: the phone carries on with what it has.
  }
}

function push(termId: string, patch: KnowledgePatch): void {
  const me = useRoom.getState().me
  if (!me) return
  putKnowledge(me.name, me.user_id, termId, patch)
    .then((record) => useRoom.getState().setRecord(record))
    .catch(() => {
      // Kept in the local layer; see the note at the top of this file.
    })
}

/** A tap or a probe answer: update this phone at once, then tell the API. */
export function recordStatus(termId: string, status: KnowledgeStatus, source: 'tap' | 'probe'): void {
  local = { ...local, [termId]: status }
  storeKnowledge(local)
  useRoom.getState().setKnowledge(termId, status)
  push(termId, { status, source })
}

/** Many statuses at once (the onboarding probe). */
export function recordStatuses(statuses: Statuses, source: 'tap' | 'probe'): void {
  Object.entries(statuses).forEach(([termId, status]) => recordStatus(termId, status, source))
}

/** A flashcard review: keep the full SM-2 record and save it. */
export function saveReview(record: Knowledge): void {
  local = { ...local, [record.term_id]: record.status }
  storeKnowledge(local)
  const room = useRoom.getState()
  room.setRecord(record)
  room.setKnowledge(record.term_id, record.status)
  const { status, source, ease, interval_days, reps, due_at, learned } = record
  push(record.term_id, { status, source, ease, interval_days, reps, due_at, learned })
}
