import { mkdir, readFile, rm, writeFile } from "node:fs/promises"
import path from "node:path"

import {
  getLayerImageData,
  getLayerMaskImageData,
  initializeCanvas,
  readPsd,
  type BlendMode,
  type Color,
  type Layer,
  type PixelData,
} from "ag-psd"

import type { HostLayerRef, LayerNode } from "./model"
import { encodePng, pngDataUrl, type RasterImage } from "./png"

// ag-psd only needs pixel buffers; the mapper never draws to a canvas.
initializeCanvas(
  () => { throw new Error("PT Bridge reads PSD pixels without a canvas") },
  (width, height) => ({ width, height, data: new Uint8ClampedArray(width * height * 4) }) as ImageData,
)

const THUMBNAIL_SIZE = 36

export type PhotoshopDocument = {
  path: string
  name: string
  width: number
  height: number
  /** PNG depth written for transfers: 8-bit documents stay 8-bit, deeper ones use 16. */
  bitDepth: 8 | 16
  nodes: LayerNode[]
  layers: Map<string, Layer>
  /** Clipped layers per base node id, bottom to top. */
  clipped: Map<string, Layer[]>
  /** Clipped node ids already merged into a base; skipping them is silent. */
  merged: Set<string>
  /** Solid colour fill layers by node id, as sRGB components in 0..1. */
  colors: Map<string, Rgb>
}

type Rgb = [number, number, number]

export type PhotoshopTransferSource = {
  host: "photoshop"
  id: string
  kind: "group" | "layer"
  path: string
  png: string | null
  /** Solid fill colour (sRGB 0..1); Painter keeps it as an editable colour fill. */
  color?: Rgb
  mask_png: string | null
  blend_mode: string
  opacity: number
  visible: boolean
  children?: PhotoshopTransferSource[]
}

/**
 * Reads a PSD/PSB directly so connecting a document never needs Photoshop.
 * The trade-off is that nothing rendered by Photoshop itself comes along:
 * layer styles are dropped, and adjustment or fill layers cannot transfer.
 */
export async function readPhotoshopDocument(psdPath: string): Promise<PhotoshopDocument> {
  const resolved = path.resolve(psdPath)
  const psd = readPsd(await readFile(resolved), {
    useRawData: true,
    useImageData: true,
    skipCompositeImageData: true,
    skipThumbnail: true,
    skipLinkedFilesData: true,
  })
  if (psd.colorMode !== 3) throw new Error("Only RGB Photoshop documents can be connected")
  const document: PhotoshopDocument = {
    path: resolved,
    name: path.basename(resolved),
    width: psd.width,
    height: psd.height,
    bitDepth: (psd.bitsPerChannel ?? 8) <= 8 ? 8 : 16,
    nodes: [],
    layers: new Map(),
    clipped: new Map(),
    merged: new Set(),
    colors: new Map(),
  }
  document.nodes = layerNodes(document, psd.children ?? [], "", [])
  return document
}

function layerNodes(document: PhotoshopDocument, layers: Layer[], parentPath: string, parentIndex: number[]): LayerNode[] {
  // ag-psd lists siblings top to bottom; a clipped layer belongs to the nearest
  // unclipped layer below it, so walk bottom-up to find each clipping base.
  const bases = new Map<Layer, Layer>()
  let base: Layer | null = null
  for (let index = layers.length - 1; index >= 0; index -= 1) {
    const layer = layers[index]
    if (layer.clipping && base) bases.set(layer, base)
    else base = layer
  }

  const nodes = layers.map((layer, index) => {
    const name = layer.name || `Layer ${index + 1}`
    const layerPath = parentPath ? `${parentPath}/${name}` : name
    const indexPath = [...parentIndex, index]
    // Many production PSDs carry no persistent layer id ("lyid"). Their layers
    // are addressed by position and verified by name when Photoshop inserts.
    const id = layer.id !== undefined ? `ps:${layer.id}` : `ps:@${indexPath.join(".")}`
    const ref: HostLayerRef = {
      host: "photoshop",
      externalId: id,
      nativeId: layer.id !== undefined ? String(layer.id) : null,
      kind: layer.children ? "group" : "layer",
      path: layerPath,
      blendMode: layer.blendMode ?? "normal",
      opacity: Math.round((layer.opacity ?? 1) * 100),
      visible: !layer.hidden,
      hasMask: hasMask(layer),
      indexPath,
    }
    const node: LayerNode = {
      id: `photoshop:${id}`,
      kind: layer.children ? "group" : "layer",
      name,
      detail: "",
      masked: hasMask(layer),
      ref,
    }
    document.layers.set(node.id, layer)
    if (layer.children) {
      node.detail = "Group"
      node.children = layerNodes(document, layer.children, layerPath, indexPath)
    }
    return { layer, node }
  })

  const byLayer = new Map(nodes.map(({ layer, node }) => [layer, node]))
  for (const { layer, node } of nodes) {
    const clipBase = bases.get(layer)
    if (clipBase) {
      const baseNode = byLayer.get(clipBase)!
      if (clipBase.children) {
        node.locked = "Clipped to a folder · not supported"
      } else {
        // Painter has no clipping, so the clipped stack travels as one layer.
        node.locked = `Clipped · merges into ${baseNode.name}`
        const list = document.clipped.get(baseNode.id) ?? []
        list.unshift(layer)
        document.clipped.set(baseNode.id, list)
        document.merged.add(node.id)
      }
    }
  }

  for (const { layer, node } of nodes) {
    if (layer.children) continue
    const color = layer.vectorMask ? null : solidFillColor(layer)
    if (layer.adjustment) {
      node.locked = "Adjustment layer · not supported"
    } else if (color) {
      // A solid colour fill stays a colour in Painter instead of a baked bitmap,
      // so it remains editable there; shapes keep their pixels because the
      // vector outline is the content.
      document.colors.set(node.id, color)
      node.thumbnailPath = swatch(color)
    } else if (layer.vectorFill?.type === "color" && !layer.vectorMask) {
      node.locked = "Fill colour model not supported"
    } else {
      const pixels = getLayerImageData(layer)
      if (pixels) node.thumbnailPath = thumbnail(document, layer, pixels)
      else if (layer.vectorMask) node.locked = "Shape layer · not supported"
      else if (layer.vectorFill) node.locked = "Gradient or pattern fill · not supported"
      else node.locked = "Empty layer"
    }
    node.detail = node.locked
      ?? layerDetail(layer, document.clipped.get(node.id)?.length ?? 0, Boolean(color))
    node.note = transferNote(layer, document.clipped.get(node.id)?.length ?? 0, Boolean(color))
  }
  return nodes.map(({ node }) => node)
}

function layerDetail(layer: Layer, clippedCount: number, colorFill: boolean): string {
  const parts = [`${humanize(layer.blendMode ?? "normal")} · ${Math.round((layer.opacity ?? 1) * 100)}%`]
  if (colorFill) parts.push("colour fill")
  if (clippedCount) parts.push(`merges ${clippedCount} clipped`)
  if (layer.effects && !layer.effects.disabled) parts.push("styles not transferred")
  return parts.join(" · ")
}

function transferNote(layer: Layer, clippedCount: number, colorFill: boolean): string | undefined {
  const parts = []
  if (colorFill) parts.push("Colour fill")
  if (clippedCount) parts.push(`Merges ${clippedCount} clipped`)
  if (layer.effects && !layer.effects.disabled) parts.push("Styles not transferred")
  return parts.length ? parts.join(" · ") : undefined
}

function humanize(value: string): string {
  return value.replace(/\b\w/g, (letter) => letter.toUpperCase())
}

function hasMask(layer: Layer): boolean {
  return Boolean(layer.mask && !layer.mask.disabled)
}

function solidFillColor(layer: Layer): Rgb | null {
  if (layer.vectorFill?.type !== "color") return null
  return rgbFromDescriptor(layer.vectorFill.color)
}

/** Photoshop descriptor colours: RGB 0-255, HSB degrees/percent, Gray as % black. */
function rgbFromDescriptor(color: Color): Rgb | null {
  if ("r" in color) return [color.r / 255, color.g / 255, color.b / 255]
  if ("fr" in color) return [color.fr, color.fg, color.fb]
  if ("h" in color) {
    const h = (((color.h % 360) + 360) % 360) / 60
    const s = color.s / 100
    const v = color.b / 100
    const f = (n: number) => {
      const k = (n + h) % 6
      return v - v * s * Math.max(0, Math.min(k, 4 - k, 1))
    }
    return [f(5), f(3), f(1)]
  }
  if ("k" in color && !("c" in color)) {
    const value = 1 - color.k / 100
    return [value, value, value]
  }
  return null
}

function swatch(color: Rgb): string {
  const size = 4
  const data = new Uint8Array(size * size * 4)
  for (let index = 0; index < data.length; index += 4) {
    data.set([...color.map((value) => Math.round(clamp(value) * 255)), 255], index)
  }
  return pngDataUrl({ width: size, height: size, channels: 4, bitDepth: 8, data })
}

function thumbnail(document: PhotoshopDocument, layer: Layer, pixels: PixelData): string {
  const size = THUMBNAIL_SIZE
  const data = new Uint8Array(size * size * 4)
  const left = layer.left ?? 0
  const top = layer.top ?? 0
  const max = maxSample(pixels)
  for (let y = 0; y < size; y += 1) {
    const sy = Math.floor(((y + 0.5) / size) * document.height) - top
    if (sy < 0 || sy >= pixels.height) continue
    for (let x = 0; x < size; x += 1) {
      const sx = Math.floor(((x + 0.5) / size) * document.width) - left
      if (sx < 0 || sx >= pixels.width) continue
      const source = (sy * pixels.width + sx) * 4
      const target = (y * size + x) * 4
      for (let channel = 0; channel < 4; channel += 1) {
        data[target + channel] = Math.round(sampleUnit(pixels, source + channel, channel, max) * 255)
      }
    }
  }
  return pngDataUrl({ width: size, height: size, channels: 4, bitDepth: 8, data })
}

/**
 * Renders a mapped Photoshop node into the PNG files Painter imports. A folder
 * becomes a Painter folder with the children it still holds in the mapping
 * preview (a child mapped on its own was already moved out and must not be
 * sent twice). Locked nodes are skipped and reported, except clipped layers,
 * which are already merged into their base.
 */
export async function renderPhotoshopTransfer(
  document: PhotoshopDocument,
  node: LayerNode,
  directory: string,
  warnings: string[],
): Promise<PhotoshopTransferSource | null> {
  const layer = document.layers.get(node.id)
  if (!layer) throw new Error(`Photoshop layer is no longer in ${document.name}`)
  if (node.locked) {
    if (!document.merged.has(node.id)) warnings.push(`${node.name}: ${node.locked}, skipped.`)
    return null
  }
  await mkdir(directory, { recursive: true })
  const stem = path.join(directory, `${safeName(node.name)}_${safeName(node.ref.externalId)}`)
  const record: PhotoshopTransferSource = {
    host: "photoshop",
    id: node.ref.nativeId ?? node.ref.externalId,
    kind: node.kind,
    path: node.ref.path,
    png: null,
    mask_png: hasMask(layer) ? await writeRaster(`${stem}_mask.png`, maskCanvas(document, layer)) : null,
    blend_mode: layer.blendMode ?? "normal",
    opacity: Math.round((layer.opacity ?? 1) * 100),
    visible: !layer.hidden,
  }
  if (node.kind === "group") {
    const children = []
    for (const child of node.children ?? []) {
      const rendered = await renderPhotoshopTransfer(document, child, directory, warnings)
      if (rendered) children.push(rendered)
    }
    record.children = children
    return record
  }
  const clipped = document.clipped.get(node.id) ?? []
  const color = document.colors.get(node.id)
  if (color && clipped.length === 0) {
    record.color = color
    return record
  }
  record.png = await writeRaster(`${stem}.png`, layerCanvas(document, layer, clipped, color))
  return record
}

export async function clearTransferDirectory(directory: string): Promise<void> {
  await rm(directory, { recursive: true, force: true })
}

function safeName(value: string): string {
  return value.replace(/[^\p{L}\p{N}._-]+/gu, "_").slice(0, 48) || "layer"
}

async function writeRaster(filePath: string, image: RasterImage): Promise<string> {
  await writeFile(filePath, encodePng(image))
  return filePath
}

function newCanvas(document: PhotoshopDocument, channels: 1 | 4): RasterImage {
  const length = document.width * document.height * channels
  return {
    width: document.width,
    height: document.height,
    channels,
    bitDepth: document.bitDepth,
    data: document.bitDepth === 8 ? new Uint8Array(length) : new Uint16Array(length),
  }
}

function layerCanvas(document: PhotoshopDocument, base: Layer, clipped: Layer[], color?: Rgb): RasterImage {
  const canvas = newCanvas(document, 4)
  const scale = document.bitDepth === 8 ? 255 : 65535
  if (color) {
    // A colour fill covers the canvas; its mask is transferred separately.
    const pixel = [...color.map((value) => Math.round(clamp(value) * scale)), scale]
    for (let index = 0; index < canvas.data.length; index += 4) canvas.data.set(pixel, index)
  } else {
    const pixels = getLayerImageData(base)
    if (!pixels) return canvas
    const baseMax = maxSample(pixels)
    eachPixel(document, base, pixels, (target, source) => {
      for (let channel = 0; channel < 4; channel += 1) {
        canvas.data[target + channel] = Math.round(sampleUnit(pixels, source + channel, channel, baseMax) * scale)
      }
    })
  }
  for (const layer of clipped) {
    if (layer.hidden) continue
    const source = getLayerImageData(layer)
    if (!source) continue
    const mask = hasMask(layer) ? maskCanvas(document, layer) : null
    const opacity = (layer.opacity ?? 1) * (layer.fillOpacity ?? 1)
    const blend = blendFunction(layer.blendMode ?? "normal")
    const max = maxSample(source)
    const backdrop = [0, 0, 0]
    const color = [0, 0, 0]
    eachPixel(document, layer, source, (target, offset) => {
      const baseAlpha = canvas.data[target + 3] / scale
      if (baseAlpha === 0) return
      const pixelIndex = target / 4
      const coverage = sampleUnit(source, offset + 3, 3, max) * opacity
        * (mask ? mask.data[pixelIndex] / scale : 1)
      if (coverage === 0) return
      for (let channel = 0; channel < 3; channel += 1) {
        backdrop[channel] = canvas.data[target + channel] / scale
        color[channel] = sampleUnit(source, offset + channel, channel, max)
      }
      // A clipped layer only paints inside its base, so the base alpha stays.
      const blended = blend(backdrop, color)
      for (let channel = 0; channel < 3; channel += 1) {
        const value = backdrop[channel] + (blended[channel] - backdrop[channel]) * coverage
        canvas.data[target + channel] = Math.round(clamp(value) * scale)
      }
    })
  }
  return canvas
}

function maskCanvas(document: PhotoshopDocument, layer: Layer): RasterImage {
  const canvas = newCanvas(document, 1)
  const scale = document.bitDepth === 8 ? 255 : 65535
  const mask = layer.mask!
  canvas.data.fill(Math.round(((mask.defaultColor ?? 0) / 255) * scale))
  const pixels = getLayerMaskImageData(layer)
  if (!pixels) return canvas
  const max = maxSample(pixels)
  const left = mask.left ?? 0
  const top = mask.top ?? 0
  for (let y = 0; y < pixels.height; y += 1) {
    const cy = top + y
    if (cy < 0 || cy >= document.height) continue
    for (let x = 0; x < pixels.width; x += 1) {
      const cx = left + x
      if (cx < 0 || cx >= document.width) continue
      const value = sampleUnit(pixels, (y * pixels.width + x) * 4, 3, max)
      canvas.data[cy * document.width + cx] = Math.round(value * scale)
    }
  }
  return canvas
}

function eachPixel(
  document: PhotoshopDocument,
  layer: Layer,
  pixels: PixelData,
  visit: (target: number, source: number) => void,
): void {
  const left = layer.left ?? 0
  const top = layer.top ?? 0
  for (let y = 0; y < pixels.height; y += 1) {
    const cy = top + y
    if (cy < 0 || cy >= document.height) continue
    for (let x = 0; x < pixels.width; x += 1) {
      const cx = left + x
      if (cx < 0 || cx >= document.width) continue
      visit((cy * document.width + cx) * 4, (y * pixels.width + x) * 4)
    }
  }
}

function maxSample(pixels: PixelData): number {
  if (pixels.data instanceof Float32Array) return 1
  return pixels.data instanceof Uint16Array ? 65535 : 255
}

/**
 * Normalizes one sample. Masks and alpha pass through; 32-bit colour is
 * linear in PSD files and is encoded to sRGB like the 8/16-bit documents.
 */
function sampleUnit(pixels: PixelData, index: number, channel: number, max: number): number {
  const value = pixels.data[index] / max
  if (!(pixels.data instanceof Float32Array) || channel === 3) return value
  return value <= 0.0031308 ? value * 12.92 : 1.055 * value ** (1 / 2.4) - 0.055
}

function clamp(value: number): number {
  return value < 0 ? 0 : value > 1 ? 1 : value
}

type Blend = (backdrop: number[], source: number[]) => number[]

function separable(mix: (b: number, s: number) => number): Blend {
  return (backdrop, source) => backdrop.map((b, index) => mix(b, source[index]))
}

const multiply = (b: number, s: number) => b * s
const screen = (b: number, s: number) => b + s - b * s
const colorDodge = (b: number, s: number) => (b === 0 ? 0 : s >= 1 ? 1 : Math.min(1, b / (1 - s)))
const colorBurn = (b: number, s: number) => (b >= 1 ? 1 : s <= 0 ? 0 : 1 - Math.min(1, (1 - b) / s))
const hardLight = (b: number, s: number) => (s <= 0.5 ? multiply(b, 2 * s) : screen(b, 2 * s - 1))
const softLight = (b: number, s: number) => {
  if (s <= 0.5) return b - (1 - 2 * s) * b * (1 - b)
  const d = b <= 0.25 ? ((16 * b - 12) * b + 4) * b : Math.sqrt(b)
  return b + (2 * s - 1) * (d - b)
}
const vividLight = (b: number, s: number) => (s <= 0.5 ? colorBurn(b, 2 * s) : colorDodge(b, 2 * s - 1))
const pinLight = (b: number, s: number) => (s <= 0.5 ? Math.min(b, 2 * s) : Math.max(b, 2 * s - 1))

const lum = (c: number[]) => 0.3 * c[0] + 0.59 * c[1] + 0.11 * c[2]
const sat = (c: number[]) => Math.max(...c) - Math.min(...c)
function clipColor(c: number[]): number[] {
  const l = lum(c)
  const n = Math.min(...c)
  const x = Math.max(...c)
  return c.map((value) => {
    let out = value
    if (n < 0) out = l + ((out - l) * l) / (l - n)
    if (x > 1) out = l + ((out - l) * (1 - l)) / (x - l)
    return out
  })
}
function setLum(c: number[], l: number): number[] {
  const d = l - lum(c)
  return clipColor(c.map((value) => value + d))
}
function setSat(c: number[], s: number): number[] {
  const max = Math.max(...c)
  const min = Math.min(...c)
  if (max === min) return [0, 0, 0]
  return c.map((value) => (value === max ? s : value === min ? 0 : ((value - min) * s) / (max - min)))
}

// Photoshop blends in document (sRGB-encoded) space; these follow its published
// mode definitions so a clipped stack merges the way the artist saw it.
const BLENDS: Partial<Record<BlendMode, Blend>> = {
  darken: separable(Math.min),
  multiply: separable(multiply),
  "color burn": separable(colorBurn),
  "linear burn": separable((b, s) => Math.max(0, b + s - 1)),
  "darker color": (b, s) => (lum(s) < lum(b) ? s : b),
  lighten: separable(Math.max),
  screen: separable(screen),
  "color dodge": separable(colorDodge),
  "linear dodge": separable((b, s) => Math.min(1, b + s)),
  "lighter color": (b, s) => (lum(s) > lum(b) ? s : b),
  overlay: separable((b, s) => hardLight(s, b)),
  "soft light": separable(softLight),
  "hard light": separable(hardLight),
  "vivid light": separable(vividLight),
  "linear light": separable((b, s) => clamp(b + 2 * s - 1)),
  "pin light": separable(pinLight),
  "hard mix": separable((b, s) => (vividLight(b, s) < 0.5 ? 0 : 1)),
  difference: separable((b, s) => Math.abs(b - s)),
  exclusion: separable((b, s) => b + s - 2 * b * s),
  subtract: separable((b, s) => Math.max(0, b - s)),
  divide: separable((b, s) => (s <= 0 ? 1 : Math.min(1, b / s))),
  hue: (b, s) => setLum(setSat(s, sat(b)), lum(b)),
  saturation: (b, s) => setLum(setSat(b, sat(s)), lum(b)),
  color: (b, s) => setLum(s, lum(b)),
  luminosity: (b, s) => setLum(b, lum(s)),
}

function blendFunction(mode: BlendMode): Blend {
  return BLENDS[mode] ?? ((_backdrop, source) => source)
}
