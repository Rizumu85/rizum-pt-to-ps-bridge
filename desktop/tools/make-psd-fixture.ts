import { writeFileSync } from "node:fs"
import path from "node:path"

import { writePsdBuffer, type Layer } from "ag-psd"

import "../src/psd"

// Regenerates test-fixtures/photoshop_document.psd, the connected document the
// desktop tests and tools load: two masked/unmasked layers, a plain layer and
// an empty folder, with stable Photoshop layer ids 100-103.
const size = 64

function solid(r: number, g: number, b: number, a = 255) {
  const data = new Uint8ClampedArray(size * size * 4)
  for (let index = 0; index < data.length; index += 4) data.set([r, g, b, a], index)
  return { width: size, height: size, data }
}

function halfMask() {
  const data = new Uint8ClampedArray(size * size * 4)
  for (let index = 0; index < size * size; index += 1) {
    const value = index % size < size / 2 ? 255 : 0
    data.set([value, value, value, 255], index * 4)
  }
  return { width: size, height: size, data }
}

const children: Layer[] = [
  { id: 100, name: "Paint edit", blendMode: "normal", opacity: 1, top: 0, left: 0, imageData: solid(200, 80, 60) },
  {
    id: 101, name: "Color pass", blendMode: "overlay", opacity: 0.65, top: 0, left: 0, imageData: solid(40, 120, 220),
    mask: { top: 0, left: 0, bottom: size, right: size, defaultColor: 0, imageData: halfMask() },
  },
  { id: 102, name: "Mask cleanup", blendMode: "normal", opacity: 1, top: 0, left: 0, imageData: solid(255, 255, 255, 128) },
  { id: 103, name: "Retouch group", blendMode: "pass through", opacity: 1, children: [] },
]

const buffer = writePsdBuffer(
  { width: size, height: size, children },
  { generateThumbnail: false, noBackground: true },
)
const output = path.resolve(import.meta.dir, "../test-fixtures/photoshop_document.psd")
writeFileSync(output, buffer)
console.log(`Wrote ${output} (${buffer.length} bytes)`)
