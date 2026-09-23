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
child.stdout.on("data", data => {
  if (String(data).split("\n").some(line => line.startsWith(PAINTER_REQUEST_MARKER))) requested = true
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
  console.log({ connected: true, directory })
} finally {
  await app.close()
}
