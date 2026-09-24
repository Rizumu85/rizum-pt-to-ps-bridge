import path from "node:path"
import { connectTest, type TreeNode } from "@gpuix/react/automation"
import { createTestRoot } from "./test-root"
import { describe, expect, it, vi } from "vitest"
import { BridgeApp, initialWindowHeight } from "./bridge-app"
import { loadBridgeSession } from "./transport"
import { colors, metrics } from "./theme"
import type { BridgeState } from "./model"

const fixtures = path.resolve(import.meta.dirname, "../test-fixtures")

async function setup(nested = false) {
  const session = await loadBridgeSession({
    painterSnapshot: path.join(fixtures, "painter_snapshot.json"),
    photoshopDocument: path.join(fixtures, "photoshop_document.psd"),
  })
  if (nested) {
    const group = session.state.painter.find(node => node.kind === "group")!
    group.children = [{ ...group, id: "nested", name: "Nested", children: group.children }]
  }
  const root = createTestRoot({ width: 700, height: 560 })
  const app = await connectTest(root.renderer)
  root.render(<BridgeApp session={session} onApply={async () => ({ session: null, message: "Applied", failed: false })} onConnectPhotoshop={async () => null} />)
  root.renderer.flush()
  return { root, app, close: async () => { root.unmount(); await app.close() } }
}

function insertionLines(node: TreeNode | null): number {
  if (!node) return 0
  return Number(node.testId?.startsWith("drop-indicator:") ?? false)
    + (node.children ?? []).reduce((sum, child) => sum + insertionLines(child), 0)
}

describe("layer tree interaction", () => {
  it("shows only the actual drag target and clears it on Escape", async () => {
    const { app, root, close } = await setup()
    try {
      await app.mouse.down(app.getByText("Paint edit"))
      await app.mouse.move(app.getByText("Lighten"), { pressedButton: 0 })
      expect(insertionLines((await app.call("getTree", {})).tree)).toBe(1)
      expect(await app.getByTestId("drop-indicator:substance_painter:sp-lighten").count()).toBe(1)
      expect(root.renderer.findByTestId("layer-row:photoshop:ps:100")?.style.opacity).toBe(0.65)
      root.renderer.simulateKeystrokes("escape")
      root.renderer.dispatchNativeEvents()
      root.renderer.flush()
      expect(insertionLines((await app.call("getTree", {})).tree)).toBe(0)
      await app.mouse.up(app.getByText("Lighten"))
      expect(await app.getByText("Pending").count()).toBe(0)
    } finally { await close() }
  })

  it("hover highlights only the row under the pointer, never its folders", async () => {
    const { app, root, close } = await setup(true)
    try {
      await app.getByText("Lighten").hover()
      expect(root.renderer.findByTestId("layer-row:substance_painter:sp-lighten")?.style.backgroundColor).toBe(colors.controlHover)
      for (const folder of ["layer-group:nested", "layer-group:substance_painter:sp-working"]) {
        expect(root.renderer.findByTestId(folder)?.style.backgroundColor).toBeUndefined()
      }
      expect(root.renderer.findByTestId("layer-row:substance_painter:sp-working")?.style.backgroundColor).toBeUndefined()
    } finally { await close() }
  })

  it("frames a folder drop target and draws a line for a layer target", async () => {
    const { app, root, close } = await setup()
    try {
      await app.mouse.down(app.getByText("Paint edit"))
      await app.mouse.move(app.getByText("Working"), { pressedButton: 0 })
      expect(root.renderer.findByTestId("drop-indicator:substance_painter:sp-working")?.style.borderWidth).toBe(1)
      await app.mouse.move(app.getByText("Lighten"), { pressedButton: 0 })
      expect(root.renderer.findByTestId("drop-indicator:substance_painter:sp-lighten")?.style.height).toBe(2)
      root.renderer.simulateKeystrokes("escape")
      root.renderer.dispatchNativeEvents()
    } finally { await close() }
  })

  it("does not dim a pressed row before the drag threshold or leave insertion lines after clicks", async () => {
    const { app, root, close } = await setup()
    try {
      await app.mouse.down(app.getByText("Paint edit"))
      expect(root.renderer.findByTestId("layer-row:photoshop:ps:100")?.style.opacity ?? 1).toBe(1)
      await app.mouse.up(app.getByText("Paint edit"))
      await app.getByText("Working").hover()
      expect(insertionLines((await app.call("getTree", {})).tree)).toBe(0)
      await app.getByTestId("layer-toggle:substance_painter:sp-working").click()
      expect(root.renderer.findByTestId("layer-row:substance_painter:sp-working")?.style.opacity ?? 1).toBe(1)
      await app.getByText("Retouch group").hover()
      expect(insertionLines((await app.call("getTree", {})).tree)).toBe(0)
    } finally { await close() }
  })

  it("carries a labelled chip with the pointer and says where a drop is refused", async () => {
    const { app, root, close } = await setup()
    try {
      expect(root.renderer.findByTestId("layer-row:photoshop:ps:100")?.style.cursor).toBe("grab")
      await app.mouse.down(app.getByText("Paint edit"))
      await app.mouse.move(app.getByText("Lighten"), { pressedButton: 0 })
      expect(await app.getByTestId("drag-preview").count()).toBe(1)
      expect(await app.getByText("Paint edit").count()).toBe(2)
      const lighten = await app.getByTestId("layer-row:substance_painter:sp-lighten").bounds()
      const chip = await app.getByTestId("drag-preview").bounds()
      expect(chip.y).toBeGreaterThan(lighten.y)
      expect(root.renderer.findByTestId("layer-row:substance_painter:sp-lighten")?.style.cursor).toBe("grabbing")
      expect(root.renderer.findByTestId("layer-row:photoshop:ps:101")?.style.cursor).toBe("no-drop")
      await app.mouse.up(app.getByText("Lighten"))
      await app.clock.fastForward(400)
      root.renderer.flush()
      root.renderer.dispatchNativeEvents()
      await vi.waitFor(async () => expect(await app.getByTestId("drag-preview").count()).toBe(0))
    } finally { await close() }
  })

  it("flies the chip back to its row when a drag does not land", async () => {
    const { app, root, close } = await setup()
    try {
      const home = await app.getByText("Paint edit").center()
      await app.mouse.down(app.getByText("Paint edit"))
      await app.mouse.move(app.getByText("Mask cleanup"), { pressedButton: 0 })
      const carried = await app.getByTestId("drag-preview").bounds()
      await app.mouse.up(app.getByText("Mask cleanup"))
      await app.clock.fastForward(400)
      root.renderer.flush()
      const settled = await app.getByTestId("drag-preview").bounds()
      expect(Math.abs(settled.y - home.y)).toBeLessThan(Math.abs(carried.y - home.y))
      expect(Math.abs(settled.y - (home.y + 10))).toBeLessThan(20)
      root.renderer.dispatchNativeEvents()
      expect(await app.getByTestId("drag-preview").count()).toBe(0)
      expect(await app.getByText("Pending").count()).toBe(0)
    } finally { await close() }
  })

  it("animates rows the pointer moved, while undo swaps them instantly", async () => {
    const { app, root, close } = await setup()
    try {
      await app.mouse.down(app.getByText("Paint edit"))
      await app.mouse.move(app.getByText("Lighten"), { pressedButton: 0 })
      await app.mouse.up(app.getByText("Lighten"))
      await app.clock.fastForward(400)
      root.renderer.flush()
      await vi.waitFor(async () => expect(await app.getByText("Pending").count()).toBe(1))
      root.renderer.simulateKeystrokes("ctrl-z")
      root.renderer.dispatchNativeEvents()
      root.renderer.flush()
      expect(await app.getByText("Pending").count()).toBe(0)
      expect(await app.getByText("Paint edit").count()).toBe(1)
    } finally { await close() }
  })

  it("reserves the status line so the first click does not resize the panels", async () => {
    const { app, close } = await setup()
    try {
      const before = await app.getByTestId("layer-thumbnail:substance_painter:sp-maskout").bounds()
      const status = await app.getByTestId("bridge-status").bounds()
      await app.mouse.down(app.getByText("Paint edit"))
      await app.mouse.up(app.getByText("Paint edit"))
      expect(await app.getByText("1 selected").count()).toBe(1)
      expect((await app.getByTestId("bridge-status").bounds()).y).toBe(status.y)
      expect((await app.getByTestId("layer-thumbnail:substance_painter:sp-maskout").bounds()).y).toBe(before.y)
    } finally { await close() }
  })

  it("aligns sibling folders and layers and indents children exactly one step", async () => {
    const { app, close } = await setup()
    try {
      const layer = await app.getByTestId("layer-thumbnail:substance_painter:sp-maskout").bounds()
      const group = await app.getByTestId("layer-thumbnail:substance_painter:sp-working").bounds()
      const child = await app.getByTestId("layer-thumbnail:substance_painter:sp-lighten").bounds()
      expect(group.x).toBe(layer.x)
      const row = await app.getByTestId("layer-row:substance_painter:sp-working").bounds()
      // Native DPI rounding can quantize fractional logical pixels.
      expect(Math.abs((child.x - group.x) / (row.height / metrics.rowHeight) - 18)).toBeLessThan(1)
    } finally { await close() }
  })

  it("does not invent interactive folder parents for host collections", async () => {
    const { app, close } = await setup()
    try {
      expect(await app.getByText("Painter Stack").count()).toBe(0)
      expect(await app.getByText("Selected Layers").count()).toBe(0)
    } finally { await close() }
  })

  it("fits short sessions and caps long trees at a scrollable initial height", async () => {
    const { state } = await loadBridgeSession({
      painterSnapshot: path.join(fixtures, "painter_snapshot.json"),
    })
    expect(initialWindowHeight(state)).toBe(metrics.minWindowHeight)
    const long: BridgeState = { ...state, painter: Array.from({ length: 40 }, (_, index) => ({ ...state.painter[0], id: `row-${index}` })) }
    expect(initialWindowHeight(long)).toBe(metrics.maxInitialHeight)
  })
})
