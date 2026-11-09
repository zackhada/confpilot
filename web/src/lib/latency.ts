// Latency badge maths: contracts/README.md section 2.
// word_to_card_ms = rendered_at - spoken_at, both in server-time epoch milliseconds.

const P95_QUANTILE = 0.95;

/** Milliseconds from the end of the spoken word to the painted card; never negative. */
export function wordToCardMs(spokenAt: number, renderedAt: number): number {
  const elapsed = renderedAt - spokenAt;
  return Number.isFinite(elapsed) ? Math.max(0, Math.round(elapsed)) : 0;
}

/** 95th percentile by the nearest-rank method; 0 for an empty list. */
export function p95(values: number[]): number {
  const sorted = values.filter(Number.isFinite).sort((a, b) => a - b);
  if (sorted.length === 0) return 0;
  const rank = Math.ceil(P95_QUANTILE * sorted.length);
  return sorted[Math.max(0, rank - 1)] as number;
}
