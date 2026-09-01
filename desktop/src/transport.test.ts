import { mkdtemp, readFile, writeFile } from "node:fs/promises"
import os from "node:os"
import path from "node:path"

import { describe, expect, it } from "vitest"

import { transferBetweenHosts } from "./model"
import {
  loadBridgeSession,
  parseSessionOptions,
  writeConnectPhotoshopRequest,
  writeTransferManifest,
} from "./transport"

const fixtureDir = path.resolve(import.meta.dirname, "../test-fixtures")

describe("desktop file transport", () => {
  it("loads every Painter snapshot context into the domain model", async () => {
    const session = await loadBridgeSession({
      photoshopManifest: path.join(fixtureDir, "photoshop_selection.json"),
      painterSnapshot: path.join(fixtureDir, "painter_snapshot.json"),
    })

    expect(session.photoshopSubtitle).toBe("basecolor.psd")
    expect(session.painterContexts.map((context) => context.subtitle)).toEqual([
      "M_body · Base Color",
      "M_body · Normal",
      "M_clothes · Base Color",
    ])
    expect(session.initialPainterContextId).toBe(session.painterContexts[0].id)
    expect(session.state.photoshop.map((node) => node.name)).toEqual([
      "Paint edit",
      "Color pass",
      "Mask cleanup",
      "Retouch group",
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
      painterSnapshot: path.join(fixtureDir, "painter_snapshot.json"),
      output: path.join(outputDir, "desktop_transfer.json"),
    })
    const mapped = transferBetweenHosts(
      session.state,
      "photoshop:ps:42:101",
      "substance_painter:sp-working",
    )

    const output = await writeTransferManifest(session, mapped, session.initialPainterContextId)
    const manifest = JSON.parse(await readFile(output, "utf8"))

    expect(manifest.schema_version).toBe(2)
    expect(manifest.request_type).toBe("desktop_transfer")
    expect(manifest.transfers[0].insertion).toBe("inside")
    expect(manifest.transfers[0].direction).toBe("photoshop_to_painter")
    expect(manifest.transfers[0].source.mask_png).toMatch(/color_pass_mask\.png$/)
    expect(manifest.transfers[0].source).toMatchObject({
      blend_mode: "overlay",
      opacity: 65,
      visible: true,
    })
    expect(manifest.transfers[0].target.id).toBe("sp-working")
    expect(manifest.painter.context).toMatchObject({
      texture_set: "M_body",
      stack: "",
      channel: "BaseColor",
    })
  })

  it("rebuilds a Photoshop document hierarchy from manifest paths", async () => {
    const outputDir = await mkdtemp(path.join(os.tmpdir(), "pt-bridge-photoshop-tree-"))
    const manifestPath = path.join(outputDir, "photoshop_selection.json")
    await writeFile(
      manifestPath,
      JSON.stringify({
        schema_version: 1,
        request_type: "photoshop_selection",
        document: { name: "external.psd", path: "C:/art/external.psd" },
        layers: [
          {
            source_id: "ps:1:10",
            ps_layer_id: 10,
            display_name: "Paint",
            ps_kind: "group",
            path: "Paint",
            png: "paint.png",
          },
          {
            source_id: "ps:1:11",
            ps_layer_id: 11,
            parent_id: 10,
            display_name: "Details",
            ps_kind: "pixel",
            group: "Paint",
            path: "Paint/Details",
            png: "details.png",
          },
        ],
      }),
      "utf8",
    )

    const session = await loadBridgeSession({
      photoshopManifest: manifestPath,
      painterSnapshot: path.join(fixtureDir, "painter_snapshot.json"),
    })

    expect(session.state.photoshop.map((node) => node.name)).toEqual(["Paint"])
    expect(session.state.photoshop[0].children?.map((node) => node.name)).toEqual(["Details"])
  })

  it("writes Painter-to-Photoshop intent with the native Photoshop layer id", async () => {
    const outputDir = await mkdtemp(path.join(os.tmpdir(), "pt-bridge-desktop-"))
    const session = await loadBridgeSession({
      photoshopManifest: path.join(fixtureDir, "photoshop_selection.json"),
      painterSnapshot: path.join(fixtureDir, "painter_snapshot.json"),
      output: path.join(outputDir, "desktop_transfer.json"),
    })
    const mapped = transferBetweenHosts(
      session.state,
      "substance_painter:sp-lighten",
      "photoshop:ps:42:103",
    )

    const output = await writeTransferManifest(session, mapped, session.initialPainterContextId)
    const manifest = JSON.parse(await readFile(output, "utf8"))

    expect(manifest.transfers[0]).toMatchObject({
      direction: "painter_to_photoshop",
      insertion: "inside",
      source: {
        host: "substance_painter",
        id: "sp-lighten",
        has_mask: true,
      },
      target: {
        host: "photoshop",
        id: "103",
        kind: "group",
      },
    })
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

  it("opens with Painter only until Photoshop is connected", async () => {
    const outputDir = await mkdtemp(path.join(os.tmpdir(), "pt-bridge-desktop-"))
    const output = path.join(outputDir, "desktop_transfer.json")
    const options = parseSessionOptions([
      "--painter",
      path.join(fixtureDir, "painter_snapshot.json"),
      "--output",
      output,
    ])
    const session = await loadBridgeSession(options)

    expect(session.photoshopConnected).toBe(false)
    expect(session.photoshopSubtitle).toBe("No selection loaded")
    expect(session.state.photoshop).toEqual([])
    expect(session.state.painter.length).toBeGreaterThan(0)

    await writeConnectPhotoshopRequest(session)
    const request = JSON.parse(await readFile(output, "utf8"))
    expect(request).toMatchObject({
      schema_version: 1,
      request_type: "desktop_connect_photoshop",
      painter_snapshot: path.join(fixtureDir, "painter_snapshot.json"),
    })
  })
})
