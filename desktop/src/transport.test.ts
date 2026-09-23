import { mkdir, mkdtemp, readFile, writeFile } from "node:fs/promises"
import os from "node:os"
import path from "node:path"
import { PassThrough } from "node:stream"

import { describe, expect, it, vi } from "vitest"

import { transferBetweenHosts } from "./model"
import {
  PAINTER_REQUEST_MARKER,
  connectPhotoshop,
  createPainterLink,
  loadBridgeSession,
  parseSessionOptions,
  writeTransferManifest,
} from "./transport"

const fixtureDir = path.resolve(import.meta.dirname, "../test-fixtures")

vi.mock("node:fs/promises", async importOriginal => {
  const actual = await importOriginal<typeof import("node:fs/promises")>()
  return { ...actual, mkdir: vi.fn(actual.mkdir) }
})

describe("desktop file transport", () => {
  it("writes apply when mkdir reports EEXIST for a verified directory", async () => {
    const directory = await mkdtemp(path.join(os.tmpdir(), "pt-bridge-existing-"))
    const output = path.join(directory, "request.json")
    const session = await loadBridgeSession({
      painterSnapshot: path.join(fixtureDir, "painter_snapshot.json"),
      photoshopManifest: path.join(fixtureDir, "photoshop_selection.json"),
      output,
    })
    // Reproduce Bun's cloud-directory error, but verify against the real filesystem.
    vi.mocked(mkdir).mockRejectedValueOnce(Object.assign(new Error("Directory already exists"), { code: "EEXIST" }))
    const mapped = transferBetweenHosts(session.state, "photoshop:ps:42:101", "substance_painter:sp-working")
    await writeTransferManifest(session, mapped, session.initialPainterContextId)
    const request = JSON.parse(await readFile(output, "utf8"))
    expect(request.request_type).toBe("desktop_transfer")
  })

  it("rejects a real file blocking the output directory without modifying it", async () => {
    const directory = await mkdtemp(path.join(os.tmpdir(), "pt-bridge-conflict-"))
    const conflict = path.join(directory, "not-a-directory")
    await writeFile(conflict, "keep this file")
    const session = await loadBridgeSession({
      painterSnapshot: path.join(fixtureDir, "painter_snapshot.json"),
      photoshopManifest: path.join(fixtureDir, "photoshop_selection.json"),
      output: path.join(conflict, "request.json"),
    })
    const mapped = transferBetweenHosts(session.state, "photoshop:ps:42:101", "substance_painter:sp-working")
    await expect(writeTransferManifest(session, mapped, session.initialPainterContextId))
      .rejects.toMatchObject({ code: "EEXIST" })
    expect(await readFile(conflict, "utf8")).toBe("keep this file")
  })

  it("does not suppress access errors just because the directory exists", async () => {
    const directory = await mkdtemp(path.join(os.tmpdir(), "pt-bridge-denied-"))
    const session = await loadBridgeSession({
      painterSnapshot: path.join(fixtureDir, "painter_snapshot.json"),
      photoshopManifest: path.join(fixtureDir, "photoshop_selection.json"),
      output: path.join(directory, "request.json"),
    })
    const denied = Object.assign(new Error("Access denied"), { code: "EACCES" })
    vi.mocked(mkdir).mockRejectedValueOnce(denied)
    const mapped = transferBetweenHosts(session.state, "photoshop:ps:42:101", "substance_painter:sp-working")
    await expect(writeTransferManifest(session, mapped, session.initialPainterContextId)).rejects.toBe(denied)
  })

  it("opens Painter's active texture set instead of the PSD's original texture set", async () => {
    const directory = await mkdtemp(path.join(os.tmpdir(), "pt-bridge-active-"))
    const snapshot = JSON.parse(await readFile(path.join(fixtureDir, "painter_snapshot.json"), "utf8"))
    snapshot.active_context = { texture_set: "M_clothes", stack: "" }
    const snapshotPath = path.join(directory, "painter_snapshot.json")
    await writeFile(snapshotPath, JSON.stringify(snapshot))
    const session = await loadBridgeSession({
      painterSnapshot: snapshotPath,
      photoshopManifest: path.join(fixtureDir, "photoshop_selection.json"),
    })
    const selected = session.painterContexts.find(context => context.id === session.initialPainterContextId)
    expect(selected?.textureSet).toBe("M_clothes")
    expect(session.state.painter).toEqual(selected?.nodes)
  })
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
    expect(session.outputPath).toBe(output)
  })
})

function painterPipe() {
  const input = new PassThrough()
  return {
    input,
    send: (text: string) => { input.write(text) },
    end: () => { input.end() },
  }
}

describe("Painter link", () => {
  it("marks requests and resolves the reply even when it arrives in pieces", async () => {
    const pipe = painterPipe()
    const written: string[] = []
    const link = createPainterLink(pipe.input, line => written.push(line))
    const reply = link.request("connect_photoshop")
    expect(written).toEqual([`${PAINTER_REQUEST_MARKER}{"type":"connect_photoshop"}\n`])
    pipe.send('{"type":"photoshop_connect_')
    pipe.send('failed","message":"Photoshop is busy"}\n')
    await expect(reply).resolves.toEqual({ type: "photoshop_connect_failed", message: "Photoshop is busy" })
  })

  it("rejects pending and later requests once Painter closes stdin", async () => {
    const pipe = painterPipe()
    const link = createPainterLink(pipe.input, () => {})
    const pending = link.request("connect_photoshop")
    pipe.end()
    await expect(pending).rejects.toThrow("Painter closed the Bridge connection")
    await expect(link.request("connect_photoshop")).rejects.toThrow("Painter closed the Bridge connection")
  })

  it("reloads the session from the connected manifest and keeps Painter paths", async () => {
    const session = await loadBridgeSession({
      painterSnapshot: path.join(fixtureDir, "painter_snapshot.json"),
      output: path.join(os.tmpdir(), "pt-bridge-link.json"),
    })
    const manifest = path.join(fixtureDir, "photoshop_selection.json")
    const connected = await connectPhotoshop(session, {
      request: async () => ({ type: "photoshop_connected", manifest }),
    })
    expect(connected?.photoshopConnected).toBe(true)
    expect(connected?.sourceManifestPath).toBe(manifest)
    expect(connected?.targetSnapshotPath).toBe(session.targetSnapshotPath)
    expect(connected?.outputPath).toBe(session.outputPath)
    await expect(connectPhotoshop(session, {
      request: async () => ({ type: "photoshop_connect_cancelled" }),
    })).resolves.toBeNull()
  })
})
