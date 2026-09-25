import { spawn } from "node:child_process"
import { mkdtemp } from "node:fs/promises"
import { tmpdir } from "node:os"
import path from "node:path"
import { connectStdio } from "@gpuix/react/automation"

import { PAINTER_REQUEST_MARKER } from "../src/transport"

const directory = await mkdtemp(path.join(tmpdir(), "bridge-win-input-"))
const compiled = process.env.BRIDGE_TEST_COMPILED === "1"
const psd = path.resolve("test-fixtures/photoshop_document.psd")
const child = spawn(compiled ? path.resolve("dist/pt-bridge.exe") : process.execPath, [...(compiled ? [] : ["src/main.tsx"]), "--painter",
  process.argv[2] ?? "test-fixtures/painter_snapshot.json", "--output", path.join(directory, "desktop_transfer.json")],
  { stdio: ["pipe", "pipe", "pipe"], env: { ...process.env, GPUIX_BACKGROUND: "1" } })
// Painter's link and GPUiX automation share this stdio pair, exactly as under
// Painter's QProcess; the check proves neither protocol consumes the other.
let requested = false
let applying = false
child.stdout.on("data", data => {
  if (String(data).split("\n").some(line => line.startsWith(PAINTER_REQUEST_MARKER))) requested = true
  if (String(data).split("\n").some(line => line.startsWith(PAINTER_REQUEST_MARKER) && line.includes('"type":"apply"'))) applying = true
})
const app = await connectStdio({
  write: data => { child.stdin.write(data) },
  feed: listener => { child.stdout.on("data", data => listener(data.toString())) },
  close: async () => { child.kill() },
})
try {
  await app.getByTestId("connect-photoshop").waitFor({ timeoutMs: 15000 })
  await Bun.sleep(500)
  const button = await app.getByTestId("connect-photoshop").center()
  const input = Bun.spawn(["python", "tools/windows-pointer.py", String(child.pid),
    process.env.BRIDGE_PHYSICAL_INPUT === "1" ? "physical-click" : "click",
    String(button.x), String(button.y)], { stdout: "inherit", stderr: "inherit" })
  if (await input.exited) throw new Error("Win32 input failed")
  await Bun.sleep(1000)
  if (!requested) {
    await app.screenshot({ path: path.join(directory, "failed-click.png") })
    throw new Error(`Win32 Connect click did not request Painter (${directory})`)
  }
  child.stdin.write(`${JSON.stringify({ type: "photoshop_connected", psd })}\n`)
  await app.getByText("Paint edit").waitFor({ timeoutMs: 5000 })
  if (child.exitCode !== null) throw new Error(`Connect closed the mapper: ${child.exitCode}`)
  // Real Win32 moves over a row are handled inside the native list, unlike
  // the synthetic moves unit tests send, so only this proves the carried
  // card keeps up while the pointer sweeps across a row.
  const source = await app.getByText("Paint edit").center()
  const row = await app.getByTestId("layer-row:substance_painter:sp-lighten").bounds()
  const sweepY = row.y + row.height * 0.7
  const sweep = [`down:${source.x}:${source.y}:30`, `move:${source.x + 10}:${source.y}:30`]
  for (let step = 0; step <= 12; step++) sweep.push(`move:${row.x + 30 + step * 10}:${sweepY}:12`)
  const drag = Bun.spawn(["python", "tools/windows-drag.py", String(child.pid), ...sweep], { stdout: "inherit", stderr: "inherit" })
  if (await drag.exited) throw new Error("Win32 drag failed")
  await Bun.sleep(100)
  const card = await app.getByTestId("drag-preview").bounds()
  const pointerX = row.x + 150
  const lag = Math.min(Math.abs(card.x - (pointerX + 14)), Math.abs(card.x + card.width - (pointerX - 14)))
  if (lag > 20) throw new Error(`The carried card is ${lag.toFixed(0)}px behind the pointer over a row`)
  const release = Bun.spawn(["python", "tools/windows-drag.py", String(child.pid), `up:${source.x}:${source.y}:30`])
  await release.exited
  await Bun.sleep(300)
  await app.mouse.down(app.getByText("Paint edit"))
  await app.mouse.move(app.getByText("Working"), { pressedButton: 0 })
  await app.mouse.up(app.getByText("Working"))
  await app.getByTestId("apply-mapping").click()
  await app.getByTestId("apply-progress").waitFor({ timeoutMs: 5000 })
  const deadline = Date.now() + 5000
  while (!applying && Date.now() < deadline) await Bun.sleep(25)
  if (!applying) throw new Error("Apply did not request Painter")
  child.stdin.write(`${JSON.stringify({ type: "apply_progress", message: "Inserting mapped items into Painter...", completed: 1, total: 4 })}\n`)
  await app.getByText("1 / 4").waitFor({ timeoutMs: 5000 })
  await app.screenshot({ path: path.join(directory, "apply-progress.png") })
  child.stdin.write(`${JSON.stringify({ type: "apply_failed", message: "Host test: no document was changed", snapshot: null })}\n`)
  await app.getByText("Host test: no document was changed").waitFor({ timeoutMs: 5000 })
  if (await app.getByTestId("apply-progress").count()) throw new Error("Apply progress did not dismiss")
  console.log({ connected: true, directory })
} finally {
  await app.close()
}
