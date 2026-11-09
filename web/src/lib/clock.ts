// Clock sync: contracts/README.md section 3. Phones do not share a clock, so every
// timestamp on the wire is server time. Feed each time.ping / time.pong pair to sample().

export interface Clock {
  /** t0: local ms when time.ping was sent. t1: local ms when time.pong arrived. */
  sample(t0: number, t1: number, serverTs: number): void;
  /** Current time in server-time epoch milliseconds. */
  now(): number;
  /** Milliseconds to add to local time to get server time. 0 until the first sample. */
  offset(): number;
}

export type TimeSource = () => number;

interface BestSample {
  readonly roundTripMs: number;
  readonly offsetMs: number;
}

export function createClock(localNow: TimeSource = Date.now): Clock {
  let best: BestSample | null = null;

  return {
    sample(t0: number, t1: number, serverTs: number): void {
      const roundTripMs = t1 - t0;
      const valid = Number.isFinite(roundTripMs) && Number.isFinite(serverTs) && roundTripMs >= 0;
      if (!valid) return;
      // The shortest round trip has the least network jitter, so its midpoint is the best guess.
      if (best === null || roundTripMs <= best.roundTripMs) {
        best = { roundTripMs, offsetMs: serverTs - (t0 + t1) / 2 };
      }
    },
    now: (): number => localNow() + (best?.offsetMs ?? 0),
    offset: (): number => best?.offsetMs ?? 0,
  };
}
