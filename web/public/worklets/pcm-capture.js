// AudioWorklet that hands microphone samples to the page in small batches.
// It stays tiny on purpose: resampling and 16-bit conversion happen in src/stt/pcm.ts,
// where they are unit tested. Only channel 0 is used (the mic is requested as mono).

const BATCH_FRAMES = 2048 // about 43 ms at 48 kHz

class PcmCapture extends AudioWorkletProcessor {
  constructor() {
    super()
    this.batch = new Float32Array(BATCH_FRAMES)
    this.filled = 0
  }

  process(inputs) {
    const channel = inputs[0] && inputs[0][0]
    if (!channel) return true
    let offset = 0
    while (offset < channel.length) {
      const room = BATCH_FRAMES - this.filled
      const take = Math.min(room, channel.length - offset)
      this.batch.set(channel.subarray(offset, offset + take), this.filled)
      this.filled += take
      offset += take
      if (this.filled === BATCH_FRAMES) {
        const full = this.batch
        this.port.postMessage(full, [full.buffer])
        this.batch = new Float32Array(BATCH_FRAMES)
        this.filled = 0
      }
    }
    return true
  }
}

registerProcessor('pcm-capture', PcmCapture)
