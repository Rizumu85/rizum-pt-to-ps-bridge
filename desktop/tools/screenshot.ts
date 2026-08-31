import { mkdirSync } from "node:fs"
import path from "node:path"

import { launch } from "@gpuix/react/automation"

const output = process.argv[2] ?? "screenshots/pt-bridge.png"
mkdirSync(path.dirname(output), { recursive: true })
const fixtureDir = path.resolve(import.meta.dirname, "../test-fixtures")

const app = await launch({
  command: process.execPath,
  args: [
    "src/main.tsx",
    "--photoshop",
    path.join(fixtureDir, "photoshop_selection.json"),
    "--painter",
    path.join(fixtureDir, "painter_snapshot.json"),
    "--output",
    path.resolve("screenshots/desktop_transfer.json"),
  ],
  env: { GPUIX_BACKGROUND: "1" },
})

await app.getByTestId("bridge-root").waitFor({ timeoutMs: 60_000 })
await Bun.sleep(300)
await app.clock.pause()
await app.screenshot({ path: output })
await app.close()

console.log(`[screenshot] wrote ${output}`)
