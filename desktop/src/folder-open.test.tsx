import { mkdtemp, readFile, writeFile } from "node:fs/promises"
import os from "node:os"
import path from "node:path"

import { writePsdBuffer } from "ag-psd"
import { connectTest } from "@gpuix/react/automation"
import { describe, expect, it } from "vitest"

import { BridgeApp } from "./bridge-app"
import { fileOrder } from "./test-psd"
import { createTestRoot } from "./test-root"
import { loadBridgeSession } from "./transport"

const fixtureDir = path.resolve(import.meta.dirname, "../test-fixtures")

describe("folders open as their hosts show them", () => {
  it("folds a Painter folder folded in Painter and a Photoshop group closed in Photoshop", async () => {
    const directory = await mkdtemp(path.join(os.tmpdir(), "pt-bridge-folders-"))
    const snapshot = JSON.parse(await readFile(path.join(fixtureDir, "painter_snapshot.json"), "utf8"))
    for (const context of snapshot.contexts) {
      for (const layer of context.layers) if (layer.uid_hex === "sp-working") layer.collapsed = true
    }
    const snapshotPath = path.join(directory, "painter_snapshot.json")
    await writeFile(snapshotPath, JSON.stringify(snapshot))
    const pixel = { width: 1, height: 1, data: new Uint8ClampedArray([255, 0, 0, 255]) }
    const psdPath = path.join(directory, "folders.psd")
    await writeFile(psdPath, writePsdBuffer({
      width: 1, height: 1,
      children: fileOrder([
        { id: 1, name: "Shut", opened: false, children: [{ id: 2, name: "Inside shut", top: 0, left: 0, imageData: pixel }] },
        { id: 3, name: "Open", opened: true, children: [{ id: 4, name: "Inside open", top: 0, left: 0, imageData: pixel }] },
      ]),
    }))
    const session = await loadBridgeSession({ painterSnapshot: snapshotPath, photoshopDocument: psdPath })
    const root = createTestRoot({ width: 700, height: 560 })
    const app = await connectTest(root.renderer)
    try {
      root.render(<BridgeApp session={session} onConnectPhotoshop={async () => null}
        onApply={async () => ({ session: null, message: "", failed: false })} />)
      root.renderer.flush()
      expect(await app.getByText("Working").count()).toBe(1)
      expect(await app.getByText("Lighten").count()).toBe(0)
      expect(await app.getByText("Inside shut").count()).toBe(0)
      expect(await app.getByText("Inside open").count()).toBe(1)
    } finally { root.unmount(); await app.close() }
  })
})
