// STUB written by the UI slice so the app compiles and runs. The pure-logic owner replaces
// this file; keep the exported signatures identical.

/** Milliseconds from the end of the spoken word to the painted card. Never negative. */
export function wordToCardMs(spokenAt: number, renderedAt: number): number {
  return Math.max(0, Math.round(renderedAt - spokenAt))
}

/** 95th percentile by the nearest-rank method. Returns 0 for an empty list. */
export function p95(values: number[]): number {
  if (values.length === 0) return 0
  const sorted = [...values].sort((a, b) => a - b)
  const rank = Math.ceil(0.95 * sorted.length)
  return sorted[Math.max(0, rank - 1)] ?? 0
}
