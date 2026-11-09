import { describe, expect, it } from 'vitest';
import { createClock } from './clock';

describe('createClock', () => {
  it('reports local time and a zero offset before any sample', () => {
    const clock = createClock(() => 1_000);
    expect(clock.offset()).toBe(0);
    expect(clock.now()).toBe(1_000);
  });

  it('computes offset = serverTs - (t0 + t1) / 2', () => {
    const clock = createClock(() => 2_000);
    clock.sample(1_000, 1_100, 6_050);
    expect(clock.offset()).toBe(5_000);
    expect(clock.now()).toBe(7_000);
  });

  it('handles a server clock that is behind the phone', () => {
    const clock = createClock(() => 10_000);
    clock.sample(9_000, 9_040, 4_020);
    expect(clock.offset()).toBe(-5_000);
    expect(clock.now()).toBe(5_000);
  });

  it('keeps the sample with the lowest round-trip time', () => {
    const clock = createClock(() => 0);
    clock.sample(0, 400, 1_200); // rtt 400, offset 1000
    clock.sample(1_000, 1_040, 2_030); // rtt 40, offset 1010
    clock.sample(2_000, 2_300, 3_100); // rtt 300, offset 950: ignored
    expect(clock.offset()).toBe(1_010);
  });

  it('prefers the newer sample when round-trip times tie', () => {
    const clock = createClock(() => 0);
    clock.sample(0, 50, 1_025);
    clock.sample(100, 150, 1_130);
    expect(clock.offset()).toBe(1_005);
  });

  it('ignores impossible samples', () => {
    const clock = createClock(() => 0);
    clock.sample(500, 400, 9_999);
    clock.sample(Number.NaN, 400, 9_999);
    clock.sample(0, 100, Number.POSITIVE_INFINITY);
    expect(clock.offset()).toBe(0);
  });

  it('follows the injected local time source', () => {
    let local = 100;
    const clock = createClock(() => local);
    clock.sample(0, 10, 505);
    local = 250;
    expect(clock.now()).toBe(750);
  });

  it('defaults to Date.now', () => {
    const before = Date.now();
    const now = createClock().now();
    expect(now).toBeGreaterThanOrEqual(before);
    expect(now).toBeLessThanOrEqual(Date.now());
  });
});
