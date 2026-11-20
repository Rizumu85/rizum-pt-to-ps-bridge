import { mkdir, readFile, rm, writeFile } from "node:fs/promises"
import path from "node:path"

import {
  getLayerImageData,
  getLayerMaskImageData,
  initializeCanvas,
  readPsd,
  type Color,
  type Layer,
  type PixelData,
} from "ag-psd"

import { t } from "./i18n"
import { isTiff, readTiffDocument, type LayerHint } from "./tiff"
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
  clipped: Map<string, LayerNode[]>
  /** Solid colour fill layers by node id, as sRGB components in 0..1. */
  colors: Map<string, Rgb>
  /** Of those, raster layers painted in one colour: their alpha is their shape. */
  rasterColors: Set<string>
}

type Rgb = [number, number, number]

export type PhotoshopTransferSource = {
  host: "photoshop"
  id: string
  kind: "group" | "layer"
  name: string
  path: string
  png: string | null
  /** Solid fill colour (sRGB 0..1); Painter keeps it as an editable colour fill. */
  color?: Rgb
  mask_png: string | null
  blend_mode: string
  opacity: number
  visible: boolean
  children?: PhotoshopTransferSource[]
  clipped?: PhotoshopTransferSource[]
}

/**
 * Reads a PSD/PSB, or a layered TIFF, directly so connecting a document never
 * needs Photoshop. The trade-off is that nothing rendered by Photoshop itself
 * comes along: layer styles are dropped, and adjustment or fill layers cannot
 * transfer.
 */
export async function readPhotoshopDocument(psdPath: string): Promise<PhotoshopDocument> {
  const resolved = path.resolve(psdPath)
  const bytes = await readFile(resolved)
  const tiff = isTiff(bytes) ? readTiffDocument(bytes) : null
  const psd = readPsd(tiff?.psd ?? bytes, {
    useRawData: true,
    useImageData: true,
    skipCompositeImageData: true,
    skipThumbnail: true,
    skipLinkedFilesData: true,
  })
  if (psd.colorMode !== 3) throw new Error(t("Only RGB Photoshop documents can be connected"))
  if (tiff) applyTiffHints(psd.children, tiff.hints)
  const document: PhotoshopDocument = {
    path: resolved,
    name: path.basename(resolved),
    width: psd.width,
    height: psd.height,
    bitDepth: (psd.bitsPerChannel ?? 8) <= 8 ? 8 : 16,
    nodes: [],
    layers: new Map(),
    clipped: new Map(),
    colors: new Map(),
    rasterColors: new Set(),
  }
  document.nodes = layerNodes(document, psd.children ?? [], "", [])
  return document
}

function layerNodes(document: PhotoshopDocument, layers: Layer[], parentPath: string, parentIndex: number[]): LayerNode[] {
  // ag-psd keeps the file's order, bottom to top. The mapper, Painter and
  // Photoshop scripting (document.layers, which index_path walks) all read
  // top to bottom, so siblings flip here and nowhere else. A clipped layer
  // belongs to the nearest unclipped layer below it: the one before it here.
  let base: LayerNode | undefined
  const nodes = layers.map((layer, fileIndex) => {
    const index = layers.length - fileIndex - 1
    const name = layer.name || t("Layer {index}", { index: layers.length - index })
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
      name,
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
      masked: hasMask(layer),
      ref,
    }
    document.layers.set(node.id, layer)
    if (layer.children) {
      node.children = layerNodes(document, layer.children, layerPath, indexPath)
      node.open = layer.opened !== false
    } else {
      const color = layer.vectorMask ? null : solidFillColor(layer)
      if (layer.adjustment) {
        node.unsupported = t("Adjustment layer · not supported")
      } else if (color) {
        document.colors.set(node.id, color)
        node.thumbnailPath = swatch(color)
      } else if (layer.vectorFill?.type === "color" && !layer.vectorMask) {
        node.unsupported = t("Fill colour model not supported")
      } else {
        const pixels = getLayerImageData(layer)
        // CSP saves a layer filled with one colour as pixels, not as a fill
        // layer. The user wanted it back as a colour they can change in
        // Painter, so any layer whose covered pixels share one colour goes
        // over as a colour fill, its alpha becoming the mask.
        const flat = pixels && uniformColor(pixels)
        if (flat) {
          document.colors.set(node.id, flat)
          document.rasterColors.add(node.id)
        }
        if (pixels) node.thumbnailPath = thumbnail(document, layer, pixels)
        else if (layer.vectorMask) node.unsupported = t("Shape layer · not supported")
        else if (layer.vectorFill) node.unsupported = t("Gradient or pattern fill · not supported")
        else node.unsupported = t("Empty layer")
      }
    }
    if (layer.clipping && base) {
      node.clipped = base.kind
      if (base.kind === "group") {
        node.unsupported ??= t("Clipped to a folder · not supported")
      } else {
        const list = document.clipped.get(base.id) ?? []
        list.push(node)
        document.clipped.set(base.id, list)
        node.locked = t("Clipped to {name} · goes with it", { name: base.name })
      }
    } else {
      base = node
    }
    node.locked = node.unsupported ?? node.locked
    return node
  })
  for (const [index, node] of nodes.entries()) {
    if (node.kind === "layer") {
      node.note = transferNote(layers[index], document.clipped.get(node.id)?.length ?? 0, document.colors.has(node.id))
    }
  }
  return nodes.reverse()
}

function transferNote(layer: Layer, clippedCount: number, colorFill: boolean): string | undefined {
  const parts = []
  if (colorFill) parts.push(t("Colour fill"))
  if (clippedCount) parts.push(t("Brings {count} clipped", { count: clippedCount }))
  if (layer.effects && !layer.effects.disabled) parts.push(t("Styles not transferred"))
  return parts.length ? parts.join(" · ") : undefined
}

function hasMask(layer: Layer): boolean {
  return Boolean(layer.mask && !layer.mask.disabled)
}

/** What a TIFF's layers hold that only Photoshop renders, set as reading a PSD would. */
function applyTiffHints(layers: Layer[] | undefined, hints: Map<number, LayerHint>) {
  for (const layer of layers ?? []) {
    const hint = layer.id === undefined ? undefined : hints.get(layer.id)
    if (hint?.adjustment) layer.adjustment = { type: "unknown" } as unknown as Layer["adjustment"]
    if (hint?.effects) layer.effects = {}
    if (hint?.vectorMask) layer.vectorMask = { paths: [] }
    if (hint?.vectorFill) layer.vectorFill = hint.vectorFill as Layer["vectorFill"]
    applyTiffHints(layer.children, hints)
  }
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
 * sent twice). A clipped row travels with its base even when only the base
 * was mapped.
 */
export async function renderPhotoshopTransfer(
  document: PhotoshopDocument,
  node: LayerNode,
  directory: string,
  warnings: string[],
  baseOpacity = 1,
): Promise<PhotoshopTransferSource | null> {
  const layer = document.layers.get(node.id)
  if (!layer) throw new Error(t("Photoshop layer is no longer in {name}", { name: document.name }))
  if (node.unsupported) {
    warnings.push(t("{name}: {reason}, skipped.", { name: node.name, reason: node.unsupported }))
    return null
  }
  await mkdir(directory, { recursive: true })
  const stem = path.join(directory, `${safeName(node.name)}_${safeName(node.ref.externalId)}`)
  const record: PhotoshopTransferSource = {
    host: "photoshop",
    id: node.ref.nativeId ?? node.ref.externalId,
    kind: node.kind,
    name: node.name,
    path: node.ref.path,
    png: null,
    mask_png: hasMask(layer) ? await writeRaster(`${stem}_mask.png`, maskCanvas(document, layer)) : null,
    blend_mode: layer.blendMode ?? "normal",
    opacity: Math.round((layer.opacity ?? 1) * baseOpacity * 100),
    visible: !layer.hidden,
  }
  if (node.kind === "group") {
    const children = []
    for (const child of node.children ?? []) {
      if (child.clipped === "layer") continue
      const rendered = await renderPhotoshopTransfer(document, child, directory, warnings)
      if (rendered) children.push(rendered)
    }
    record.children = children
    return record
  }
  const color = document.colors.get(node.id)
  if (color) record.color = color
  else record.png = await writeRaster(`${stem}.png`, layerCanvas(document, layer))
  if (document.rasterColors.has(node.id)) {
    const coverage = coverageCanvas(document, layer)
    record.mask_png = coverage ? await writeRaster(`${stem}_mask.png`, coverage) : record.mask_png
  }
  const clipped = document.clipped.get(node.id)
  if (clipped) {
    record.clipped = []
    for (const child of clipped) {
      const rendered = await renderPhotoshopTransfer(document, child, directory, warnings, layer.opacity ?? 1)
      if (rendered) record.clipped.push(rendered)
    }
    if (record.clipped.length && record.blend_mode !== "normal") {
      warnings.push(t("{name}: in Painter its clipped layers blend on their own.", { name: node.name }))
    }
  }
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

function layerCanvas(document: PhotoshopDocument, layer: Layer): RasterImage {
  const canvas = newCanvas(document, 4)
  const scale = document.bitDepth === 8 ? 255 : 65535
  const pixels = getLayerImageData(layer)!
  const max = maxSample(pixels)
  eachPixel(document, layer, pixels, (target, source) => {
    for (let channel = 0; channel < 4; channel += 1) {
      canvas.data[target + channel] = Math.round(sampleUnit(pixels, source + channel, channel, max) * scale)
    }
  })
  return canvas
}

/** The colour every covered pixel shares, or null when they differ. */
function uniformColor(pixels: PixelData): Rgb | null {
  const data = pixels.data
  const max = maxSample(pixels)
  let first = -1
  for (let index = 0; index < data.length; index += 4) {
    if (data[index + 3] === 0) continue
    if (first < 0) first = index
    else if (data[index] !== data[first] || data[index + 1] !== data[first + 1] || data[index + 2] !== data[first + 2]) return null
  }
  return first < 0 ? null : [data[first] / max, data[first + 1] / max, data[first + 2] / max]
}

/** A raster layer's alpha times its mask on the canvas, or null where it covers all of it. */
function coverageCanvas(document: PhotoshopDocument, layer: Layer): RasterImage | null {
  const canvas = newCanvas(document, 1)
  const scale = document.bitDepth === 8 ? 255 : 65535
  const pixels = getLayerImageData(layer)!
  const max = maxSample(pixels)
  eachPixel(document, layer, pixels, (target, source) => {
    canvas.data[target / 4] = Math.round(sampleUnit(pixels, source + 3, 3, max) * scale)
  })
  if (hasMask(layer)) {
    const mask = maskCanvas(document, layer)
    for (let index = 0; index < canvas.data.length; index += 1) {
      canvas.data[index] = Math.round((canvas.data[index] * mask.data[index]) / scale)
    }
  }
  return canvas.data.every(value => value === scale) ? null : canvas
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
