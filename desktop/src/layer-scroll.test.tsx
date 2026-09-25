import { describe, expect, it, vi } from "vitest"
import { createTestRoot } from "./test-root"
import { LayerScroll } from "./layer-scroll"

async function setup() {
  const root = createTestRoot({ width: 400, height: 260 })
  root.render(<div style={{ height: 240, display: "flex", flexDirection: "column" }}>
    <LayerScroll id="test" layoutKey="fixed" rowCount={30}>
      {Array.from({ length: 30 }, (_, i) => <div key={i} style={{ height: 32, flexShrink: 0 }}><text>Layer {i}</text></div>)}
    </LayerScroll>
  </div>)
  await new Promise(resolve => setTimeout(resolve, 300))
  root.renderer.flush()
  const track = root.renderer.getElementBounds(root.renderer.findByTestId("layer-scrollbar:test")!.id)!
  const viewport = root.renderer.findByTestId("layer-scroll:test")!.id
  return { root, track, viewport }
}

describe("layer scrolling", () => {
  it("does not measure layout on hover or restart geometry timers after scrolling", async () => {
    const { root } = await setup()
    const read = vi.spyOn(root.renderer, "getElementBounds")
    try {
      root.renderer.dispatchMouseMove(100, 100)
      root.renderer.dispatchScrollWheel(100, 100, 0, -40)
      root.renderer.flush()
      await new Promise(resolve => setTimeout(resolve, 300))
      expect(read).not.toHaveBeenCalled()
    } finally { read.mockRestore(); root.unmount() }
  })

  it("does not resume a thumb drag after releasing outside the track", async () => {
    const { root, track, viewport } = await setup()
    try {
      const x = track.x + track.width / 2
      root.renderer.nativeSimulateMouseDown(x, track.y + 12)
      root.renderer.nativeSimulateMouseMove(x, track.y + 60, 0)
      root.renderer.nativeSimulateMouseUp(100, 100)
      const before = root.renderer.getListScrollTop(viewport)!
      root.renderer.nativeSimulateMouseMove(x, track.y + 150)
      expect(root.renderer.getListScrollTop(viewport)).toEqual(before)
      expect(before[0]).toBeGreaterThan(0)
    } finally { root.unmount() }
  })
})
