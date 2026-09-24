import { copyFile, cp, mkdir } from "node:fs/promises"
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

// The unmodified font and its license travel beside the executable so private
// registration never depends on a user's installed-font library.
await cp(join(root, "fonts"), join(dist, "fonts"), { recursive: true, force: true })
await copyFile(
  join(root, "THIRD-PARTY-NOTICES.txt"),
  join(dist, "THIRD-PARTY-NOTICES.txt"),
)
