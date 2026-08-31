import { existsSync } from "node:fs"
import { dirname, join, resolve } from "node:path"

import { dlopen, FFIType } from "bun:ffi"

const FR_PRIVATE = 0x10
const bundledFonts = ["MiSans VF.ttf"] as const

function fontDirectory(): string {
  const runsFromCompiledBundle = import.meta.path
    .replaceAll("\\", "/")
    .includes("/~BUN/root/")
  return runsFromCompiledBundle
    ? join(dirname(process.execPath), "fonts")
    : resolve(import.meta.dir, "../fonts")
}

export function registerBundledFonts(): void {
  if (process.platform !== "win32") {
    throw new Error("PT Bridge Desktop currently requires Windows font registration")
  }

  const gdi32 = dlopen("gdi32.dll", {
    AddFontResourceExW: {
      args: [FFIType.ptr, FFIType.u32, FFIType.ptr],
      returns: FFIType.i32,
    },
  })

  for (const filename of bundledFonts) {
    const path = join(fontDirectory(), filename)
    if (!existsSync(path)) throw new Error(`Bundled font is missing: ${path}`)

    // Process-private registration keeps the licensed font scoped to PT Bridge
    // while letting GPUI discover it before the renderer creates its text system.
    const widePath = Buffer.from(`${path}\0`, "utf16le")
    const added = gdi32.symbols.AddFontResourceExW(widePath, FR_PRIVATE, null)
    if (added === 0) throw new Error(`Could not register bundled font: ${filename}`)
  }
}
