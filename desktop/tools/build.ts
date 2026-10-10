import { dlopen, FFIType } from "bun:ffi"
import { copyFile, cp, mkdir, readFile } from "node:fs/promises"
import { join, resolve } from "node:path"

const root = resolve(import.meta.dir, "..")
const dist = join(root, "dist")

await mkdir(dist, { recursive: true })

// GPUiX 0.10's ESM loader requires its .node addon through createRequire,
// which the compiler cannot follow, so the exe shipped without it and failed
// at startup. The package's CommonJS loader uses a plain require that gets
// embedded. Drop this redirect once GPUiX's ESM entry compiles on its own.
const nativeLoader: import("bun").BunPlugin = {
  name: "gpuix-native-cjs",
  setup(build) {
    build.onResolve({ filter: /^@gpuix\/native$/ }, () => ({
      path: join(root, "node_modules", "@gpuix", "native", "index.cjs"),
    }))
  },
}

const result = await Bun.build({
  entrypoints: [join(root, "src/main.tsx")],
  compile: { outfile: join(dist, "pt-bridge") },
  plugins: [nativeLoader],
})
if (!result.success) {
  for (const log of result.logs) console.error(log)
  process.exit(1)
}

// Bun's `windows.icon` option is not used: it files the icon under group id 0
// and leaves its stock "IDI_MYICON" group pointing at the replaced images, so
// Explorer stretched the 16px one, and GPUI only loads the window icon from
// group id 1, so the window had none. Both groups are written here instead.
async function embedIcon(exe: string, ico: string) {
  const file = await readFile(ico)
  const count = file.readUInt16LE(4)
  const group = Buffer.alloc(6 + 14 * count)
  file.copy(group, 0, 0, 6)
  const { symbols: kernel } = dlopen("kernel32.dll", {
    BeginUpdateResourceW: { args: [FFIType.ptr, FFIType.i32], returns: FFIType.ptr },
    UpdateResourceW: {
      args: [FFIType.ptr, FFIType.ptr, FFIType.ptr, FFIType.u16, FFIType.ptr, FFIType.u32],
      returns: FFIType.i32,
    },
    EndUpdateResourceW: { args: [FFIType.ptr, FFIType.i32], returns: FFIType.i32 },
  })
  const wide = (text: string) => new Uint8Array(Buffer.from(`${text}\0`, "utf16le"))
  const imageType = 3, groupType = 14, language = 1033
  const update = kernel.BeginUpdateResourceW(wide(exe), 0)
  let written = update !== null
  for (let index = 0; written && index < count; index += 1) {
    const entry = 6 + 16 * index
    const start = file.readUInt32LE(entry + 12)
    const image = new Uint8Array(file.subarray(start, start + file.readUInt32LE(entry + 8)))
    file.copy(group, 6 + 14 * index, entry, entry + 12)
    group.writeUInt16LE(index + 1, 6 + 14 * index + 12)
    written = kernel.UpdateResourceW(update, imageType, index + 1, language, image, image.length) !== 0
  }
  for (const name of [wide("IDI_MYICON"), 1]) {
    written = written && kernel.UpdateResourceW(update, groupType, name, language, new Uint8Array(group), group.length) !== 0
  }
  if (update !== null && !kernel.EndUpdateResourceW(update, written ? 0 : 1)) written = false
  if (!written) throw new Error(`Could not write the icon into ${exe}`)
}
await embedIcon(join(dist, "pt-bridge.exe"), join(root, "assets", "pt-bridge.ico"))

// The unmodified font and its license travel beside the executable so private
// registration never depends on a user's installed-font library.
await cp(join(root, "fonts"), join(dist, "fonts"), { recursive: true, force: true })
await copyFile(
  join(root, "THIRD-PARTY-NOTICES.txt"),
  join(dist, "THIRD-PARTY-NOTICES.txt"),
)
