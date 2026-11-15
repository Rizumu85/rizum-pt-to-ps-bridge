import { mkdtemp, readFile, writeFile } from "node:fs/promises"
import os from "node:os"
import path from "node:path"
import { deflateSync } from "node:zlib"

import { getLayerImageData, readPsd, writePsdBuffer } from "ag-psd"
import { describe, expect, it } from "vitest"

import { readPhotoshopDocument } from "./psd"
import { writeFeaturePsd } from "./test-psd"
import { readTiffDocument } from "./tiff"

const HEADER = "Adobe Photoshop Document Data Block\0"

/** A one-IFD TIFF; entries are written in the file's byte order. */
function tiff(le: boolean, width: number, height: number, depth: number, sourceData: Uint8Array | null): Uint8Array {
  const tags: [number, number, number, Uint8Array | number][] = [
    [256, 4, 1, width], [257, 4, 1, height], [258, 3, 1, depth], [262, 3, 1, 2], [277, 3, 1, 4],
  ]
  if (sourceData) tags.push([37724, 7, sourceData.length, sourceData])
  const ifdSize = 2 + tags.length * 12 + 4
  const out = new Uint8Array(8 + ifdSize + (sourceData?.length ?? 0))
  const view = new DataView(out.buffer)
  out.set(le ? [0x49, 0x49, 42, 0] : [0x4d, 0x4d, 0, 42])
  view.setUint32(4, 8, le)
  view.setUint16(8, tags.length, le)
  tags.forEach(([tag, type, count, value], index) => {
    const at = 10 + index * 12
    view.setUint16(at, tag, le); view.setUint16(at + 2, type, le); view.setUint32(at + 4, count, le)
    if (value instanceof Uint8Array) {
      view.setUint32(at + 8, 8 + ifdSize, le)
      out.set(value, 8 + ifdSize)
    } else if (type === 3) view.setUint16(at + 8, value, le)
    else view.setUint32(at + 8, value, le)
  })
  return out
}

function sourceData(le: boolean, key: string, layerInfo: Uint8Array): Uint8Array {
  const out = new Uint8Array(HEADER.length + 12 + layerInfo.length)
  out.set(Uint8Array.from(HEADER, c => c.charCodeAt(0)))
  const code = (text: string) => Uint8Array.from(le ? [...text].reverse() : [...text], c => c.charCodeAt(0))
  out.set(code("8BIM"), HEADER.length)
  out.set(code(key), HEADER.length + 4)
  new DataView(out.buffer).setUint32(HEADER.length + 8, layerInfo.length, le)
  out.set(layerInfo, HEADER.length + 12)
  return out
}

/** The layer info section of a PSD ag-psd wrote: big-endian, as a big-endian TIFF stores it. */
function psdLayerInfo(psd: Uint8Array): Uint8Array {
  const view = new DataView(psd.buffer, psd.byteOffset, psd.byteLength)
  let at = 26
  at += 4 + view.getUint32(at)
  at += 4 + view.getUint32(at)
  at += 4
  const length = view.getUint32(at)
  return psd.subarray(at + 4, at + 4 + length)
}

async function saved(name: string, bytes: Uint8Array) {
  const file = path.join(await mkdtemp(path.join(os.tmpdir(), "pt-bridge-tiff-")), name)
  await writeFile(file, bytes)
  return file
}

describe("layered TIFF documents", () => {
  it("read as the PSD they were saved from", async () => {
    const psdPath = await writeFeaturePsd()
    const psd = new Uint8Array(await readFile(psdPath))
    const tiffPath = await saved("features.tif", tiff(false, 4, 4, 8, sourceData(false, "Layr", psdLayerInfo(psd))))

    const fromPsd = await readPhotoshopDocument(psdPath)
    const fromTiff = await readPhotoshopDocument(tiffPath)

    const shape = (document: typeof fromPsd) => JSON.stringify(document.nodes, (key, value) =>
      key === "assetPath" || key === "thumbnailPath" ? undefined : value)
    expect(shape(fromTiff)).toBe(shape(fromPsd))
    expect([...fromTiff.colors]).toEqual([...fromPsd.colors])
    expect([...fromTiff.layers.keys()]).toEqual([...fromPsd.layers.keys()])
    for (const [id, layer] of fromPsd.layers) {
      const ours = getLayerImageData(fromTiff.layers.get(id)!)?.data
      expect(ours ? [...ours] : null, id).toEqual((() => { const data = getLayerImageData(layer)?.data; return data ? [...data] : null })())
    }
  })

  it("read a mask with density, feather and a real mask", async () => {
    const size = 4
    const plane = (value: number) => ({ width: size, height: size, data: new Uint8ClampedArray(size * size * 4).fill(value) })
    const psd = writePsdBuffer({
      width: size, height: size, children: [{
        id: 5, name: "Soft", top: 0, left: 0, imageData: plane(200),
        mask: { top: 0, left: 0, bottom: size, right: size, defaultColor: 0, userMaskDensity: 0.5, userMaskFeather: 2, imageData: plane(255) },
        realMask: { top: 1, left: 1, bottom: 3, right: 3, defaultColor: 0, imageData: plane(128) },
      }],
    }, { generateThumbnail: false, noBackground: true })
    const options = { useRawData: true, skipCompositeImageData: true, skipThumbnail: true } as const
    const direct = readPsd(psd, options).children![0]
    const converted = readPsd(readTiffDocument(tiff(false, size, size, 8, sourceData(false, "Layr", psdLayerInfo(psd)))).psd, options).children![0]
    for (const field of ["mask", "realMask"] as const) {
      const { imageDataRaw: _a, ...ours } = (converted[field] ?? {}) as Record<string, unknown>
      const { imageDataRaw: _b, ...theirs } = (direct[field] ?? {}) as Record<string, unknown>
      expect(ours, field).toEqual(theirs)
    }
    expect(direct.mask?.userMaskDensity).toBeCloseTo(0.5, 2)
  })

  it("read 16-bit little-endian layers whichever way their channels are compressed", async () => {
    // Written byte by byte as Photoshop on Windows does, not by the converter.
    const width = 2, height = 2
    const samples = { alpha: [65535, 65535, 0, 65535], red: [0, 1000, 65535, 32768], green: [10, 20, 30, 40], blue: [60000, 50000, 40000, 30000] }
    const littleEndian = (values: number[]) => {
      const out = new Uint8Array(values.length * 2)
      values.forEach((value, index) => new DataView(out.buffer).setUint16(index * 2, value, true))
      return out
    }
    const predicted = (values: number[]) => values.map((value, index) => (index % width === 0 ? value : (value - values[index - 1]) & 0xffff))
    const channel = (compression: number, data: Uint8Array) => {
      const out = new Uint8Array(2 + data.length)
      new DataView(out.buffer).setUint16(0, compression, true)
      out.set(data, 2)
      return out
    }
    const channels: [number, Uint8Array][] = [
      [-1, channel(0, littleEndian(samples.alpha))],
      [0, channel(2, new Uint8Array(deflateSync(littleEndian(samples.red))))],
      [1, channel(3, new Uint8Array(deflateSync(littleEndian(predicted(samples.green)))))],
      [2, channel(0, littleEndian(samples.blue))],
    ]
    const bytes: number[] = []
    const u8 = (v: number) => bytes.push(v & 0xff)
    const u16 = (v: number) => { u8(v); u8(v >> 8) }
    const u32 = (v: number) => { u16(v & 0xffff); u16(v >>> 16) }
    const code = (text: string) => [...text].reverse().forEach(c => u8(c.charCodeAt(0)))
    u16(1)
    ;[0, 0, height, width].forEach(u32)
    u16(channels.length)
    for (const [id, data] of channels) { u16(id & 0xffff); u32(data.length) }
    code("8BIM"); code("norm"); u8(255); u8(0); u8(0); u8(0)
    const extra = [0, 0, 0, 0, 0, 0, 0, 0, 1, 65, 0, 0]
    const idBlock = [..."MIB8"].map(c => c.charCodeAt(0)).concat([..."diyl"].map(c => c.charCodeAt(0)), [4, 0, 0, 0, 7, 0, 0, 0])
    u32(extra.length + idBlock.length)
    extra.concat(idBlock).forEach(u8)
    for (const [, data] of channels) data.forEach(u8)

    const file = await saved("deep.tif", tiff(true, width, height, 16, sourceData(true, "Layr", Uint8Array.from(bytes))))
    const document = await readPhotoshopDocument(file)
    expect(document.bitDepth).toBe(16)
    expect(document.nodes.map(node => [node.name, node.ref.nativeId])).toEqual([["A", "7"]])
    const data = getLayerImageData(document.layers.get(document.nodes[0].id)!)!.data
    const read = (offset: number) => Array.from({ length: 4 }, (_, pixel) => data[pixel * 4 + offset])
    expect([read(0), read(1), read(2), read(3)]).toEqual([samples.red, samples.green, samples.blue, samples.alpha])
  })

  it("open with no layers when they were saved without", async () => {
    const file = await saved("flat.tif", tiff(true, 8, 8, 8, null))
    const document = await readPhotoshopDocument(file)
    expect(document.nodes).toEqual([])
    expect([document.width, document.height]).toEqual([8, 8])
  })
})
