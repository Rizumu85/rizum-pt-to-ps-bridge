import { mkdir, mkdtemp, readFile, writeFile } from "node:fs/promises"
import os from "node:os"
import path from "node:path"
import { PassThrough } from "node:stream"

import { describe, expect, it, vi } from "vitest"

import { inflateSync } from "node:zlib"
import { writePsdBuffer } from "ag-psd"

import { findNode, transferBetweenHosts } from "./model"
import { writeFeaturePsd } from "./test-psd"
import {
  PAINTER_REQUEST_MARKER,
  applyTransfer,
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
  it("streams Apply progress without settling the request until a final receipt", async () => {
    const input = new PassThrough()
    const progress = vi.fn()
    const link = createPainterLink(input, () => {})
    let settled = false
    const pending = link.request("apply", {}, progress).then(reply => { settled = true; return reply })
    input.write('{"type":"apply_progress","message":"Inserting","completed":1,"total":4}\n')
    await Promise.resolve()
    expect(progress).toHaveBeenCalledWith({ type: "apply_progress", message: "Inserting", completed: 1, total: 4 })
    expect(settled).toBe(false)
    input.write('{"type":"apply_progress","message":"Saving"}\n')
    expect(progress.mock.calls.at(-1)?.[0].total).toBeUndefined()
    input.write('{"type":"apply_failed","message":"Partial import","snapshot":null}\n')
    expect(await pending).toMatchObject({ type: "apply_failed", message: "Partial import" })
    input.destroy()
  })

  it("writes apply when mkdir reports EEXIST for a verified directory", async () => {
    const directory = await mkdtemp(path.join(os.tmpdir(), "pt-bridge-existing-"))
    const output = path.join(directory, "request.json")
    const session = await loadBridgeSession({
      painterSnapshot: path.join(fixtureDir, "painter_snapshot.json"),
      photoshopDocument: path.join(fixtureDir, "photoshop_document.psd"),
      output,
    })
    // Reproduce Bun's cloud-directory error, but verify against the real filesystem.
    vi.mocked(mkdir).mockRejectedValueOnce(Object.assign(new Error("Directory already exists"), { code: "EEXIST" }))
    const mapped = transferBetweenHosts(session.state, "substance_painter:sp-lighten", "photoshop:ps:103")
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
      photoshopDocument: path.join(fixtureDir, "photoshop_document.psd"),
      output: path.join(conflict, "request.json"),
    })
    const mapped = transferBetweenHosts(session.state, "substance_painter:sp-lighten", "photoshop:ps:103")
    await expect(writeTransferManifest(session, mapped, session.initialPainterContextId))
      .rejects.toMatchObject({ code: "EEXIST" })
    expect(await readFile(conflict, "utf8")).toBe("keep this file")
  })

  it("does not suppress access errors just because the directory exists", async () => {
    const directory = await mkdtemp(path.join(os.tmpdir(), "pt-bridge-denied-"))
    const session = await loadBridgeSession({
      painterSnapshot: path.join(fixtureDir, "painter_snapshot.json"),
      photoshopDocument: path.join(fixtureDir, "photoshop_document.psd"),
      output: path.join(directory, "request.json"),
    })
    const denied = Object.assign(new Error("Access denied"), { code: "EACCES" })
    vi.mocked(mkdir).mockRejectedValueOnce(denied)
    const mapped = transferBetweenHosts(session.state, "substance_painter:sp-lighten", "photoshop:ps:103")
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
      photoshopDocument: path.join(fixtureDir, "photoshop_document.psd"),
    })
    const selected = session.painterContexts.find(context => context.id === session.initialPainterContextId)
    expect(selected?.textureSet).toBe("M_clothes")
    expect(session.state.painter).toEqual(selected?.nodes)
  })
  it("loads every Painter snapshot context into the domain model", async () => {
    const session = await loadBridgeSession({
      photoshopDocument: path.join(fixtureDir, "photoshop_document.psd"),
      painterSnapshot: path.join(fixtureDir, "painter_snapshot.json"),
    })

    expect(session.photoshopSubtitle).toBe("photoshop_document.psd")
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
      photoshopDocument: path.join(fixtureDir, "photoshop_document.psd"),
      painterSnapshot: path.join(fixtureDir, "painter_snapshot.json"),
      output: path.join(outputDir, "desktop_transfer.json"),
    })
    const mapped = transferBetweenHosts(
      session.state,
      "photoshop:ps:101",
      "substance_painter:sp-working",
    )

    const output = await writeTransferManifest(session, mapped, session.initialPainterContextId)
    const manifest = JSON.parse(await readFile(output, "utf8"))

    expect(manifest.schema_version).toBe(3)
    expect(manifest.request_type).toBe("desktop_transfer")
    expect(manifest.transfers[0].insertion).toBe("inside")
    expect(manifest.transfers[0].direction).toBe("photoshop_to_painter")
    expect(manifest.transfers[0].source.png).toMatch(/Color_pass_ps_101\.png$/)
    expect(manifest.transfers[0].source.mask_png).toMatch(/Color_pass_ps_101_mask\.png$/)
    expect(manifest.photoshop.document.path).toBe(path.join(fixtureDir, "photoshop_document.psd"))
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

  it("reads a PSD directly, locking what Painter cannot represent", async () => {
    const session = await loadBridgeSession({
      photoshopDocument: await writeFeaturePsd(),
      painterSnapshot: path.join(fixtureDir, "painter_snapshot.json"),
    })
    const [folder, levels] = session.state.photoshop
    expect(folder.name).toBe("Paint")
    const [clipped, base] = folder.children ?? []
    expect(clipped.locked).toBe("Clipped · merges into Base")
    expect(base.detail).toBe("Normal · 100% · merges 1 clipped · styles not transferred")
    expect(base.note).toBe("Merges 1 clipped · Styles not transferred")
    expect(levels.locked).toBe("Adjustment layer · not supported")
    const [, , tint, , ramp] = session.state.photoshop
    expect(tint.locked).toBeUndefined()
    expect(tint.detail).toBe("Multiply · 100% · colour fill")
    expect(tint.note).toBe("Colour fill")
    expect(ramp.locked).toBe("Gradient or pattern fill · not supported")
    expect(transferBetweenHosts(session.state, clipped.id, "substance_painter:sp-working")).toBe(session.state)
  })

  it("shows a PSD's file order top-down and addresses rows the way Photoshop's layers do", async () => {
    const directory = await mkdtemp(path.join(os.tmpdir(), "pt-bridge-order-"))
    const file = path.join(directory, "order.psd")
    const pixels = { width: 2, height: 2, data: new Uint8ClampedArray(16).fill(255) }
    // Raw file order, bottom first, exactly as Photoshop saves siblings.
    await writeFile(file, writePsdBuffer({
      width: 2, height: 2, children: [
        { name: "Bottom", top: 0, left: 0, imageData: pixels },
        { name: "Shade", clipping: true, top: 0, left: 0, imageData: pixels },
        { name: "Top", top: 0, left: 0, imageData: pixels },
      ],
    }, { generateThumbnail: false, noBackground: true }))
    const session = await loadBridgeSession({
      photoshopDocument: file,
      painterSnapshot: path.join(fixtureDir, "painter_snapshot.json"),
    })
    expect(session.state.photoshop.map(node => node.name)).toEqual(["Top", "Shade", "Bottom"])
    expect(session.state.photoshop.map(node => node.ref.indexPath)).toEqual([[0], [1], [2]])
    expect(session.state.photoshop[1].locked).toBe("Clipped · merges into Bottom")
  })

  it("sends a colour fill as its colour and mask instead of a bitmap", async () => {
    const outputDir = await mkdtemp(path.join(os.tmpdir(), "pt-bridge-fill-"))
    const session = await loadBridgeSession({
      photoshopDocument: await writeFeaturePsd(),
      painterSnapshot: path.join(fixtureDir, "painter_snapshot.json"),
      output: path.join(outputDir, "desktop_transfer.json"),
    })
    const tint = session.state.photoshop[2]
    const mapped = transferBetweenHosts(session.state, tint.id, "substance_painter:sp-working")
    const manifest = JSON.parse(await readFile(
      await writeTransferManifest(session, mapped, session.initialPainterContextId), "utf8",
    ))
    const source = manifest.transfers[0].source
    expect(source.png).toBeNull()
    expect(source.color).toEqual([1, 128 / 255, 0])
    expect(source.mask_png).toMatch(/Tint_ps_30_mask\.png$/)
  })

  it("renders a mapped folder as its layers with clipping merged into the base", async () => {
    const outputDir = await mkdtemp(path.join(os.tmpdir(), "pt-bridge-psd-"))
    const session = await loadBridgeSession({
      photoshopDocument: await writeFeaturePsd(),
      painterSnapshot: path.join(fixtureDir, "painter_snapshot.json"),
      output: path.join(outputDir, "desktop_transfer.json"),
    })
    const folder = session.state.photoshop[0]
    const mapped = transferBetweenHosts(session.state, folder.id, "substance_painter:sp-working")
    expect(findNode(mapped.painter, folder.id)?.children).toHaveLength(2)

    const manifest = JSON.parse(await readFile(
      await writeTransferManifest(session, mapped, session.initialPainterContextId), "utf8",
    ))
    const source = manifest.transfers[0].source
    expect(source).toMatchObject({ kind: "group", png: null, blend_mode: "pass through" })
    expect(source.children.map((child: { path: string }) => child.path)).toEqual(["Paint/Base"])
    const base = new Uint8Array(await readFile(source.children[0].png))
    // Multiply of red (255,0,0) by gray (128) keeps red at 128 inside the base.
    expect(Array.from(decodeRgba8(base, 1, 1))).toEqual([128, 0, 0, 255])
  })

  it("writes Painter-to-Photoshop intent with the native Photoshop layer id", async () => {
    const outputDir = await mkdtemp(path.join(os.tmpdir(), "pt-bridge-desktop-"))
    const session = await loadBridgeSession({
      photoshopDocument: path.join(fixtureDir, "photoshop_document.psd"),
      painterSnapshot: path.join(fixtureDir, "painter_snapshot.json"),
      output: path.join(outputDir, "desktop_transfer.json"),
    })
    const mapped = transferBetweenHosts(
      session.state,
      "substance_painter:sp-lighten",
      "photoshop:ps:103",
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
        index_path: [3],
      },
    })
  })

  it("accepts environment paths without hidden discovery", () => {
    expect(
      parseSessionOptions([], {
        PT_BRIDGE_PHOTOSHOP_DOCUMENT: "document.psd",
        PT_BRIDGE_PAINTER_SNAPSHOT: "target.json",
      }),
    ).toEqual({
      photoshopDocument: "document.psd",
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

    expect(session.photoshop).toBeNull()
    expect(session.photoshopSubtitle).toBe("No document connected")
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

  it("applies through Painter and reloads both trees from its reply", async () => {
    const outputDir = await mkdtemp(path.join(os.tmpdir(), "pt-bridge-apply-"))
    const session = await loadBridgeSession({
      painterSnapshot: path.join(fixtureDir, "painter_snapshot.json"),
      photoshopDocument: path.join(fixtureDir, "photoshop_document.psd"),
      output: path.join(outputDir, "desktop_transfer.json"),
    })
    const mapped = transferBetweenHosts(session.state, "photoshop:ps:101", "substance_painter:sp-working")
    const requests: unknown[] = []
    const reply = (type: "applied" | "apply_failed") => ({
      request: async (kind: string, fields?: Record<string, string>) => {
        requests.push({ kind, ...fields })
        return { type, message: `${type} message`, snapshot: path.join(fixtureDir, "painter_snapshot.json") }
      },
    })

    const done = await applyTransfer(session, mapped, session.initialPainterContextId, reply("applied"))
    expect(requests[0]).toEqual({ kind: "apply", manifest: path.join(outputDir, "desktop_transfer.json") })
    expect(done).toMatchObject({ message: "applied message", failed: false })
    expect(done.session?.state.mappings).toEqual([])
    expect(done.session?.photoshop?.path).toBe(session.photoshop?.path)

    const failed = await applyTransfer(session, mapped, session.initialPainterContextId, reply("apply_failed"))
    expect(failed).toMatchObject({ message: "apply_failed message", failed: true })
    expect(failed.session).not.toBeNull()
  })

  it("rejects a request Painter reports as failed", async () => {
    const pipe = painterPipe()
    const link = createPainterLink(pipe.input, () => {})
    const pending = link.request("apply", { manifest: "m.json" })
    pipe.send('{"type":"failed","message":"Painter is still busy with the last request."}\n')
    await expect(pending).rejects.toThrow("Painter is still busy")
  })

  it("reloads the session from the connected PSD and keeps Painter paths", async () => {
    const session = await loadBridgeSession({
      painterSnapshot: path.join(fixtureDir, "painter_snapshot.json"),
      output: path.join(os.tmpdir(), "pt-bridge-link.json"),
    })
    const psd = path.join(fixtureDir, "photoshop_document.psd")
    const connected = await connectPhotoshop(session, {
      request: async () => ({ type: "photoshop_connected", psd }),
    })
    expect(connected?.photoshop?.path).toBe(psd)
    expect(connected?.targetSnapshotPath).toBe(session.targetSnapshotPath)
    expect(connected?.outputPath).toBe(session.outputPath)
    await expect(connectPhotoshop(session, {
      request: async () => ({ type: "photoshop_connect_cancelled" }),
    })).resolves.toBeNull()
  })
})

function decodeRgba8(png: Uint8Array, x: number, y: number): Uint8Array {
  const view = new DataView(png.buffer, png.byteOffset)
  const width = view.getUint32(16)
  const chunks: Uint8Array[] = []
  for (let offset = 8; offset < png.length;) {
    const length = view.getUint32(offset)
    const type = String.fromCharCode(...png.subarray(offset + 4, offset + 8))
    if (type === "IDAT") chunks.push(png.subarray(offset + 8, offset + 8 + length))
    offset += length + 12
  }
  const raw = inflateSync(Buffer.concat(chunks))
  const start = y * (width * 4 + 1) + 1 + x * 4
  return raw.subarray(start, start + 4)
}
