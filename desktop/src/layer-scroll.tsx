import { createContext, useEffect, useLayoutEffect, useRef, useState, type ReactNode } from "react"
import { useGpuixRequired, useWindowSize, type PublicInstance } from "@gpuix/react"
import { colors, metrics as themeMetrics } from "./theme"
import { createRowBoundsCache } from "./drag-feedback"

export const RowBoundsContext = createContext<ReturnType<typeof createRowBoundsCache> | null>(null)

export function LayerScroll({ id, renderRow, layoutKey, rowCount }: { id: string; renderRow: (index: number) => ReactNode; layoutKey: unknown; rowCount: number }) {
  const renderer = useGpuixRequired()
  const [rowBounds] = useState(() => createRowBoundsCache(id => renderer.getElementBounds?.(id) ?? null))
  const windowSize = useWindowSize()
  const viewport = useRef<PublicInstance>(null)
  const track = useRef<PublicInstance>(null)
  const drag = useRef<{ y: number; offset: number } | null>(null)
  const [metrics, setMetrics] = useState({ height: 0, total: 0, offset: 0 })
  const [range, setRange] = useState({ start: 0, end: 32 })
  const start = Math.min(range.start, Math.max(0, rowCount - 1))
  useLayoutEffect(() => rowBounds.invalidate(), [rowBounds, layoutKey, windowSize.width, windowSize.height])

  // Native reports only rows the mounted window can lay out, so after a jump
  // (a thumb drag) its endIndex stopped at the old window's edge and the rest
  // of the viewport stayed blank. Rows share one fixed height, so the window
  // follows from the first visible row and the viewport height instead.
  const windowAt = (first: number, height: number) => ({
    start: Math.max(0, first - 8),
    end: first + Math.ceil((height || 24 * themeMetrics.rowHeight) / themeMetrics.rowHeight) + 8,
  })
  const adoptWindow = (next: { start: number; end: number }) =>
    setRange(previous => previous.start === next.start && previous.end === next.end ? previous : next)

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
    rowBounds.invalidate()
    const value = Math.max(0, Math.min(maximum, offset))
    renderer.scrollToItem?.(viewport.current.id, Math.floor(value / themeMetrics.rowHeight), value % themeMetrics.rowHeight)
    adoptWindow(windowAt(Math.floor(value / themeMetrics.rowHeight), metrics.height))
    setMetrics(previous => ({ ...previous, offset: value }))
  }

  return <RowBoundsContext.Provider value={rowBounds}><div
    onScroll={rowBounds.invalidate}
    style={{ display: "flex", flexDirection: "row", flexGrow: 1, flexBasis: 0, minHeight: 0 }}>
    <virtual-list ref={viewport} testId={`layer-scroll:${id}`} itemCount={rowCount} windowStart={start}
      estimatedItemHeight={themeMetrics.rowHeight} overdraw={64} onVisibleRange={event => {
      rowBounds.invalidate()
      const anchor = viewport.current && renderer.getListScrollTop?.(viewport.current.id)
      adoptWindow(windowAt(event.startIndex ?? 0, anchor?.[2] ?? metrics.height))
      if (!anchor) return
      const offset = anchorOffset(anchor)
      setMetrics(previous => previous.offset === offset ? previous : { ...previous, offset })
    }}
      style={{ flexGrow: 1, flexBasis: 0, minWidth: 0, minHeight: 0, margin: 8 }}>
        {/* Scroll recycling is not a layer deletion. Stable row keys preserve
            overlapping rows, and offscreen rows never become React elements. */}
        {Array.from({ length: Math.max(0, Math.min(rowCount, Math.max(start + 1, range.end)) - start) }, (_, offset) => renderRow(start + offset))}
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
  </div></RowBoundsContext.Provider>
}
