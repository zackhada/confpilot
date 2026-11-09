// Microphone audio arrives as 32-bit floats at the device's rate (44.1 or 48 kHz). The
// speech-to-text service wants 16 kHz, 16-bit, mono, little-endian PCM (contracts/README.md).

export const TARGET_SAMPLE_RATE = 16_000

/** Convert one float sample (-1..1) to a signed 16-bit integer, clipping anything louder. */
export function floatToInt16(sample: number): number {
  const clipped = Math.max(-1, Math.min(1, sample))
  return Math.round(clipped < 0 ? clipped * 0x8000 : clipped * 0x7fff)
}

export type Downsampler = (input: Float32Array) => Int16Array<ArrayBuffer>

/**
 * Returns a function that turns successive chunks of audio at `inputRate` into 16 kHz
 * 16-bit PCM. Each output sample is the average of the input samples it covers, which
 * also removes most of the frequencies 16 kHz cannot carry. The position is carried
 * between chunks, so chunk boundaries do not click or drift.
 */
export function createDownsampler(inputRate: number, targetRate = TARGET_SAMPLE_RATE): Downsampler {
  if (!(inputRate >= targetRate)) {
    throw new Error(`The microphone rate (${inputRate} Hz) is below ${targetRate} Hz.`)
  }
  const step = inputRate / targetRate
  let position = 0 // fractional input index where the next output window starts
  let carrySum = 0
  let carryCount = 0

  return (input) => {
    const output: number[] = []
    let sum = carrySum
    let count = carryCount
    let windowEnd = position + step
    for (let i = 0; i < input.length; i += 1) {
      if (i >= windowEnd) {
        output.push(floatToInt16(count > 0 ? sum / count : 0))
        sum = 0
        count = 0
        position = windowEnd
        windowEnd = position + step
      }
      sum += input[i] ?? 0
      count += 1
    }
    // Keep the unfinished window for the next chunk, with positions rebased to it.
    carrySum = sum
    carryCount = count
    position -= input.length
    return Int16Array.from(output)
  }
}
