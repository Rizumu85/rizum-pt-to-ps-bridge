import { afterEach, describe, expect, it, vi } from "vitest"
import { createPointerFollower, createRowBoundsCache } from "./drag-feedback"

afterEach(() => vi.useRealTimers())

describe("drag feedback work bounds", () => {
  it("reads a stationary row once, but refreshes after layout changes and on release", () => {
    const read = vi.fn(() => ({ x: 0, y: 20, width: 200, height: 36 }))
    const cache = createRowBoundsCache(read)
    for (let i = 0; i < 100; i++) cache.read(1)
    expect(read).toHaveBeenCalledTimes(1)
    cache.invalidate()
    read.mockReturnValue({ x: 0, y: 5, width: 200, height: 36 })
    expect(cache.read(1)?.y).toBe(5)
    expect(read).toHaveBeenCalledTimes(2)
    cache.read(1, true)
    expect(read).toHaveBeenCalledTimes(3)
  })

  it("does not retain missing native bounds", () => {
    const read = vi.fn<() => { x: number; y: number; width: number; height: number } | null>(() => null)
    const cache = createRowBoundsCache(read)
    expect(cache.read(1)).toBeNull()
    read.mockReturnValue({ x: 0, y: 20, width: 200, height: 36 })
    expect(cache.read(1)).not.toBeNull()
  })

  it("coalesces a burst into the latest position and ignores duplicate coordinates", () => {
    vi.useFakeTimers()
    const write = vi.fn()
    const follow = createPointerFollower({ x: 0, y: 0 }, write)
    for (let i = 1; i <= 100; i++) follow.move(i, i)
    expect(write).not.toHaveBeenCalled()
    vi.advanceTimersByTime(8)
    expect(write).toHaveBeenCalledExactlyOnceWith({ x: 100, y: 100 })
    for (let i = 0; i < 100; i++) follow.move(100, 100)
    vi.advanceTimersByTime(8)
    expect(write).toHaveBeenCalledTimes(1)
    follow.dispose()
  })

  it("flushes release immediately and never writes after unmount", () => {
    vi.useFakeTimers()
    const write = vi.fn()
    const follow = createPointerFollower({ x: 0, y: 0 }, write)
    follow.move(80, 100)
    follow.flush()
    expect(write).toHaveBeenCalledExactlyOnceWith({ x: 80, y: 100 })
    follow.move(90, 110)
    follow.dispose()
    follow.move(150, 200)
    vi.runAllTimers()
    expect(write).toHaveBeenCalledTimes(1)
  })
})
