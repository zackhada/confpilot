// STUB written by the UI slice so the app compiles and runs. The pure-logic owner replaces
// this file; keep the exported signature identical.

export interface Clock {
  /** Record one time.ping/time.pong round trip (t0, t1 on the client clock). */
  sample(t0: number, t1: number, serverTs: number): void
  /** The current time in server milliseconds. */
  now(): number
  /** Server time minus client time, in milliseconds. */
  offset(): number
}

export function createClock(): Clock {
  let best: { rtt: number; offset: number } | null = null
  return {
    sample(t0, t1, serverTs) {
      const rtt = t1 - t0
      if (rtt < 0) return
      // The round trip with the least delay gives the most trustworthy offset.
      if (!best || rtt <= best.rtt) best = { rtt, offset: serverTs - (t0 + t1) / 2 }
    },
    now: () => Date.now() + (best?.offset ?? 0),
    offset: () => best?.offset ?? 0,
  }
}
