import path from "node:path"

import { connectTest } from "@gpuix/react/automation"
import { createTestRoot } from "@gpuix/react/testing"
import { describe, expect, it } from "vitest"

import { BridgeApp } from "./main"
import { loadBridgeSession } from "./transport"

const fixtureDir = path.resolve(import.meta.dirname, "../test-fixtures")

describe("Painter context selectors", () => {
  it("switches the rendered Painter tree with the texture set selector", async () => {
    const session = await loadBridgeSession({
      photoshopManifest: path.join(fixtureDir, "photoshop_selection.json"),
      painterSnapshot: path.join(fixtureDir, "painter_snapshot.json"),
    })
    const testRoot = createTestRoot({ width: 652, height: 484 })
    const app = await connectTest(testRoot.renderer)

    try {
      testRoot.render(<BridgeApp session={session} onApply={async () => "unused"} />)
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
      testRoot.render(<BridgeApp session={session} onApply={async () => "unused"} />)
      testRoot.renderer.flush()

      expect(await app.getByText("Drop Photoshop layers here to map").count()).toBe(0)
      expect(await app.getByText("Map Photoshop layers").count()).toBe(0)

      await app.getByTestId("mapping-help-trigger").click()
      expect(await app.getByText("Map Photoshop layers").count()).toBeGreaterThan(0)
      expect(await app.getByText("Group: place inside").count()).toBeGreaterThan(0)
    } finally {
      testRoot.unmount()
      await app.close()
    }
  })
})
