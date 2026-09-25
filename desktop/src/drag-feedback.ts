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

/** Tilt angles the carried cards can show, in whole degrees; clockwise is positive. */
export const tiltSteps = [-6, -5, -4, -3, -2, -1, 0, 1, 2, 3, 4, 5, 6]

/**
 * The carried cards lean into horizontal motion, the way a card held at its
 * top swings while it travels, and straighten once the pointer rests. The
 * angle eases toward a target set by recent pointer speed, and apply() only
 * runs when the shown whole-degree step changes, so continuous drags cost a
 * native update per degree, not per move.
 */
export function createTilt(apply: (step: number) => void, now = () => performance.now()) {
  let angle = 0
  let target = 0
  let velocity = 0
  let last: { x: number; t: number } | null = null
  let shown = 0
  let timer: ReturnType<typeof setTimeout> | null = null
  let disposed = false
  const tick = () => {
    timer = null
    if (disposed) return
    // A pointer that stopped reporting has stopped moving.
    if (last && now() - last.t > 60) {
      target = 0
      velocity = 0
    }
    angle += (target - angle) * 0.3
    if (target === 0 && Math.abs(angle) < 0.25) angle = 0
    const step = Math.max(-6, Math.min(6, Math.round(angle)))
    if (step !== shown) {
      shown = step
      apply(step)
    }
    if (angle !== 0 || target !== 0) timer = setTimeout(tick, 16)
  }
  return {
    sample(x: number) {
      if (disposed) return
      const t = now()
      if (last && t > last.t) velocity = velocity * 0.6 + ((x - last.x) / (t - last.t)) * 0.4
      last = { x, t }
      // About 1.5px per ms, a brisk drag, reaches the full lean.
      target = Math.max(-6, Math.min(6, velocity * 4))
      if (timer === null) timer = setTimeout(tick, 16)
    },
    dispose() {
      disposed = true
      if (timer !== null) clearTimeout(timer)
      timer = null
    },
  }
}
