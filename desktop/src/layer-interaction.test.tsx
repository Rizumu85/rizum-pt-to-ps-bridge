import path from "node:path"
import { connectTest, type TreeNode } from "@gpuix/react/automation"
import { createTestRoot } from "./test-root"
import { describe, expect, it, vi } from "vitest"
import { BridgeApp, initialWindowHeight } from "./bridge-app"
import { loadBridgeSession } from "./transport"
import { colors, metrics } from "./theme"
import type { BridgeState } from "./model"

const fixtures = path.resolve(import.meta.dirname, "../test-fixtures")

async function setup(nested = false, childCount = 0, synchronousInput = true) {
  const session = await loadBridgeSession({
    painterSnapshot: path.join(fixtures, "painter_snapshot.json"),
    photoshopDocument: path.join(fixtures, "photoshop_document.psd"),
  })
  if (childCount) {
    const group = session.state.painter.find(node => node.kind === "group")!
    group.children = Array.from({ length: childCount }, (_, index) => ({
      ...group.children![0], id: `large-child-${index}`, name: `Large child ${index}`,
    }))
  }
  if (nested) {
    const group = session.state.painter.find(node => node.kind === "group")!
    group.children = [{ ...group, id: "nested", name: "Nested", children: group.children }]
  }
  const root = createTestRoot({ width: 700, height: 560 }, synchronousInput)
  const app = await connectTest(root.renderer)
  const apply = vi.fn(async (_state: BridgeState) => ({ session: null, message: "Applied", failed: false }))
  root.render(<BridgeApp session={session} onApply={apply} onConnectPhotoshop={async () => null} />)
  root.renderer.flush()
  return { root, app, apply, close: async () => { root.unmount(); await app.close() } }
}

function dropMarks(node: TreeNode | null): number {
  if (!node) return 0
  return Number(node.testId?.startsWith("drop-indicator:") ?? false)
    + (node.children ?? []).reduce((sum, child) => sum + dropMarks(child), 0)
}

describe("layer tree interaction", () => {
  it.each([
    ["Paint edit", "Working"],
    ["Retouch group", "Working"],
    ["MaskOut", "Retouch group"],
    ["Working", "Retouch group"],
  ])("commits %s to %s when native input arrives before a React frame", async (sourceName, targetName) => {
    const { app, root, apply, close } = await setup(false, 0, false)
    try {
      const source = await app.getByText(sourceName).bounds()
      const target = await app.getByText(targetName).bounds()
      root.renderer.nativeSimulateMouseDown(source.x + 4, source.y + 4)
      root.renderer.dispatchMouseMove(target.x + 4, target.y + 4, 0)
      root.renderer.nativeSimulateMouseUp(target.x + 4, target.y + 4)
      await vi.waitFor(async () => expect(await app.getByText("Pending").count()).toBe(1))
      await app.getByTestId("apply-mapping").click()
      await vi.waitFor(() => expect(apply).toHaveBeenCalledOnce())
      expect(apply.mock.calls[0][0].mappings).toHaveLength(1)
    } finally { await close() }
  })

  it("keeps the carried card beside the pointer across layer and folder rows", async () => {
    const { app, root, close } = await setup()
    const wait = (ms: number) => new Promise(resolve => setTimeout(resolve, ms))
    try {
      await app.mouse.down(app.getByText("Paint edit"))
      for (const id of ["photoshop:ps:101", "substance_painter:sp-lighten", "substance_painter:sp-working", "substance_painter:sp-recolor"]) {
        const row = await app.getByTestId(`layer-row:${id}`).bounds()
        const x = row.x + row.width * 0.3, y = row.y + row.height * 0.7
        await app.mouse.move({ x, y }, { pressedButton: 0 })
        root.renderer.flush()
        await wait(30)
        root.renderer.flush()
        const card = await app.getByTestId("drag-preview").bounds()
        // Off the pointer's lower right, or its lower left where the right would leave the window.
        const right = Math.abs(card.x - (x + 14)) < 12
        const left = Math.abs(card.x + card.width - (x - 14)) < 12
        expect(right || left).toBe(true)
        expect(Math.abs(card.y - (y + 10))).toBeLessThan(3)
      }
    } finally { await close() }
  })

  it.each(["photoshop:ps:100", "photoshop:ps:103"])("picks up %s when the first move lands in the panel gutter", async id => {
    const { app, root, close } = await setup()
    try {
      const box = await app.getByTestId(`layer-thumbnail:${id}`).bounds()
      root.renderer.nativeSimulateMouseDown(box.x + box.width / 2, box.y + box.height / 2)
      root.renderer.dispatchMouseMove(350, 500, 0)
      root.renderer.flush()
      expect(await app.getByTestId("drag-preview").count()).toBe(1)
      root.renderer.nativeSimulateMouseUp(350, 500)
      await app.clock.fastForward(400)
      root.renderer.flush()
      root.renderer.dispatchNativeEvents()
      await vi.waitFor(async () => expect(await app.getByTestId("drag-preview").count()).toBe(0))
      expect(await app.getByText("Pending").count()).toBe(0)
    } finally { await close() }
  })

  it.each(["photoshop:ps:100", "photoshop:ps:103"])("picks up %s on the first threshold-crossing move without waiting for animation", async id => {
    const { app, root, close } = await setup()
    try {
      const box = await app.getByTestId(`layer-thumbnail:${id}`).bounds()
      const x = box.x + box.width / 2, y = box.y + box.height / 2
      root.renderer.nativeSimulateMouseDown(x, y)
      expect(await app.getByTestId("drag-preview").count()).toBe(0)
      root.renderer.dispatchMouseMove(x + metrics.dragThreshold + 1, y, 0)
      root.renderer.flush()
      const pickedUp = await app.getByTestId("drag-preview").bounds()
      expect(pickedUp.x).toBeGreaterThan(x + metrics.dragThreshold)
      expect(pickedUp.y).toBeGreaterThan(y)
      expect(root.renderer.findByTestId(`layer-row:${id}`)?.style.opacity).toBe(0.65)
    } finally { await close() }
  })

  it.each([
    ["Paint edit", "Working", "Locator", "substance_painter:sp-locator", "layer"],
    ["Retouch group", "Working", "Locator", "substance_painter:sp-locator", "group"],
    ["MaskOut", "Retouch group", "Paint edit", "photoshop:ps:100", "PaintLayer"],
    ["Working", "Retouch group", "Paint edit", "photoshop:ps:100", "GroupLayer"],
  ])("repositions staged %s on the destination side without duplicating its mapping", async (source, first, second, targetId, kind) => {
    const { app, root, apply, close } = await setup()
    try {
      for (const target of [first, second]) {
        await app.mouse.down(app.getByText(source))
        await app.mouse.move(app.getByText(target), { pressedButton: 0 })
        expect(dropMarks((await app.call("getTree", {})).tree)).toBe(1)
        await app.mouse.up(app.getByText(target))
        await app.clock.fastForward(400)
        root.renderer.flush()
        root.renderer.dispatchNativeEvents()
        await vi.waitFor(async () => expect(await app.getByTestId("drag-preview").count()).toBe(0))
        expect(await app.getByText(source).count()).toBe(1)
      }
      await app.getByTestId("apply-mapping").click()
      await vi.waitFor(() => expect(apply).toHaveBeenCalledOnce())
      const state = apply.mock.calls[0][0]
      expect(state.mappings).toHaveLength(1)
      expect(state.mappings[0]).toMatchObject({ targetId, placement: "after", source: { kind } })
    } finally { await close() }
  })

  it("culls descendants inside large folders and restores compact layout after collapse", async () => {
    const { app, root, close } = await setup(false, 160)
    try {
      await new Promise(resolve => setTimeout(resolve, 300))
      const list = root.renderer.findByTestId("layer-scroll:painter")!.id
      expect(root.renderer.findByTestId("layer-row:large-child-159")).toBeUndefined()
      root.renderer.scrollToItem(list, 162)
      root.renderer.flush()
      root.renderer.dispatchNativeEvents()
      await vi.waitFor(() => {
        root.renderer.flush()
        root.renderer.dispatchNativeEvents()
        const last = root.renderer.findByTestId("layer-row:large-child-159")
        expect(last && root.renderer.getElementBounds(last.id)).toBeTruthy()
      })
      root.renderer.scrollToItem(list, 0)
      root.renderer.flush()
      root.renderer.dispatchNativeEvents()
      await vi.waitFor(async () => expect(await app.getByTestId("layer-toggle:substance_painter:sp-working").count()).toBe(1))
      await app.getByTestId("layer-toggle:substance_painter:sp-working").click()
      await app.clock.fastForward(400)
      root.renderer.flush()
      root.renderer.dispatchNativeEvents()
      await vi.waitFor(async () => expect(await app.getByTestId("layer-row:large-child-0").count()).toBe(0))
      const folder = await app.getByTestId("layer-row:substance_painter:sp-working").bounds()
      const following = await app.getByText("LC_BaseTextures").bounds()
      expect(following.y - folder.y).toBeLessThan(folder.height * 2)
      await app.getByTestId("layer-toggle:substance_painter:sp-working").click()
      await app.clock.fastForward(400)
      root.renderer.flush()
      root.renderer.dispatchNativeEvents()
      expect(await app.getByTestId("layer-row:large-child-0").count()).toBe(1)
      root.renderer.scrollToItem(list, 162)
      root.renderer.flush()
      await vi.waitFor(() => {
        root.renderer.flush()
        root.renderer.dispatchNativeEvents()
        const last = root.renderer.findByTestId("layer-row:large-child-159")
        expect(last && root.renderer.getElementBounds(last.id)).toBeTruthy()
      })
    } finally { await close() }
  })
  it("fills the viewport after a thumb drag jumps past the mounted rows", async () => {
    const { root, close } = await setup(false, 60)
    const settle = async () => {
      for (let i = 0; i < 4; i++) {
        root.renderer.flush()
        root.renderer.dispatchNativeEvents()
        await new Promise(resolve => setTimeout(resolve, 15))
      }
    }
    try {
      await new Promise(resolve => setTimeout(resolve, 300))
      await settle()
      const track = root.renderer.getElementBounds(root.renderer.findByTestId("layer-scrollbar:painter")!.id)!
      const bottomEdge = track.y + track.height
      const paintedBottom = () => Math.max(0, ...root.renderer.findByType("div")
        .filter(element => element.testId?.startsWith("layer-row:"))
        .map(element => root.renderer.getElementBounds(element.id))
        .filter(box => box && box.x < track.x && box.y < bottomEdge)
        .map(box => box!.y + box!.height))
      // Wheel far enough that the mounted window no longer holds the top rows.
      for (let step = 0; step < 12; step++) {
        root.renderer.dispatchScrollWheel(track.x - 80, track.y + 80, 0, -90)
        await settle()
      }
      const x = track.x + track.width / 2
      root.renderer.nativeSimulateMouseDown(x, track.y + 4)
      for (const y of [track.y + 4, track.y + 60, track.y + 120]) {
        root.renderer.nativeSimulateMouseMove(x, y, 0)
        await settle()
        expect(paintedBottom()).toBeGreaterThanOrEqual(bottomEdge - 1)
      }
      root.renderer.nativeSimulateMouseUp(x, track.y + 120)
    } finally { await close() }
  })
  it("shows only the actual drag target and clears it on Escape", async () => {
    const { app, root, close } = await setup()
    try {
      await app.mouse.down(app.getByText("Paint edit"))
      await app.mouse.move(app.getByText("Lighten"), { pressedButton: 0 })
      expect(dropMarks((await app.call("getTree", {})).tree)).toBe(1)
      expect(await app.getByTestId("drop-indicator:substance_painter:sp-lighten").count()).toBe(1)
      expect(root.renderer.findByTestId("layer-row:photoshop:ps:100")?.style.opacity).toBe(0.65)
      root.renderer.simulateKeystrokes("escape")
      root.renderer.dispatchNativeEvents()
      root.renderer.flush()
      expect(dropMarks((await app.call("getTree", {})).tree)).toBe(0)
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

  it("aims by position: a folder's upper edge places above it, its body inside, a layer's halves above or below", async () => {
    const { app, root, close } = await setup()
    const at = async (testId: string, share: number) => {
      const box = await app.getByTestId(testId).bounds()
      return { x: box.x + box.width / 2, y: box.y + box.height * share }
    }
    const line = async (testId: string) => (await app.getByTestId(testId).bounds()).y
    try {
      await app.mouse.down(app.getByText("Paint edit"))
      await app.mouse.move(await at("layer-row:substance_painter:sp-working", 0.7), { pressedButton: 0 })
      expect(root.renderer.findByTestId("drop-indicator:substance_painter:sp-working")?.style.borderWidth).toBe(1)
      const working = await app.getByTestId("layer-row:substance_painter:sp-working").bounds()
      await app.mouse.move(await at("layer-row:substance_painter:sp-working", 0.1), { pressedButton: 0 })
      expect(root.renderer.findByTestId("drop-indicator:substance_painter:sp-working")?.style.borderWidth).toBeUndefined()
      expect(Math.abs(await line("drop-indicator:substance_painter:sp-working") - working.y)).toBeLessThan(2)
      const lighten = await app.getByTestId("layer-row:substance_painter:sp-lighten").bounds()
      await app.mouse.move(await at("layer-row:substance_painter:sp-lighten", 0.2), { pressedButton: 0 })
      expect(Math.abs(await line("drop-indicator:substance_painter:sp-lighten") - lighten.y)).toBeLessThan(2)
      await app.mouse.move(await at("layer-row:substance_painter:sp-lighten", 0.75), { pressedButton: 0 })
      expect(Math.abs(await line("drop-indicator:substance_painter:sp-lighten") - (lighten.y + lighten.height - 6))).toBeLessThan(2)
      root.renderer.simulateKeystrokes("escape")
      root.renderer.dispatchNativeEvents()
    } finally { await close() }
  })

  it("drops above the first row of a list, which only the upper half can reach", async () => {
    const { app, root, close } = await setup()
    try {
      const top = await app.getByTestId("layer-row:substance_painter:sp-locator").bounds()
      await app.mouse.down(app.getByText("Paint edit"))
      await app.mouse.move({ x: top.x + top.width / 2, y: top.y + top.height * 0.2 }, { pressedButton: 0 })
      await app.mouse.up({ x: top.x + top.width / 2, y: top.y + top.height * 0.2 })
      await app.clock.fastForward(400)
      root.renderer.flush()
      root.renderer.dispatchNativeEvents()
      const dropped = await app.getByTestId("layer-row:photoshop:ps:100").bounds()
      const locator = await app.getByTestId("layer-row:substance_painter:sp-locator").bounds()
      expect(dropped.x).toBeGreaterThan(top.x - 1)
      expect(dropped.y).toBeLessThan(locator.y)
      expect(await app.getByText("Pending").count()).toBe(1)
    } finally { await close() }
  })

  it("drops where the line shows when released in the list margin above the first row", async () => {
    const { app, root, close } = await setup()
    try {
      const top = await app.getByTestId("layer-row:substance_painter:sp-locator").bounds()
      await app.mouse.down(app.getByText("Paint edit"))
      await app.mouse.move({ x: top.x + top.width / 2, y: top.y + top.height * 0.2 }, { pressedButton: 0 })
      // Out of the row, into the margin above it: the line stays, so the drop does.
      await app.mouse.move({ x: top.x + top.width / 2, y: top.y - 4 }, { pressedButton: 0 })
      await app.mouse.up({ x: top.x + top.width / 2, y: top.y - 4 })
      await app.clock.fastForward(400)
      root.renderer.flush()
      root.renderer.dispatchNativeEvents()
      expect(await app.getByText("Pending").count()).toBe(1)
      const dropped = await app.getByTestId("layer-row:photoshop:ps:100").bounds()
      const locator = await app.getByTestId("layer-row:substance_painter:sp-locator").bounds()
      expect(dropped.y).toBeLessThan(locator.y)
    } finally { await close() }
  })

  it("cancels a drop released between the panels, where no line shows", async () => {
    const { app, root, close } = await setup()
    try {
      const top = await app.getByTestId("layer-row:substance_painter:sp-locator").bounds()
      const panel = await app.getByTestId("layer-panel:painter").bounds()
      await app.mouse.down(app.getByText("Paint edit"))
      await app.mouse.move({ x: top.x + top.width / 2, y: top.y + top.height * 0.2 }, { pressedButton: 0 })
      await app.mouse.move({ x: panel.x - 6, y: top.y }, { pressedButton: 0 })
      root.renderer.flush()
      expect(dropMarks(root.renderer.toJSON() as TreeNode)).toBe(0)
      await app.mouse.up({ x: panel.x - 6, y: top.y })
      await app.clock.fastForward(400)
      root.renderer.flush()
      expect(await app.getByText("Pending").count()).toBe(0)
    } finally { await close() }
  })

  it("drops above a layer staged at the top, and applies that order", async () => {
    const { app, root, apply, close } = await setup()
    const dropOnUpperHalf = async (source: string, targetId: string) => {
      const row = await app.getByTestId(`layer-row:${targetId}`).bounds()
      const point = { x: row.x + row.width / 2, y: row.y + row.height * 0.2 }
      await app.mouse.down(app.getByText(source))
      await app.mouse.move(point, { pressedButton: 0 })
      await app.mouse.up(point)
      await app.clock.fastForward(400)
      root.renderer.flush()
      root.renderer.dispatchNativeEvents()
    }
    try {
      await dropOnUpperHalf("Paint edit", "substance_painter:sp-locator")
      await dropOnUpperHalf("Color pass", "photoshop:ps:100")
      const first = await app.getByTestId("layer-row:photoshop:ps:101").bounds()
      const second = await app.getByTestId("layer-row:photoshop:ps:100").bounds()
      const locator = await app.getByTestId("layer-row:substance_painter:sp-locator").bounds()
      expect(first.y).toBeLessThan(second.y)
      expect(second.y).toBeLessThan(locator.y)
      await app.getByTestId("apply-mapping").click()
      await vi.waitFor(() => expect(apply).toHaveBeenCalledOnce())
      const mappings = apply.mock.calls[0][0].mappings
      expect(mappings.map((mapping: { sourceId: string }) => mapping.sourceId)).toEqual(["photoshop:ps:101", "photoshop:ps:100"])
      expect(mappings.every((mapping: { targetId: string; placement: string }) =>
        mapping.targetId === "substance_painter:sp-locator" && mapping.placement === "before")).toBe(true)
    } finally { await close() }
  })

  it("does not dim a pressed row before the drag threshold or leave insertion lines after clicks", async () => {
    const { app, root, close } = await setup()
    try {
      await app.mouse.down(app.getByText("Paint edit"))
      expect(root.renderer.findByTestId("layer-row:photoshop:ps:100")?.style.opacity ?? 1).toBe(1)
      await app.mouse.up(app.getByText("Paint edit"))
      await app.getByText("Working").hover()
      expect(dropMarks((await app.call("getTree", {})).tree)).toBe(0)
      await app.getByTestId("layer-toggle:substance_painter:sp-working").click()
      expect(root.renderer.findByTestId("layer-row:substance_painter:sp-working")?.style.opacity ?? 1).toBe(1)
      await app.getByText("Retouch group").hover()
      expect(dropMarks((await app.call("getTree", {})).tree)).toBe(0)
    } finally { await close() }
  })

  it("carries a labelled chip with the pointer and says where a drop is refused", async () => {
    const { app, root, close } = await setup()
    try {
      expect(root.renderer.findByTestId("layer-row:photoshop:ps:100")?.style.cursor).toBe("grab")
      await app.mouse.down(app.getByText("Paint edit"))
      await app.mouse.move(app.getByText("Lighten"), { pressedButton: 0 })
      expect(await app.getByTestId("drag-preview").count()).toBe(1)
      // The source row and the carried card.
      expect(await app.getByText("Paint edit").count()).toBe(2)
      const lighten = await app.getByTestId("layer-row:substance_painter:sp-lighten").bounds()
      const chip = await app.getByTestId("drag-preview").bounds()
      expect(chip.y).toBeGreaterThan(lighten.y)
      expect(root.renderer.findByTestId("layer-row:substance_painter:sp-lighten")?.style.cursor).toBe("grabbing")
      await app.mouse.move(app.getByText("Color pass"), { pressedButton: 0 })
      expect(root.renderer.findByTestId("layer-row:photoshop:ps:101")?.style.cursor).toBe("no-drop")
      await app.mouse.move(app.getByText("Lighten"), { pressedButton: 0 })
      await app.mouse.up(app.getByText("Lighten"))
      await app.clock.fastForward(400)
      root.renderer.flush()
      root.renderer.dispatchNativeEvents()
      await vi.waitFor(async () => expect(await app.getByTestId("drag-preview").count()).toBe(0))
    } finally { await close() }
  })

  it("settles the cards back into their row when a drag does not land", async () => {
    const { app, root, close } = await setup()
    try {
      const home = await app.getByTestId("layer-row:photoshop:ps:100").bounds()
      await app.mouse.down(app.getByText("Paint edit"))
      await app.mouse.move(app.getByText("Mask cleanup"), { pressedButton: 0 })
      const carried = await app.getByTestId("drag-preview").bounds()
      await app.mouse.up(app.getByText("Mask cleanup"))
      await app.clock.fastForward(400)
      root.renderer.flush()
      const settled = await app.getByTestId("drag-preview").bounds()
      expect(Math.abs(settled.y - home.y)).toBeLessThan(Math.abs(carried.y - home.y))
      expect(Math.abs(settled.y - home.y)).toBeLessThan(4)
      expect(settled.width).toBeGreaterThan(carried.width)
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

  it("ends a held drag when undo replaces its source tree", async () => {
    const { app, root, close } = await setup()
    try {
      await app.mouse.down(app.getByText("Paint edit"))
      await app.mouse.move(app.getByText("Lighten"), { pressedButton: 0 })
      await app.mouse.up(app.getByText("Lighten"))
      await app.clock.fastForward(400)
      root.renderer.dispatchNativeEvents()
      await app.mouse.down(app.getByText("Mask cleanup"))
      await app.mouse.move(app.getByText("Recolor"), { pressedButton: 0 })
      root.renderer.simulateKeystrokes("ctrl-z")
      root.renderer.dispatchNativeEvents()
      await app.clock.fastForward(400)
      root.renderer.dispatchNativeEvents()
      await app.mouse.move(app.getByText("Lighten"), { pressedButton: 0 })
      expect(dropMarks((await app.call("getTree", {})).tree)).toBe(0)
      await vi.waitFor(async () => expect(await app.getByTestId("drag-preview").count()).toBe(0))
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
    expect(initialWindowHeight(state)).toBe(metrics.minInitialHeight)
    const long: BridgeState = { ...state, painter: Array.from({ length: 40 }, (_, index) => ({ ...state.painter[0], id: `row-${index}` })) }
    expect(initialWindowHeight(long)).toBe(metrics.maxInitialHeight)
  })
})
