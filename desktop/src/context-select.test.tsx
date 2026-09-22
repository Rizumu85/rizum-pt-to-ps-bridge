import path from "node:path"

import { connectTest } from "@gpuix/react/automation"
import { createTestRoot } from "@gpuix/react/testing"
import { describe, expect, it, vi } from "vitest"

import { BridgeApp } from "./main"
import type { BridgeState } from "./model"
import { loadBridgeSession } from "./transport"

const fixtureDir = path.resolve(import.meta.dirname, "../test-fixtures")

describe("Painter context selectors", () => {
  it("collapses groups, removes a row, resets, and maps in the reverse direction", async () => {
    const session = await loadBridgeSession({
      painterSnapshot: path.join(fixtureDir, "painter_snapshot.json"),
      photoshopManifest: path.join(fixtureDir, "photoshop_selection.json"),
    })
    const root = createTestRoot({ width: 652, height: 720 })
    const app = await connectTest(root.renderer)
    const apply = vi.fn(async (_state: BridgeState, _context: string) => "result.json")
    try {
      root.render(<BridgeApp session={session} onApply={apply} onConnectPhotoshop={async () => "unused"} />)
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
      expect(await app.getByText("Locator").count()).toBe(0)
      await app.getByTestId("action:reset").click()
      expect(await app.getByText("Locator").count()).toBe(1)
      await app.mouse.down(app.getByTestId("layer-thumbnail:substance_painter:sp-locator"))
      await new Promise(resolve => setTimeout(resolve, 100))
      await app.mouse.move(app.getByText("Retouch group"), { pressedButton: 0 })
      await new Promise(resolve => setTimeout(resolve, 100))
      await app.mouse.up(app.getByText("Retouch group"))
      await app.getByTestId("action:check").click()
      await vi.waitFor(() => expect(apply).toHaveBeenCalledOnce())
      expect(apply.mock.calls[0][0].mappings[0]).toMatchObject({
        direction: "painter_to_photoshop", placement: "inside", targetId: "photoshop:ps:42:103",
      })
    } finally { root.unmount(); await app.close() }
  })

  it("drops onto a nested layer without its parent replacing the target", async () => {
    const session = await loadBridgeSession({
      painterSnapshot: path.join(fixtureDir, "painter_snapshot.json"),
      photoshopManifest: path.join(fixtureDir, "photoshop_selection.json"),
    })
    const root = createTestRoot({ width: 652, height: 720 })
    const app = await connectTest(root.renderer)
    const apply = vi.fn(async (_state: BridgeState, _context: string) => "result.json")
    try {
      root.render(<BridgeApp session={session} onApply={apply} onConnectPhotoshop={async () => "unused"} />)
      root.renderer.flush()
      await app.mouse.down(app.getByText("Paint edit"))
      await new Promise(resolve => setTimeout(resolve, 100))
      await app.mouse.move(app.getByText("Lighten"), { pressedButton: 0 })
      await new Promise(resolve => setTimeout(resolve, 100))
      await app.mouse.up(app.getByText("Lighten"))
      await app.getByTestId("action:check").click()
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
    const connect = vi.fn(() => new Promise<string>((_resolve, fail) => { reject = fail }))
    try {
      root.render(<BridgeApp session={session} onApply={async () => "unused"} onConnectPhotoshop={connect} />)
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
      photoshopManifest: path.join(fixtureDir, "photoshop_selection.json"),
    })
    const root = createTestRoot({ width: 652, height: 720 })
    const app = await connectTest(root.renderer)
    const apply = vi.fn(async (_state: BridgeState, _context: string) => "result.json")
    try {
      root.render(<BridgeApp session={session} onApply={apply} onConnectPhotoshop={async () => "unused"} />)
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
      await app.getByTestId("action:check").click()
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
      testRoot.render(<BridgeApp session={session} onApply={async () => "unused"}
        onConnectPhotoshop={async () => "unused"} />)
      testRoot.renderer.flush()
      await new Promise(resolve => setTimeout(resolve, 450))
      const before = await app.getByText("Long layer 0").bounds()
      const button = await app.getByTestId("connect-photoshop").bounds()
      await app.getByText("Long layer 0").hover()
      await app.getByText("Long layer 0").wheel(0, -160)
      testRoot.renderer.flush()
      expect((await app.getByText("Long layer 0").bounds()).y).toBeLessThan(before.y - 20)
      await app.getByTestId("layer-scrollbar:painter").click()
      testRoot.renderer.flush()
      const after = await app.getByText("Long layer 0").bounds()
      expect(after.y).toBeLessThan(before.y - 100)
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
    const connect = vi.fn(async () => "request.json")
    const applied = vi.fn()
    try {
      testRoot.render(<BridgeApp session={session} onApply={async () => "unused"}
        onConnectPhotoshop={connect} onApplied={applied} />)
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
      expect(applied).toHaveBeenCalledWith("request.json")
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
  it("switches the rendered Painter tree with the texture set selector", async () => {
    const session = await loadBridgeSession({
      photoshopManifest: path.join(fixtureDir, "photoshop_selection.json"),
      painterSnapshot: path.join(fixtureDir, "painter_snapshot.json"),
    })
    const testRoot = createTestRoot({ width: 652, height: 484 })
    const app = await connectTest(testRoot.renderer)

    try {
      testRoot.render(
        <BridgeApp
          session={session}
          onApply={async () => "unused"}
          onConnectPhotoshop={async () => "unused"}
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
      photoshopManifest: path.join(fixtureDir, "photoshop_selection.json"),
      painterSnapshot: path.join(fixtureDir, "painter_snapshot.json"),
    })
    const testRoot = createTestRoot({ width: 652, height: 484 })
    const app = await connectTest(testRoot.renderer)

    try {
      testRoot.render(
        <BridgeApp
          session={session}
          onApply={async () => "unused"}
          onConnectPhotoshop={async () => "unused"}
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

  it("opens Painter content without blocking on a Photoshop file picker", async () => {
    const session = await loadBridgeSession({
      painterSnapshot: path.join(fixtureDir, "painter_snapshot.json"),
      output: path.join(fixtureDir, "desktop_connect_request.json"),
    })
    const testRoot = createTestRoot({ width: 652, height: 484 })
    const app = await connectTest(testRoot.renderer)
    let requested = false

    try {
      testRoot.render(
        <BridgeApp
          session={session}
          onApply={async () => "unused"}
          onConnectPhotoshop={async () => {
            requested = true
            return "connect.json"
          }}
        />,
      )
      testRoot.renderer.flush()

      expect(await app.getByText("No selection loaded").count()).toBeGreaterThan(0)
      expect(await app.getByText("Locator").count()).toBeGreaterThan(0)
      await app.getByTestId("connect-photoshop").click()
      expect(requested).toBe(true)
    } finally {
      testRoot.unmount()
      await app.close()
    }
  })
})
