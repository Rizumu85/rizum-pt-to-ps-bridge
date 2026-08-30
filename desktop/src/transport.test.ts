import { mkdtemp, readFile } from "node:fs/promises"
import os from "node:os"
import path from "node:path"

import { describe, expect, it } from "vitest"

import { transferToPainter } from "./model"
import { loadBridgeSession, parseSessionOptions, writeTransferManifest } from "./transport"

const fixtureDir = path.resolve(import.meta.dirname, "../test-fixtures")

describe("desktop file transport", () => {
  it("loads Photoshop selection and Painter sidecar into the domain model", async () => {
    const session = await loadBridgeSession({
      photoshopManifest: path.join(fixtureDir, "photoshop_selection.json"),
      painterSnapshot: path.join(fixtureDir, "painter.rizum.json"),
    })

    expect(session.photoshopSubtitle).toBe("basecolor.psd")
    expect(session.painterSubtitle).toBe("M_body · basecolor")
    expect(session.state.photoshop.map((node) => node.name)).toEqual([
      "Paint edit",
      "Color pass",
      "Mask cleanup",
    ])
    expect(session.state.painter[2].children?.map((node) => node.name)).toEqual([
      "Lighten",
      "Recolor",
    ])
  })

  it("writes an atomic transfer manifest with explicit insertion intent", async () => {
    const outputDir = await mkdtemp(path.join(os.tmpdir(), "pt-bridge-desktop-"))
    const session = await loadBridgeSession({
      photoshopManifest: path.join(fixtureDir, "photoshop_selection.json"),
      painterSnapshot: path.join(fixtureDir, "painter.rizum.json"),
      output: path.join(outputDir, "desktop_transfer.json"),
    })
    const mapped = transferToPainter(
      session.state,
      "photoshop:ps:42:101",
      "substance_painter:sp-working",
    )

    const output = await writeTransferManifest(session, mapped)
    const manifest = JSON.parse(await readFile(output, "utf8"))

    expect(manifest.request_type).toBe("desktop_transfer")
    expect(manifest.transfers[0].insertion).toBe("inside")
    expect(manifest.transfers[0].source.mask_png).toMatch(/color_pass_mask\.png$/)
    expect(manifest.transfers[0].target.id).toBe("sp-working")
  })

  it("accepts environment paths without hidden discovery", () => {
    expect(
      parseSessionOptions([], {
        PT_BRIDGE_PHOTOSHOP_MANIFEST: "selection.json",
        PT_BRIDGE_PAINTER_SNAPSHOT: "target.json",
      }),
    ).toEqual({
      photoshopManifest: "selection.json",
      painterSnapshot: "target.json",
      output: undefined,
    })
  })
})
