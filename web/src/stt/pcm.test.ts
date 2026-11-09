import { describe, expect, it } from 'vitest'
import { createDownsampler, floatToInt16 } from './pcm'

describe('floatToInt16', () => {
  it('maps the float range onto the 16-bit range', () => {
    expect(floatToInt16(0)).toBe(0)
    expect(floatToInt16(1)).toBe(32767)
    expect(floatToInt16(-1)).toBe(-32768)
  })

  it('clips samples that are too loud instead of wrapping', () => {
    expect(floatToInt16(1.8)).toBe(32767)
    expect(floatToInt16(-3)).toBe(-32768)
  })
})

describe('createDownsampler', () => {
  it('turns one second at 48 kHz into about one second at 16 kHz', () => {
    const downsample = createDownsampler(48_000)
    const out = downsample(new Float32Array(48_000).fill(0.5))
    expect(Math.abs(out.length - 16_000)).toBeLessThanOrEqual(1)
    expect(out[100]).toBe(floatToInt16(0.5))
  })

  it('produces the same number of samples however the audio is chunked', () => {
    const whole = createDownsampler(44_100)(new Float32Array(44_100))
    const chunked = createDownsampler(44_100)
    let total = 0
    for (let i = 0; i < 44_100; i += 2048) {
      total += chunked(new Float32Array(Math.min(2048, 44_100 - i))).length
    }
    expect(Math.abs(total - whole.length)).toBeLessThanOrEqual(1)
    expect(Math.abs(total - 16_000)).toBeLessThanOrEqual(1)
  })

  it('averages the samples each output covers', () => {
    const downsample = createDownsampler(48_000)
    const out = downsample(Float32Array.from([0.3, 0.6, 0.9, -0.2, -0.2, -0.2, 0, 0, 0]))
    expect(out[0]).toBe(floatToInt16(0.6))
    expect(out[1]).toBe(floatToInt16(-0.2))
  })

  it('passes 16 kHz audio through sample for sample', () => {
    const out = createDownsampler(16_000)(Float32Array.from([0.1, -0.1, 0.2, 0]))
    expect([...out]).toEqual([floatToInt16(0.1), floatToInt16(-0.1), floatToInt16(0.2)])
  })

  it('refuses a microphone slower than the target rate', () => {
    expect(() => createDownsampler(8000)).toThrow(/below 16000 Hz/)
  })
})
