import { deflateSync, inflateSync } from "node:zlib"

/**
 * Photoshop keeps a layered TIFF's layers in tag 37724 as the PSD layer
 * section, in the TIFF's byte order. ag-psd reads only big-endian PSDs, and
 * Photoshop on Windows writes little-endian TIFFs by default, so this rebuilds
 * a big-endian PSD from the TIFF and the rest of the mapper reads it as any
 * other PSD. The user asked for TIFF support next to PSD (2026-11-15).
 *
 * Only what the mapper uses is rewritten: layer records, names, folders, ids,
 * masks and pixels. Styles, adjustments, vector masks and fills are
 * Photoshop-rendered content the mapper does not transfer; it only needs to
 * know they are there, and a solid fill's colour, so they travel as hints.
 */
export type LayerHint = {
  adjustment?: true
  effects?: true
  vectorMask?: true
  vectorFill?: { type: "color"; color: { r: number; g: number; b: number } } | { type: "other" }
}

export type TiffDocument = {
  psd: Uint8Array
  /** By Photoshop layer id. */
  hints: Map<number, LayerHint>
}

const SOURCE_DATA_TAG = 37724
const ICC_PROFILE_TAG = 34675
const SOURCE_DATA_HEADER = "Adobe Photoshop Document Data Block\0"
const ADJUSTMENT_KEYS = new Set([
  "levl", "curv", "brit", "blnc", "hue2", "hue ", "selc", "mixr", "grdm", "phfl", "thrs", "nvrt",
  "post", "expA", "vibA", "clrL", "blwh", "CgEd",
])

export function isTiff(bytes: Uint8Array): boolean {
  return bytes.length >= 4 && (
    (bytes[0] === 0x49 && bytes[1] === 0x49 && bytes[2] === 42 && bytes[3] === 0)
    || (bytes[0] === 0x4d && bytes[1] === 0x4d && bytes[2] === 0 && bytes[3] === 42)
  )
}

class Reader {
  pos: number
  private view: DataView
  constructor(readonly bytes: Uint8Array, readonly le: boolean, start = 0, readonly end = bytes.length) {
    this.pos = start
    this.view = new DataView(bytes.buffer, bytes.byteOffset, bytes.byteLength)
  }
  private need(size: number) {
    if (this.pos + size > this.end) throw new Error("The TIFF's Photoshop layer data is cut short")
  }
  u8() { this.need(1); return this.bytes[this.pos++] }
  u16() { this.need(2); const v = this.view.getUint16(this.pos, this.le); this.pos += 2; return v }
  i16() { this.need(2); const v = this.view.getInt16(this.pos, this.le); this.pos += 2; return v }
  u32() { this.need(4); const v = this.view.getUint32(this.pos, this.le); this.pos += 4; return v }
  /** A block length: 8B64 blocks carry a 64-bit one. */
  length(sig: string) {
    if (sig !== "8B64" && sig !== "46B8") return this.u32()
    const high = this.u32(), low = this.u32()
    return this.le ? high + low * 2 ** 32 : high * 2 ** 32 + low
  }
  i32() { this.need(4); const v = this.view.getInt32(this.pos, this.le); this.pos += 4; return v }
  f64() { this.need(8); const v = this.view.getFloat64(this.pos, this.le); this.pos += 8; return v }
  take(size: number) { this.need(size); const v = this.bytes.subarray(this.pos, this.pos + size); this.pos += size; return v }
  /** A four-character code, which a little-endian file stores reversed. */
  code() { const raw = this.take(4); return String.fromCharCode(...(this.le ? [...raw].reverse() : raw)) }
  left() { return this.end - this.pos }
}

class Writer {
  private chunks: Uint8Array[] = []
  length = 0
  private scalar(size: number, set: (view: DataView) => void) {
    const chunk = new Uint8Array(size)
    set(new DataView(chunk.buffer))
    this.push(chunk)
  }
  push(chunk: Uint8Array) { this.chunks.push(chunk); this.length += chunk.length }
  u8(v: number) { this.scalar(1, d => d.setUint8(0, v)) }
  u16(v: number) { this.scalar(2, d => d.setUint16(0, v)) }
  i16(v: number) { this.scalar(2, d => d.setInt16(0, v)) }
  u32(v: number) { this.scalar(4, d => d.setUint32(0, v)) }
  i32(v: number) { this.scalar(4, d => d.setInt32(0, v)) }
  code(v: string) { this.push(Uint8Array.from(v, c => c.charCodeAt(0))) }
  pad(multiple: number) { while (this.length % multiple) this.u8(0) }
  bytes() {
    const out = new Uint8Array(this.length)
    let at = 0
    for (const chunk of this.chunks) { out.set(chunk, at); at += chunk.length }
    return out
  }
}

type Tag = { type: number; count: number; at: number }

function readTags(bytes: Uint8Array): { le: boolean; tags: Map<number, Tag> } {
  const le = bytes[0] === 0x49
  const r = new Reader(bytes, le, 4)
  r.pos = r.u32()
  const tags = new Map<number, Tag>()
  const count = r.u16()
  for (let index = 0; index < count; index += 1) {
    const tag = r.u16(), type = r.u16(), n = r.u32()
    const size = ({ 1: 1, 2: 1, 3: 2, 4: 4, 7: 1 } as Record<number, number>)[type] ?? 4
    const at = size * n <= 4 ? r.pos : r.u32()
    if (size * n <= 4) r.pos += 4
    tags.set(tag, { type, count: n, at })
  }
  return { le, tags }
}

function tagNumbers(bytes: Uint8Array, le: boolean, tag: Tag | undefined): number[] {
  if (!tag) return []
  const r = new Reader(bytes, le, tag.at)
  return Array.from({ length: tag.count }, () => (tag.type === 3 ? r.u16() : tag.type === 4 ? r.u32() : r.u8()))
}

function tagBytes(bytes: Uint8Array, tag: Tag | undefined): Uint8Array | null {
  return tag ? bytes.subarray(tag.at, tag.at + tag.count) : null
}

/** The TIFF as a big-endian PSD for ag-psd, with what its layers hold but ag-psd will not see. */
export function readTiffDocument(bytes: Uint8Array): TiffDocument {
  const { le, tags } = readTags(bytes)
  const width = tagNumbers(bytes, le, tags.get(256))[0]
  const height = tagNumbers(bytes, le, tags.get(257))[0]
  const depth = tagNumbers(bytes, le, tags.get(258))[0] ?? 8
  const channels = tagNumbers(bytes, le, tags.get(277))[0] ?? 3
  const photometric = tagNumbers(bytes, le, tags.get(262))[0]
  if (depth !== 8 && depth !== 16) throw new Error(`Only 8 and 16-bit TIFFs can be connected, this one is ${depth}-bit`)

  const hints = new Map<number, LayerHint>()
  const layers = new Writer()
  const source = tagBytes(bytes, tags.get(SOURCE_DATA_TAG))
  // A TIFF saved without layers holds only the flattened image: it reads as
  // a PSD with no layers, which Bridge can still insert into.
  const layerInfo = source ? findLayerInfo(source, le) : null
  if (layerInfo) convertLayerInfo(layerInfo, depth, layers, hints)
  else layers.i16(0)

  // Known limit: a PSD is at most 30000 pixels a side, so a larger TIFF would
  // need a PSB and is refused by ag-psd. Texture documents do not get there.
  const psd = new Writer()
  psd.code("8BPS"); psd.u16(1); psd.push(new Uint8Array(6))
  psd.u16(channels); psd.u32(height); psd.u32(width); psd.u16(depth)
  psd.u16(photometric === 2 ? 3 : photometric === 1 ? 1 : photometric ?? 3)
  psd.u32(0)
  const icc = tagBytes(bytes, tags.get(ICC_PROFILE_TAG))
  const resources = new Writer()
  if (icc) {
    resources.code("8BIM"); resources.u16(1039); resources.u16(0); resources.u32(icc.length); resources.push(icc); resources.pad(2)
  }
  psd.u32(resources.length); psd.push(resources.bytes())
  layers.pad(2)
  psd.u32(4 + layers.length + 4)
  psd.u32(layers.length); psd.push(layers.bytes())
  psd.u32(0)
  // No composite: the mapper reads only layers.
  psd.u16(0)
  return { psd: psd.bytes(), hints }
}

function findLayerInfo(source: Uint8Array, le: boolean): Reader | null {
  const header = new TextDecoder("latin1").decode(source.subarray(0, SOURCE_DATA_HEADER.length))
  if (header !== SOURCE_DATA_HEADER) return null
  const r = new Reader(source, le, SOURCE_DATA_HEADER.length)
  while (r.left() >= 12) {
    // Blocks are padded; realign on the next signature.
    const sig = String.fromCharCode(...source.subarray(r.pos, r.pos + 4))
    if (!["8BIM", "MIB8", "8B64", "46B8"].includes(sig)) { r.pos += 1; continue }
    r.pos += 4
    const key = r.code()
    const length = r.length(sig)
    if (key === "Layr" || key === "Lr16") return new Reader(source, le, r.pos, r.pos + length)
    r.pos += length
  }
  return null
}

type Rect = { top: number; left: number; bottom: number; right: number }
type Channel = { id: number; length: number; data?: Uint8Array }
type LayerRecord = { rect: Rect; channels: Channel[]; head: Writer; extra: Writer; mask: Rect | null; realMask: Rect | null }

function readRect(r: Reader): Rect {
  return { top: r.i32(), left: r.i32(), bottom: r.i32(), right: r.i32() }
}

function writeRect(w: Writer, rect: Rect) {
  w.i32(rect.top); w.i32(rect.left); w.i32(rect.bottom); w.i32(rect.right)
}

function convertLayerInfo(r: Reader, depth: number, out: Writer, hints: Map<number, LayerHint>) {
  const count = r.i16()
  const records: LayerRecord[] = []
  for (let index = 0; index < Math.abs(count); index += 1) records.push(readRecord(r, hints))
  for (const record of records) {
    for (const channel of record.channels) {
      const area = channel.id === -2 ? record.mask : channel.id === -3 ? record.realMask : record.rect
      channel.data = convertChannel(r, channel.length, area, depth)
    }
  }
  out.i16(count)
  for (const record of records) {
    writeRect(out, record.rect)
    out.u16(record.channels.length)
    for (const channel of record.channels) { out.i16(channel.id); out.u32(channel.data!.length) }
    out.push(record.head.bytes())
    out.u32(record.extra.length)
    out.push(record.extra.bytes())
  }
  for (const record of records) for (const channel of record.channels) out.push(channel.data!)
}

function readRecord(r: Reader, hints: Map<number, LayerHint>): LayerRecord {
  const rect = readRect(r)
  const channels: Channel[] = Array.from({ length: r.u16() }, () => ({ id: r.i16(), length: r.u32() }))
  const head = new Writer()
  head.code(r.code()); head.code(r.code())
  head.push(r.take(4))
  const extraLength = r.u32()
  const extraEnd = r.pos + extraLength
  const extra = new Writer()

  const maskLength = r.u32()
  const maskEnd = r.pos + maskLength
  let mask: Rect | null = null
  let realMask: Rect | null = null
  const maskOut = new Writer()
  if (maskLength >= 18) {
    mask = readRect(r)
    writeRect(maskOut, mask)
    maskOut.u8(r.u8())
    const flags = r.u8()
    maskOut.u8(flags)
    // The real mask comes before the parameters, as ag-psd reads them.
    if (maskEnd - r.pos >= 18) {
      maskOut.u8(r.u8()); maskOut.u8(r.u8())
      realMask = readRect(r)
      writeRect(maskOut, realMask)
    }
    if (flags & 16 && r.pos < maskEnd) {
      const parameters = r.u8()
      maskOut.u8(parameters)
      if (parameters & 1) maskOut.u8(r.u8())
      if (parameters & 2) maskOut.push(swap(r.take(8), 8, r.le))
      if (parameters & 4) maskOut.u8(r.u8())
      if (parameters & 8) maskOut.push(swap(r.take(8), 8, r.le))
    }
    if (r.pos < maskEnd) maskOut.push(r.take(maskEnd - r.pos))
  }
  r.pos = maskEnd
  extra.u32(maskOut.length); extra.push(maskOut.bytes())

  const rangesLength = r.u32()
  extra.u32(rangesLength); extra.push(r.take(rangesLength))
  // A Pascal name, padded with its length byte to a multiple of 4.
  const nameLength = r.u8()
  const namePadding = (4 - ((nameLength + 1) % 4)) % 4
  extra.u8(nameLength); extra.push(r.take(nameLength)); extra.push(new Uint8Array(namePadding))
  r.pos += namePadding

  const hint: LayerHint = {}
  let id: number | null = null
  while (extraEnd - r.pos >= 12) {
    const sig = String.fromCharCode(...r.bytes.subarray(r.pos, r.pos + 4))
    if (!["8BIM", "MIB8", "8B64", "46B8"].includes(sig)) { r.pos += 1; continue }
    r.pos += 4
    const key = r.code()
    const length = r.length(sig)
    const block = new Reader(r.bytes, r.le, r.pos, r.pos + length)
    r.pos += length
    const data = new Writer()
    if (key === "luni") {
      const chars = block.u32()
      data.u32(chars)
      for (let index = 0; index < chars; index += 1) data.u16(block.u16())
    } else if (key === "lsct" || key === "lsdk") {
      data.u32(block.u32())
      if (block.left() >= 8) { data.code(block.code()); data.code(block.code()) }
      if (block.left() >= 4) data.u32(block.u32())
    } else if (key === "lyid") {
      id = block.u32()
      data.u32(id)
    } else if (key === "lspf") {
      data.u32(block.u32())
    } else if (key === "iOpa" || key === "clbl" || key === "infx" || key === "knko") {
      data.push(block.take(block.left()))
    } else if (key === "lclr") {
      for (let index = 0; index < 4 && block.left() >= 2; index += 1) data.u16(block.u16())
    } else {
      if (key === "SoCo") hint.vectorFill = solidColor(block) ?? { type: "other" }
      else if (key === "GdFl" || key === "PtFl") hint.vectorFill = { type: "other" }
      else if (key === "vmsk" || key === "vsms") hint.vectorMask = true
      else if (key === "lfx2" || key === "lrFX" || key === "lmfx") hint.effects = true
      else if (ADJUSTMENT_KEYS.has(key)) hint.adjustment = true
      continue
    }
    data.pad(4)
    extra.code("8BIM"); extra.code(key); extra.u32(data.length); extra.push(data.bytes())
  }
  r.pos = extraEnd
  if (id !== null && Object.keys(hint).length) hints.set(id, hint)
  return { rect, channels, head, extra, mask, realMask }
}

function swap(bytes: Uint8Array, size: number, le: boolean): Uint8Array {
  if (!le) return bytes
  const out = new Uint8Array(bytes.length)
  for (let at = 0; at < bytes.length; at += size) {
    for (let index = 0; index < size; index += 1) out[at + index] = bytes[at + size - 1 - index]
  }
  return out
}

function unpackBits(data: Uint8Array, size: number): Uint8Array {
  const out = new Uint8Array(size)
  let read = 0, write = 0
  while (write < size && read < data.length) {
    const n = data[read++]
    if (n < 128) { out.set(data.subarray(read, read + n + 1), write); read += n + 1; write += n + 1 }
    else if (n > 128) { out.fill(data[read++], write, write + 257 - n); write += 257 - n }
  }
  return out
}

/**
 * One channel as ag-psd reads it. 8-bit data compresses byte by byte, so
 * only RLE's row lengths change; 16-bit samples are swapped and deflated.
 */
function convertChannel(r: Reader, length: number, area: Rect | null, depth: number): Uint8Array {
  const end = r.pos + length
  const width = area ? Math.max(0, area.right - area.left) : 0
  const height = area ? Math.max(0, area.bottom - area.top) : 0
  const out = new Writer()
  if (length < 2) { r.pos = end; out.u16(0); return out.bytes() }
  const compression = r.u16()
  const rowBytes = width * (depth / 8)
  if (depth === 8 || width === 0 || height === 0) {
    out.u16(compression)
    if (compression === 1) for (let row = 0; row < height; row += 1) out.u16(r.u16())
    out.push(r.take(end - r.pos))
    return out.bytes()
  }
  let raw: Uint8Array
  if (compression === 0) raw = r.take(end - r.pos)
  else if (compression === 1) {
    const counts = Array.from({ length: height }, () => r.u16())
    raw = new Uint8Array(rowBytes * height)
    counts.forEach((count, row) => raw.set(unpackBits(r.take(count), rowBytes), row * rowBytes))
  } else {
    raw = new Uint8Array(inflateSync(r.take(end - r.pos)))
  }
  r.pos = end
  const values = new DataView(raw.buffer, raw.byteOffset, raw.byteLength)
  const samples = new Uint8Array(rowBytes * height)
  const big = new DataView(samples.buffer)
  for (let row = 0; row < height; row += 1) {
    let previous = 0
    for (let column = 0; column < width; column += 1) {
      const at = row * rowBytes + column * 2
      let value = values.getUint16(at, r.le)
      // Prediction stores each sample as its difference from the previous one.
      if (compression === 3) { value = (value + previous) & 0xffff; previous = value }
      big.setUint16(at, value)
    }
  }
  out.u16(2)
  out.push(new Uint8Array(deflateSync(samples)))
  return out.bytes()
}

/** A solid fill's colour from its descriptor, or null when it is not plain RGB. */
function solidColor(r: Reader): LayerHint["vectorFill"] | null {
  try {
    r.u32()
    const descriptor = readDescriptor(r)
    const colour = descriptor["Clr "] as Record<string, unknown> | undefined
    const channel = (key: string) => Number(colour?.[key])
    if (!colour || [channel("Rd  "), channel("Grn "), channel("Bl  ")].some(Number.isNaN)) return null
    return { type: "color", color: { r: channel("Rd  "), g: channel("Grn "), b: channel("Bl  ") } }
  } catch {
    return null
  }
}

function readUnicode(r: Reader) {
  const length = r.u32()
  return String.fromCharCode(...Array.from({ length }, () => r.u16())).replace(/\0$/, "")
}

function readKey(r: Reader) {
  const length = r.u32()
  return length === 0 ? r.code() : String.fromCharCode(...r.take(length))
}

function readDescriptor(r: Reader): Record<string, unknown> {
  readUnicode(r)
  readKey(r)
  const items: Record<string, unknown> = {}
  const count = r.u32()
  for (let index = 0; index < count; index += 1) {
    const key = readKey(r)
    items[key] = readValue(r, r.code())
  }
  return items
}

function readValue(r: Reader, type: string): unknown {
  switch (type) {
    case "Objc": case "GlbO": return readDescriptor(r)
    case "doub": return r.f64()
    case "UntF": r.code(); return r.f64()
    case "long": return r.i32()
    case "bool": return r.u8() !== 0
    case "TEXT": return readUnicode(r)
    case "enum": readKey(r); return readKey(r)
    case "type": case "GlbC": readUnicode(r); return readKey(r)
    case "VlLs": return Array.from({ length: r.u32() }, () => readValue(r, r.code()))
    case "tdta": return r.take(r.u32())
    default: throw new Error(`Unread descriptor type ${type}`)
  }
}
