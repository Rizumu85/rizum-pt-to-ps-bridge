import { mkdtemp, writeFile } from "node:fs/promises"
import os from "node:os"
import path from "node:path"

import { writePsdBuffer } from "ag-psd"

import "./psd"

/** A PSD exercising clipping, styles, adjustment and fill layers. */
export async function writeFeaturePsd(): Promise<string> {
  const size = 4
  const fill = (rgba: number[]) => {
    const data = new Uint8ClampedArray(size * size * 4)
    for (let index = 0; index < data.length; index += 4) data.set(rgba, index)
    return { width: size, height: size, data }
  }
  const directory = await mkdtemp(path.join(os.tmpdir(), "pt-bridge-feature-psd-"))
  const file = path.join(directory, "features.psd")
  await writeFile(file, writePsdBuffer({
    width: size,
    height: size,
    children: [
      {
        id: 10, name: "Paint", blendMode: "pass through", children: [
          { id: 12, name: "Shade", blendMode: "multiply", clipping: true, top: 0, left: 0, imageData: fill([128, 128, 128, 255]) },
          {
            id: 11, name: "Base", blendMode: "normal", top: 0, left: 0, imageData: fill([255, 0, 0, 255]),
            effects: { dropShadow: [{ enabled: true }] },
          },
        ],
      },
      { id: 20, name: "Levels", adjustment: { type: "levels" } },
      {
        id: 30, name: "Tint", blendMode: "multiply", vectorFill: { type: "color", color: { r: 255, g: 128, b: 0 } },
        mask: { top: 0, left: 0, bottom: size, right: size, defaultColor: 0, imageData: fill([255, 255, 255, 255]) },
      },
      { id: 40, name: "Glow", blendMode: "hard mix", top: 0, left: 0, imageData: fill([255, 255, 255, 255]) },
      {
        id: 31, name: "Ramp", vectorFill: {
          type: "solid", name: "", style: "linear", colorStops: [], opacityStops: [],
        } as never,
      },
    ],
  }, { generateThumbnail: false, noBackground: true }))
  return file
}
