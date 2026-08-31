import { copyFile, cp, mkdir } from "node:fs/promises"
import { join, resolve } from "node:path"

const root = resolve(import.meta.dir, "..")
const dist = join(root, "dist")

await mkdir(dist, { recursive: true })

const compiler = Bun.spawn(
  [process.execPath, "build", "--compile", "src/main.tsx", "--outfile", "dist/pt-bridge"],
  {
    cwd: root,
    stdout: "inherit",
    stderr: "inherit",
  },
)

const exitCode = await compiler.exited
if (exitCode !== 0) process.exit(exitCode)

// The unmodified font and its license travel beside the executable so private
// registration never depends on a user's installed-font library.
await cp(join(root, "fonts"), join(dist, "fonts"), { recursive: true, force: true })
await copyFile(
  join(root, "THIRD-PARTY-NOTICES.txt"),
  join(dist, "THIRD-PARTY-NOTICES.txt"),
)
