import type { ElementBounds } from "@gpuix/react"

// Bounds are stable between layout/scroll changes. Pointer frequency must not
// determine how often we synchronously ask the native UI thread for geometry.
export function createRowBoundsCache(read: (id: number) => ElementBounds | null) {
  const bounds = new Map<number, ElementBounds>()
  return {
    invalidate: () => bounds.clear(),
    read(id: number, fresh = false) {
      if (!fresh && bounds.has(id)) return bounds.get(id)!
      const value = read(id)
      if (value) bounds.set(id, value)
      else bounds.delete(id)
      return value
    },
  }
}

type Point = { x: number; y: number }

export function createPointerFollower(initial: Point, write: (point: Point) => void) {
  let shown = initial
  let latest = initial
  let timer: ReturnType<typeof setTimeout> | null = null
  let disposed = false
  const flush = () => {
    if (timer !== null) clearTimeout(timer)
    timer = null
    if (disposed || (latest.x === shown.x && latest.y === shown.y)) return
    shown = latest
    write(shown)
  }
  return {
    move(x: number, y: number) {
      if (disposed || (latest.x === x && latest.y === y)) return
      latest = { x, y }
      // Bun has no browser RAF here. A bounded 8ms batch keeps only the latest
      // position; drop decisions stay synchronous and never wait for this timer.
      if (timer === null) timer = setTimeout(flush, 8)
    },
    flush,
    dispose() {
      disposed = true
      if (timer !== null) clearTimeout(timer)
      timer = null
    },
  }
}
