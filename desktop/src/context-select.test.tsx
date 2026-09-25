import path from "node:path"

import { connectTest } from "@gpuix/react/automation"
import { createTestRoot } from "./test-root"
import { describe, expect, it, vi } from "vitest"

import { BridgeApp } from "./bridge-app"
import type { BridgeState } from "./model"
import { loadBridgeSession } from "./transport"
import { writeFeaturePsd } from "./test-psd"

const fixtureDir = path.resolve(import.meta.dirname, "../test-fixtures")

describe("Painter context selectors", () => {
  it("selects and transfers a batch with visible pending state, then undoes Reset", async () => {
    const session = await loadBridgeSession({
      painterSnapshot: path.join(fixtureDir, "painter_snapshot.json"),
      photoshopDocument: path.join(fixtureDir, "photoshop_document.psd"),
    })
    const root = createTestRoot({ width: 652, height: 720 })
    const app = await connectTest(root.renderer)
    const apply = vi.fn(async (_state: BridgeState, _context: string) => ({ session: null, message: "Applied", failed: false }))
    const connect = vi.fn(async () => null)
    try {
      root.render(<BridgeApp session={session} onApply={apply} onConnectPhotoshop={connect} />)
      root.renderer.flush()
      await app.getByText("Paint edit").click()
      await app.getByText("Color pass").click({ modifiers: "ctrl" })
      expect(await app.getByText("2 selected").count()).toBe(1)
      await app.mouse.down(app.getByText("Color pass"))
      await new Promise(resolve => setTimeout(resolve, 100))
      await app.mouse.move(app.getByText("Working"), { pressedButton: 0 })
      await new Promise(resolve => setTimeout(resolve, 100))
      await app.mouse.up(app.getByText("Working"))
      expect(await app.getByText("2 pending transfers").count()).toBe(1)
      expect(await app.getByText("Pending").count()).toBe(2)
      root.renderer.simulateKeystrokes("ctrl-z")
      root.renderer.dispatchNativeEvents()
      root.renderer.flush()
      expect(await app.getByText("Pending").count()).toBe(0)
      root.renderer.simulateKeystrokes("ctrl-shift-z")
      root.renderer.dispatchNativeEvents()
      root.renderer.flush()
      expect(await app.getByText("Pending").count()).toBe(2)
      for (const selector of ["Channel:", "Texture Set:"]) {
        await app.getByTestId(`context-select:${selector}`).click()
        await app.getByTestId(`context-option:${selector}:1`).click()
        expect(await app.getByText("Apply or reset pending transfers before changing the target.").count()).toBe(1)
        expect(await app.getByText("Pending").count()).toBe(2)
        expect(await app.getByText("Working").count()).toBe(1)
      }
      // The menu's exit timer is JavaScript time, not the native animation clock.
      await vi.waitFor(async () => {
        expect(await app.getByTestId("context-option:Texture Set::1").count()).toBe(0)
      })
      root.renderer.flush()
      await app.getByTestId("change-photoshop").click()
      expect(connect).not.toHaveBeenCalled()
      expect(await app.getByText("Apply or reset pending transfers before changing documents.").count()).toBe(1)
      await app.getByText("Paint edit").click()
      await app.getByText("Color pass").click({ modifiers: "ctrl" })
      await app.mouse.down(app.getByText("Color pass"))
      await new Promise(resolve => setTimeout(resolve, 100))
      await app.mouse.move(app.getByText("MaskOut"), { pressedButton: 0 })
      await new Promise(resolve => setTimeout(resolve, 100))
      await app.mouse.up(app.getByText("MaskOut"))
      expect(await app.getByText("2 pending transfers").count()).toBe(1)
      await app.getByTestId("action:reset").click()
      expect(await app.getByText("Pending").count()).toBe(0)
      await app.getByTestId("action:undo").click()
      expect(await app.getByText("2 pending transfers").count()).toBe(1)
      await app.getByTestId("apply-mapping").click()
      await vi.waitFor(() => expect(apply).toHaveBeenCalledOnce())
      expect(apply.mock.calls[0][0].mappings).toHaveLength(2)
      expect(apply.mock.calls[0][0].mappings.every(mapping => mapping.targetId === "substance_painter:sp-maskout")).toBe(true)
    } finally { root.unmount(); await app.close() }
  })

  it("collapses groups, removes a row, resets, and maps in the reverse direction", async () => {
    const session = await loadBridgeSession({
      painterSnapshot: path.join(fixtureDir, "painter_snapshot.json"),
      photoshopDocument: path.join(fixtureDir, "photoshop_document.psd"),
    })
    const root = createTestRoot({ width: 652, height: 720 })
    const app = await connectTest(root.renderer)
    const apply = vi.fn(async (_state: BridgeState, _context: string) => ({ session: null, message: "Applied", failed: false }))
    try {
      root.render(<BridgeApp session={session} onApply={apply} onConnectPhotoshop={async () => null} />)
      root.renderer.flush()
      const below = app.getByText("LC_BaseTextures")
      const expandedY = (await below.bounds()).y
      await app.getByTestId("layer-toggle:substance_painter:sp-working").click()
      await app.clock.fastForward(400)
      root.renderer.flush()
      expect((await below.bounds()).y).toBeLessThan(expandedY - 30)
      await app.getByTestId("layer-toggle:substance_painter:sp-working").click()
      await app.clock.fastForward(400)
      root.renderer.flush()
      expect((await below.bounds()).y).toBeCloseTo(expandedY, 0)
      await app.getByTestId("layer-row:substance_painter:sp-locator").hover()
      await app.getByTestId("layer-remove:substance_painter:sp-locator").click()
      expect(await app.getByText("Locator").count()).toBe(1)
      await app.clock.fastForward(400)
      root.renderer.flush()
      root.renderer.dispatchNativeEvents()
      expect(await app.getByText("Locator").count()).toBe(0)
      await app.getByTestId("action:reset").click()
      expect(await app.getByText("Locator").count()).toBe(1)
      await app.mouse.down(app.getByTestId("layer-thumbnail:substance_painter:sp-locator"))
      await new Promise(resolve => setTimeout(resolve, 100))
      await app.mouse.move(app.getByText("Retouch group"), { pressedButton: 0 })
      await new Promise(resolve => setTimeout(resolve, 100))
      await app.mouse.up(app.getByText("Retouch group"))
      await app.getByTestId("apply-mapping").click()
      await vi.waitFor(() => expect(apply).toHaveBeenCalledOnce())
      expect(apply.mock.calls[0][0].mappings[0]).toMatchObject({
        direction: "painter_to_photoshop", placement: "inside", targetId: "photoshop:ps:103",
      })
    } finally { root.unmount(); await app.close() }
  })

  it("drops onto a nested layer without its parent replacing the target", async () => {
    const session = await loadBridgeSession({
      painterSnapshot: path.join(fixtureDir, "painter_snapshot.json"),
      photoshopDocument: path.join(fixtureDir, "photoshop_document.psd"),
    })
    const root = createTestRoot({ width: 652, height: 720 })
    const app = await connectTest(root.renderer)
    const apply = vi.fn(async (_state: BridgeState, _context: string) => ({ session: null, message: "Applied", failed: false }))
    try {
      root.render(<BridgeApp session={session} onApply={apply} onConnectPhotoshop={async () => null} />)
      root.renderer.flush()
      await app.mouse.down(app.getByText("Paint edit"))
      await new Promise(resolve => setTimeout(resolve, 100))
      await app.mouse.move(app.getByText("Lighten"), { pressedButton: 0 })
      await new Promise(resolve => setTimeout(resolve, 100))
      await app.mouse.up(app.getByText("Lighten"))
      await app.getByTestId("apply-mapping").click()
      await vi.waitFor(() => expect(apply).toHaveBeenCalledOnce())
      const mappings = apply.mock.calls[0][0].mappings
      expect(mappings).toHaveLength(1)
      expect(mappings[0].target.externalId).toBe("sp-lighten")
      expect(mappings[0].placement).toBe("after")
    } finally { root.unmount(); await app.close() }
  })

  it("keeps connection errors visible and suppresses duplicate pending requests", async () => {
    const session = await loadBridgeSession({ painterSnapshot: path.join(fixtureDir, "painter_snapshot.json") })
    const root = createTestRoot({ width: 652, height: 484 })
    const app = await connectTest(root.renderer)
    let reject!: (error: Error) => void
    const connect = vi.fn(() => new Promise<null>((_resolve, fail) => { reject = fail }))
    try {
      root.render(<BridgeApp session={session} onApply={async () => ({ session: null, message: "Applied", failed: false })} onConnectPhotoshop={connect} />)
      root.renderer.flush()
      await app.getByTestId("connect-photoshop").click()
      await app.getByTestId("connect-photoshop").click()
      expect(connect).toHaveBeenCalledOnce()
      reject(new Error("Cannot write connection request"))
      await vi.waitFor(async () => expect(await app.getByText("Cannot write connection request").count()).toBe(1))
      const status = await app.getByTestId("bridge-status").bounds()
      const viewport = await app.getByTestId("bridge-root").bounds()
      expect(status.y).toBeGreaterThan(viewport.y)
      expect(status.y + status.height).toBeLessThanOrEqual(viewport.y + viewport.height + 1)
      await app.getByTestId("connect-photoshop").click()
      expect(connect).toHaveBeenCalledTimes(2)
      reject(new Error("Retry failed"))
      await vi.waitFor(async () => expect(await app.getByText("Retry failed").count()).toBe(1))
    } finally { root.unmount(); await app.close() }
  })

  it("maps a layer, undoes, redoes and applies using pointer input", async () => {
    const session = await loadBridgeSession({
      painterSnapshot: path.join(fixtureDir, "painter_snapshot.json"),
      photoshopDocument: path.join(fixtureDir, "photoshop_document.psd"),
    })
    const root = createTestRoot({ width: 652, height: 720 })
    const app = await connectTest(root.renderer)
    const apply = vi.fn(async (_state: BridgeState, _context: string) => ({ session: null, message: "Applied", failed: false }))
    try {
      root.render(<BridgeApp session={session} onApply={apply} onConnectPhotoshop={async () => null} />)
      root.renderer.flush()
      const source = app.getByText("Paint edit")
      const target = app.getByTestId("layer-row:substance_painter:sp-working")
      await app.mouse.down(source)
      await new Promise(resolve => setTimeout(resolve, 100))
      await app.mouse.move(target, { pressedButton: 0 })
      await new Promise(resolve => setTimeout(resolve, 100))
      await app.mouse.up(target)
      await app.getByTestId("action:undo").click()
      await app.getByTestId("action:redo").click()
      await app.getByTestId("apply-mapping").click()
      await vi.waitFor(() => expect(apply).toHaveBeenCalledOnce())
      expect(apply.mock.calls[0][0].mappings).toHaveLength(1)
    } finally { root.unmount(); await app.close() }
  })
  it("scrolls a long Painter stack without moving the Photoshop pane", async () => {
    const session = await loadBridgeSession({ painterSnapshot: path.join(fixtureDir, "painter_snapshot.json") })
    session.state.painter = Array.from({ length: 60 }, (_, index) => ({
      ...session.state.painter[0], id: `long-${index}`, name: `Long layer ${index}`,
      kind: "layer" as const, children: undefined,
    }))
    const testRoot = createTestRoot({ width: 652, height: 484 })
    const app = await connectTest(testRoot.renderer)
    try {
      testRoot.render(<BridgeApp session={session} onApply={async () => ({ session: null, message: "Applied", failed: false })}
        onConnectPhotoshop={async () => null} />)
      testRoot.renderer.flush()
      await new Promise(resolve => setTimeout(resolve, 450))
      const list = testRoot.renderer.findByTestId("layer-scroll:painter")!.id
      const button = await app.getByTestId("connect-photoshop").bounds()
      await app.getByText("Long layer 0").hover()
      await app.getByText("Long layer 0").wheel(0, -160)
      testRoot.renderer.flush()
      const before = testRoot.renderer.getListScrollTop(list)!
      expect(before[0]).toBeGreaterThan(0)
      // Offscreen rows intentionally have no painted bounds in the virtual list.
      const first = testRoot.renderer.findByTestId("layer-row:long-0")!.id
      expect(testRoot.renderer.getElementBounds(first)).toBeNull()
      await app.getByTestId("layer-scrollbar:painter").click()
      testRoot.renderer.flush()
      expect(testRoot.renderer.getListScrollTop(list)![0]).toBeGreaterThan(before[0])
      expect(await app.getByTestId("connect-photoshop").bounds()).toEqual(button)
    } finally {
      testRoot.unmount()
      await app.close()
    }
  })
  it("connects Photoshop from the empty pane", async () => {
    const session = await loadBridgeSession({
      painterSnapshot: path.join(fixtureDir, "painter_snapshot.json"),
    })
    const testRoot = createTestRoot({ width: 652, height: 484 })
    const app = await connectTest(testRoot.renderer)
    const connect = vi.fn(async () => null)
    try {
      testRoot.render(<BridgeApp session={session} onApply={async () => ({ session: null, message: "Applied", failed: false })}
        onConnectPhotoshop={connect} />)
      testRoot.renderer.flush()
      const button = app.getByTestId("connect-photoshop")
      const selector = await app.getByTestId("context-select:Texture Set:").bounds()
      await app.mouse.click({ x: selector.x + selector.width - 15, y: selector.y + selector.height / 2 })
      await app.getByTestId("context-option:Texture Set::1").click()
      await new Promise(resolve => setTimeout(resolve, 300))
      await app.mouse.move(button)
      await app.mouse.down(button)
      await new Promise(resolve => setTimeout(resolve, 150))
      testRoot.renderer.flush()
      await app.mouse.up(button)
      await vi.waitFor(() => expect(connect).toHaveBeenCalledOnce())
      for (const fraction of [0.04, 0.15, 0.35, 0.7, 0.95]) {
        await vi.waitFor(async () => expect(await app.getByText("Connecting...").count()).toBe(0))
        testRoot.renderer.flush()
        const bounds = await button.bounds()
        connect.mockClear()
        await app.mouse.click({ x: bounds.x + bounds.width * fraction, y: bounds.y + bounds.height / 2 })
        await vi.waitFor(() => expect(connect).toHaveBeenCalledOnce())
      }
    } finally {
      testRoot.unmount()
      await app.close()
    }
  })
  it("labels Apply with the pending count and reloads the saved PSD in place", async () => {
    const session = await loadBridgeSession({
      painterSnapshot: path.join(fixtureDir, "painter_snapshot.json"),
      photoshopDocument: path.join(fixtureDir, "photoshop_document.psd"),
    })
    const root = createTestRoot({ width: 652, height: 560 })
    const app = await connectTest(root.renderer)
    const reload = vi.fn(async () => session)
    try {
      root.render(<BridgeApp session={session} onApply={async () => ({ session: null, message: "Applied", failed: false })}
        onConnectPhotoshop={async () => null} onReloadPhotoshop={reload} />)
      root.renderer.flush()
      expect(await app.getByText("Apply").count()).toBe(1)
      await app.mouse.down(app.getByText("Paint edit"))
      await new Promise(resolve => setTimeout(resolve, 100))
      await app.mouse.move(app.getByText("Working"), { pressedButton: 0 })
      await new Promise(resolve => setTimeout(resolve, 100))
      await app.mouse.up(app.getByText("Working"))
      expect(await app.getByText("Apply 1").count()).toBe(1)
      await app.getByTestId("reload-photoshop").click()
      expect(reload).not.toHaveBeenCalled()
      expect(await app.getByText("Apply or reset pending transfers before changing documents.").count()).toBe(1)
      await app.getByTestId("action:reset").click()
      await app.getByTestId("reload-photoshop").click()
      await vi.waitFor(() => expect(reload).toHaveBeenCalledWith(session))
    } finally { root.unmount(); await app.close() }
  })

  it("stays open after Apply and shows Painter's outcome", async () => {
    const session = await loadBridgeSession({
      painterSnapshot: path.join(fixtureDir, "painter_snapshot.json"),
      photoshopDocument: path.join(fixtureDir, "photoshop_document.psd"),
    })
    const refreshed = await loadBridgeSession({
      painterSnapshot: path.join(fixtureDir, "painter_snapshot.json"),
      photoshopDocument: path.join(fixtureDir, "photoshop_document.psd"),
    })
    const root = createTestRoot({ width: 652, height: 560 })
    const app = await connectTest(root.renderer)
    const apply = vi.fn(async () => ({ session: refreshed, message: "Imported 1 Photoshop layer(s) into Painter.", failed: false }))
    try {
      root.render(<BridgeApp session={session} onApply={apply} onConnectPhotoshop={async () => null} />)
      root.renderer.flush()
      await app.mouse.down(app.getByText("Paint edit"))
      await new Promise(resolve => setTimeout(resolve, 100))
      await app.mouse.move(app.getByText("Working"), { pressedButton: 0 })
      await new Promise(resolve => setTimeout(resolve, 100))
      await app.mouse.up(app.getByText("Working"))
      await app.getByTestId("apply-mapping").click()
      await vi.waitFor(async () => expect(await app.getByText("Imported 1 Photoshop layer(s) into Painter.").count()).toBe(1))
      expect(await app.getByText("Pending").count()).toBe(0)
      expect(await app.getByText("Apply").count()).toBe(1)
    } finally { root.unmount(); await app.close() }
  })

  it("warns on the pending row before Apply when Painter changes a blend mode", async () => {
    const session = await loadBridgeSession({
      photoshopDocument: await writeFeaturePsd(),
      painterSnapshot: path.join(fixtureDir, "painter_snapshot.json"),
    })
    const root = createTestRoot({ width: 652, height: 700 })
    const app = await connectTest(root.renderer)
    const drag = async (source: string) => {
      await app.mouse.down(app.getByText(source))
      await new Promise(resolve => setTimeout(resolve, 100))
      await app.mouse.move(app.getByText("Working"), { pressedButton: 0 })
      await new Promise(resolve => setTimeout(resolve, 100))
      await app.mouse.up(app.getByText("Working"))
    }
    try {
      root.render(<BridgeApp session={session} onApply={async () => ({ session: null, message: "Applied", failed: false })}
        onConnectPhotoshop={async () => null} />)
      root.renderer.flush()
      await drag("Glow")
      expect(await app.getByText("Pending · Hard Mix becomes Normal").count()).toBe(1)
      await drag("Paint")
      // Its clipped layer merges into the base, so nothing is reported skipped.
      expect(await app.getByText("skipped").count()).toBe(0)
      expect(await app.getByText("Pending · Hard Mix becomes Normal").count()).toBe(1)
    } finally { root.unmount(); await app.close() }
  })

  it("says under each Photoshop row what will not transfer as-is", async () => {
    const session = await loadBridgeSession({
      photoshopDocument: await writeFeaturePsd(),
      painterSnapshot: path.join(fixtureDir, "painter_snapshot.json"),
    })
    const root = createTestRoot({ width: 652, height: 560 })
    const app = await connectTest(root.renderer)
    try {
      root.render(<BridgeApp session={session} onApply={async () => ({ session: null, message: "Applied", failed: false })} onConnectPhotoshop={async () => null} />)
      root.renderer.flush()
      for (const text of [
        "Clipped · merges into Base", "Merges 1 clipped · Styles not transferred",
        "Adjustment layer · not supported", "Colour fill",
      ]) expect(await app.getByText(text).count()).toBe(1)
    } finally { root.unmount(); await app.close() }
  })

  it("switches the rendered Painter tree with the texture set selector", async () => {
    const session = await loadBridgeSession({
      photoshopDocument: path.join(fixtureDir, "photoshop_document.psd"),
      painterSnapshot: path.join(fixtureDir, "painter_snapshot.json"),
    })
    const testRoot = createTestRoot({ width: 652, height: 484 })
    const app = await connectTest(testRoot.renderer)

    try {
      testRoot.render(
        <BridgeApp
          session={session}
          onApply={async () => ({ session: null, message: "Applied", failed: false })}
          onConnectPhotoshop={async () => null}
        />,
      )
      testRoot.renderer.flush()
      await app.getByTestId("context-select:Channel:").click()
      await app.getByTestId("context-option:Channel::1").click()
      expect(await app.getByText("Working Normals").count()).toBeGreaterThan(0)

      await app.getByTestId("context-select:Texture Set:").click()
      expect(await app.getByText("M_body").count()).toBeGreaterThan(1)
      await app.getByTestId("context-option:Texture Set::1").click()

      expect(await app.getByText("Fabric").count()).toBeGreaterThan(0)
      expect(await app.getByText("Working").count()).toBe(0)
    } finally {
      testRoot.unmount()
      await app.close()
    }
  })

  it("keeps mapping instructions behind the help popover", async () => {
    const session = await loadBridgeSession({
      photoshopDocument: path.join(fixtureDir, "photoshop_document.psd"),
      painterSnapshot: path.join(fixtureDir, "painter_snapshot.json"),
    })
    const testRoot = createTestRoot({ width: 652, height: 484 })
    const app = await connectTest(testRoot.renderer)

    try {
      testRoot.render(
        <BridgeApp
          session={session}
          onApply={async () => ({ session: null, message: "Applied", failed: false })}
          onConnectPhotoshop={async () => null}
        />,
      )
      testRoot.renderer.flush()

      expect(await app.getByText("Drop Photoshop layers here to map").count()).toBe(0)
      expect(await app.getByText("Map between hosts").count()).toBe(0)

      await app.getByTestId("mapping-help-trigger").click()
      expect(await app.getByText("Map between hosts").count()).toBeGreaterThan(0)
      expect(await app.getByText("Group: place inside").count()).toBeGreaterThan(0)
    } finally {
      testRoot.unmount()
      await app.close()
    }
  })

  it("loads a connected Photoshop document into the open mapper", async () => {
    const session = await loadBridgeSession({
      painterSnapshot: path.join(fixtureDir, "painter_snapshot.json"),
    })
    const connected = await loadBridgeSession({
      painterSnapshot: path.join(fixtureDir, "painter_snapshot.json"),
      photoshopDocument: path.join(fixtureDir, "photoshop_document.psd"),
    })
    const testRoot = createTestRoot({ width: 652, height: 484 })
    const app = await connectTest(testRoot.renderer)
    const connect = vi.fn(async () => connected)

    try {
      testRoot.render(
        <BridgeApp
          session={session}
          onApply={async () => ({ session: null, message: "Applied", failed: false })}
          onConnectPhotoshop={connect}
        />,
      )
      testRoot.renderer.flush()

      expect(await app.getByText("No document connected").count()).toBeGreaterThan(0)
      expect(await app.getByText("Locator").count()).toBeGreaterThan(0)
      await app.getByTestId("connect-photoshop").click()
      await vi.waitFor(async () => expect(await app.getByText("Paint edit").count()).toBe(1))
      expect(await app.getByText("No document connected").count()).toBe(0)
      expect(await app.getByText("Locator").count()).toBeGreaterThan(0)
      expect(connect).toHaveBeenCalledWith(session)
    } finally {
      testRoot.unmount()
      await app.close()
    }
  })
})
