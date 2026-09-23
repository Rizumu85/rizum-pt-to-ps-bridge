import { deflateSync } from "node:zlib"

export type RasterImage = {
  width: number
  height: number
  channels: 1 | 4
  bitDepth: 8 | 16
  data: Uint8Array | Uint16Array
}

const SIGNATURE = Uint8Array.of(0x89, 0x50, 0x4e, 0x47, 0x0d, 0x0a, 0x1a, 0x0a)
const CRC_TABLE = (() => {
  const table = new Uint32Array(256)
  for (let n = 0; n < 256; n += 1) {
    let c = n
    for (let k = 0; k < 8; k += 1) c = c & 1 ? 0xedb88320 ^ (c >>> 1) : c >>> 1
    table[n] = c >>> 0
  }
  return table
})()

function crc32(bytes: Uint8Array): number {
  let crc = 0xffffffff
  for (const byte of bytes) crc = CRC_TABLE[(crc ^ byte) & 0xff] ^ (crc >>> 8)
  return (crc ^ 0xffffffff) >>> 0
}

function chunk(type: string, payload: Uint8Array): Uint8Array {
  const out = new Uint8Array(12 + payload.length)
  const view = new DataView(out.buffer)
  view.setUint32(0, payload.length)
  for (let index = 0; index < 4; index += 1) out[4 + index] = type.charCodeAt(index)
  out.set(payload, 8)
  view.setUint32(8 + payload.length, crc32(out.subarray(4, 8 + payload.length)))
  return out
}

// Painter imports these files directly, so 16-bit documents keep 16-bit PNGs
// instead of being quantized for the transfer.
export function encodePng(image: RasterImage): Uint8Array {
  const { width, height, channels, bitDepth, data } = image
  const bytesPerSample = bitDepth / 8
  const stride = width * channels * bytesPerSample
  const raw = new Uint8Array((stride + 1) * height)
  for (let y = 0; y < height; y += 1) {
    const rowStart = y * (stride + 1) + 1
    const sampleStart = y * width * channels
    if (bitDepth === 8) {
      raw.set((data as Uint8Array).subarray(sampleStart, sampleStart + width * channels), rowStart)
    } else {
      for (let x = 0; x < width * channels; x += 1) {
        const value = data[sampleStart + x]
        raw[rowStart + x * 2] = value >> 8
        raw[rowStart + x * 2 + 1] = value & 0xff
      }
    }
  }
  const header = new Uint8Array(13)
  const view = new DataView(header.buffer)
  view.setUint32(0, width)
  view.setUint32(4, height)
  header[8] = bitDepth
  header[9] = channels === 4 ? 6 : 0
  const parts = [
    SIGNATURE,
    chunk("IHDR", header),
    chunk("IDAT", deflateSync(raw, { level: 6 })),
    chunk("IEND", new Uint8Array()),
  ]
  const out = new Uint8Array(parts.reduce((sum, part) => sum + part.length, 0))
  let offset = 0
  for (const part of parts) {
    out.set(part, offset)
    offset += part.length
  }
  return out
}

export function pngDataUrl(image: RasterImage): string {
  return `data:image/png;base64,${Buffer.from(encodePng(image)).toString("base64")}`
}
