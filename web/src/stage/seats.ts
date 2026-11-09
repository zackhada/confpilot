import type { Speaker } from '@contracts'

/** The two phone panels on the stage: left and right. Null is an open seat. */
export type Seats = readonly [Speaker | null, Speaker | null]

export const EMPTY_SEATS: Seats = [null, null]

/**
 * Keep each speaker on their side of the stage. A phone that reconnects comes back at the
 * end of the member list; without this, the two panels would swap sides mid-demo. A seat is
 * given away only when its speaker has left and someone new has nowhere to sit.
 */
export function assignSeats(previous: Seats, speakers: readonly Speaker[]): Seats {
  const present = new Map(speakers.map((speaker) => [speaker.user_id, speaker]))
  const seated = new Set(previous.flatMap((seat) => (seat ? [seat.user_id] : [])))
  const waiting = speakers.filter((speaker) => !seated.has(speaker.user_id))

  // First refresh names and fill open seats, then let newcomers take seats of people who left.
  const filled = previous.map((seat) => {
    if (seat) return present.get(seat.user_id) ?? seat
    return waiting.shift() ?? null
  })
  const next = filled.map((seat) => {
    if (seat && !present.has(seat.user_id) && waiting.length > 0) return waiting.shift() ?? seat
    return seat
  })
  return [next[0] ?? null, next[1] ?? null]
}

export function sameSeats(a: Seats, b: Seats): boolean {
  return a.every((seat, i) => seat?.user_id === b[i]?.user_id && seat?.name === b[i]?.name)
}
