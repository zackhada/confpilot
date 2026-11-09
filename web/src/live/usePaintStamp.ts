import { useLayoutEffect } from 'react'

/**
 * Calls `onPainted` once, right after the browser has painted this element for the first
 * time. requestAnimationFrame fires just before that paint; the message task queued inside
 * it runs straight after. The entrance animation is still running at that point, which is
 * the intent: latency is measured to first paint, never to the end of the animation.
 */
export function usePaintStamp(enabled: boolean, onPainted: () => void): void {
  useLayoutEffect(() => {
    if (!enabled) return
    const channel = new MessageChannel()
    channel.port1.onmessage = onPainted
    const frame = requestAnimationFrame(() => channel.port2.postMessage(null))
    return () => {
      cancelAnimationFrame(frame)
      channel.port1.onmessage = null
      channel.port1.close()
    }
    // The stamp belongs to the mount of one card; later re-renders must not repeat it.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])
}
