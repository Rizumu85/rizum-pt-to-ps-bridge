import { useEffect, useRef, useState, type ReactNode } from "react"
import { useGpuixRequired, type PublicInstance } from "@gpuix/react"
import { colors } from "./theme"

export function LayerScroll({ id, children }: { id: string; children: ReactNode }) {
  const renderer = useGpuixRequired()
  const viewport = useRef<PublicInstance>(null)
  const content = useRef<PublicInstance>(null)
  const track = useRef<PublicInstance>(null)
  const drag = useRef<{ y: number; offset: number } | null>(null)
  const [metrics, setMetrics] = useState({ height: 0, total: 0, offset: 0 })

  const measure = () => {
    if (!viewport.current || !content.current) return
    const box = renderer.getElementBounds?.(viewport.current.id)
    const inner = renderer.getElementBounds?.(content.current.id)
    if (!box || !inner) return
    const offset = -(renderer.getScrollOffset?.(viewport.current.id)?.[1] ?? 0)
    const next = { height: box.height, total: inner.height, offset }
    setMetrics(previous => previous.height === next.height && previous.total === next.total
      && previous.offset === next.offset ? previous : next)
  }
  const lastPointerMeasure = useRef(0)

  // Native layout and collapse animations change geometry outside React
  // commits, so read the real bounds instead of estimating from layer counts.
  // Measure on events only: a steady polling timer kept the idle mapper busy
  // enough to compete with Painter. A commit starts a burst that outlasts the
  // 200ms collapse animation; scroll and pointer movement cover the rest,
  // including window resizes, which GPUiX reports no event for.
  useEffect(() => {
    measure()
    const timers = [60, 140, 260].map(delay => setTimeout(measure, delay))
    return () => timers.forEach(clearTimeout)
  })

  const measureOnPointer = () => {
    const now = Date.now()
    if (now - lastPointerMeasure.current < 100) return
    lastPointerMeasure.current = now
    measure()
  }

  const maximum = Math.max(0, metrics.total - metrics.height)
  const thumb = Math.min(metrics.height, Math.max(28, metrics.height * metrics.height / Math.max(1, metrics.total)))
  const travel = metrics.height - thumb
  const scroll = (offset: number) => {
    if (!viewport.current) return
    const value = Math.max(0, Math.min(maximum, offset))
    renderer.scrollTo?.(viewport.current.id, 0, -value)
    setMetrics(previous => ({ ...previous, offset: value }))
  }

  return <div onMouseMove={measureOnPointer} onMouseEnter={measure}
    style={{ display: "flex", flexDirection: "row", flexGrow: 1, flexBasis: 0, minHeight: 0 }}>
    <div ref={viewport} testId={`layer-scroll:${id}`} onScroll={measure}
      style={{ flexGrow: 1, flexBasis: 0, minWidth: 0, minHeight: 0, overflowY: "scroll", overflowX: "hidden" }}>
      <div ref={content} style={{ display: "flex", flexDirection: "column", minHeight: "100%", padding: 8, flexShrink: 0 }}>
        {children}
      </div>
    </div>
    <div ref={track} testId={`layer-scrollbar:${id}`}
      onMouseDown={event => {
        const box = track.current && renderer.getElementBounds?.(track.current.id)
        if (!box || !maximum) return
        const y = (event.y ?? box.y) - box.y
        const top = metrics.offset / maximum * travel
        const offset = y >= top && y <= top + thumb ? metrics.offset
          : Math.max(0, Math.min(maximum, (y - thumb / 2) / Math.max(1, travel) * maximum))
        scroll(offset)
        drag.current = { y: event.y ?? 0, offset }
      }}
      onMouseMove={event => {
        if (drag.current) scroll(drag.current.offset + ((event.y ?? 0) - drag.current.y) * maximum / Math.max(1, travel))
      }}
      onMouseUp={() => { drag.current = null }}
      style={{ width: 12, flexShrink: 0, position: "relative", cursor: maximum ? "pointer" : "default" }}>
      {maximum > 0 ? <div style={{ position: "absolute", left: 3, width: 6,
        top: Math.min(maximum, metrics.offset) / maximum * travel, height: thumb,
        borderRadius: 3, backgroundColor: colors.tertiary, pointerEvents: "none" }} /> : null}
    </div>
  </div>
}
