import { useEffect, useRef, useState, type ReactNode } from "react"
import { AnimatePresence, useGpuixRequired, useWindowSize, type PublicInstance } from "@gpuix/react"
import { colors, metrics as themeMetrics } from "./theme"

export function LayerScroll({ id, children, layoutKey, rowCount }: { id: string; children: ReactNode[]; layoutKey: unknown; rowCount: number }) {
  const renderer = useGpuixRequired()
  const windowSize = useWindowSize()
  const viewport = useRef<PublicInstance>(null)
  const track = useRef<PublicInstance>(null)
  const drag = useRef<{ y: number; offset: number } | null>(null)
  const [metrics, setMetrics] = useState({ height: 0, total: 0, offset: 0 })
  const [range, setRange] = useState({ start: 0, end: 32 })
  const start = Math.min(range.start, Math.max(0, rowCount - 1))

  const anchorOffset = (anchor: number[]) => Math.max(0, Math.min(
    Math.max(0, rowCount * themeMetrics.rowHeight - anchor[2]),
    anchor[0] * themeMetrics.rowHeight + anchor[1],
  ))

  const measure = () => {
    if (!viewport.current) return
    const anchor = renderer.getListScrollTop?.(viewport.current.id)
    if (!anchor) return
    // Virtual lists have no painted element bounds. Their native scroll anchor
    // owns both viewport height and position, including the at-end sentinel.
    const offset = anchorOffset(anchor)
    const next = { height: anchor[2], total: rowCount * themeMetrics.rowHeight, offset }
    setMetrics(previous => previous.height === next.height && previous.total === next.total
      && previous.offset === next.offset ? previous : next)
  }
  // Geometry belongs to structural changes, not pointer feedback. Measuring
  // after every scrollbar commit creates extra native layouts while scrolling.
  useEffect(() => {
    measure()
    const timers = [60, 140, 260].map(delay => setTimeout(measure, delay))
    return () => timers.forEach(clearTimeout)
  }, [layoutKey, windowSize.width, windowSize.height])

  const maximum = Math.max(0, metrics.total - metrics.height)
  const thumb = Math.min(metrics.height, Math.max(28, metrics.height * metrics.height / Math.max(1, metrics.total)))
  const travel = metrics.height - thumb
  const scroll = (offset: number) => {
    if (!viewport.current) return
    const value = Math.max(0, Math.min(maximum, offset))
    renderer.scrollToItem?.(viewport.current.id, Math.floor(value / themeMetrics.rowHeight), value % themeMetrics.rowHeight)
    setMetrics(previous => ({ ...previous, offset: value }))
  }

  return <div
    style={{ display: "flex", flexDirection: "row", flexGrow: 1, flexBasis: 0, minHeight: 0 }}>
    <virtual-list ref={viewport} testId={`layer-scroll:${id}`} itemCount={rowCount} windowStart={start}
      estimatedItemHeight={themeMetrics.rowHeight} overdraw={64} onVisibleRange={event => {
      const next = { start: Math.max(0, (event.startIndex ?? 0) - 8), end: (event.endIndex ?? 24) + 8 }
      setRange(previous => previous.start === next.start && previous.end === next.end ? previous : next)
      if (!viewport.current) return
      const anchor = renderer.getListScrollTop?.(viewport.current.id)
      if (!anchor) return
      const offset = anchorOffset(anchor)
      setMetrics(previous => previous.offset === offset ? previous : { ...previous, offset })
    }}
      style={{ flexGrow: 1, flexBasis: 0, minWidth: 0, minHeight: 0, margin: 8 }}>
        {/* Window changes are scrolling, not removals. Never animate recycled
            rows out or replay pickup animations as they enter the viewport. */}
        <AnimatePresence key={start} initial={false}>{children.slice(start, Math.max(start + 1, range.end))}</AnimatePresence>
    </virtual-list>
    <div ref={track} testId={`layer-scrollbar:${id}`}
      onMouseDown={event => {
        if (event.button !== 0) return
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
        // Mouse-up can occur outside this track or even outside the window.
        if (event.pressedButton !== 0) { drag.current = null; return }
        if (drag.current) scroll(drag.current.offset + ((event.y ?? 0) - drag.current.y) * maximum / Math.max(1, travel))
      }}
      onMouseUp={() => { drag.current = null }}
      style={{ width: 12, marginTop: 8, marginBottom: 8, flexShrink: 0, position: "relative", cursor: maximum ? "pointer" : "default" }}>
      {maximum > 0 ? <div style={{ position: "absolute", left: 3, width: 6,
        top: Math.min(maximum, metrics.offset) / maximum * travel, height: thumb,
        borderRadius: 3, backgroundColor: colors.tertiary, pointerEvents: "none" }} /> : null}
    </div>
  </div>
}
