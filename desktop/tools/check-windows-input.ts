import { spawn } from "node:child_process"
import { mkdtemp } from "node:fs/promises"
import { tmpdir } from "node:os"
import path from "node:path"
import { connectStdio } from "@gpuix/react/automation"

const directory = await mkdtemp(path.join(tmpdir(), "bridge-win-input-"))
const output = path.join(directory, "request.json")
const compiled = process.env.BRIDGE_TEST_COMPILED === "1"
const child = spawn(compiled ? path.resolve("dist/pt-bridge.exe") : process.execPath, [...(compiled ? [] : ["src/main.tsx"]), "--painter",
  process.argv[2] ?? "test-fixtures/painter_snapshot.json", "--output", output],
  { stdio: ["pipe", "pipe", "pipe"], env: { ...process.env, GPUIX_BACKGROUND: "1" } })
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
  const connected = await Bun.file(output).exists()
  if (!connected) await app.screenshot({ path: path.join(directory, "failed-click.png") })
  console.log({ connected, directory })
  if (!connected) throw new Error("Win32 Connect click did not write a request")
  const request = await Bun.file(output).json()
  if (request.request_type !== "desktop_connect_photoshop") throw new Error("Unexpected handoff request")
  // Writing alone is insufficient: Painter opens its picker only after a clean exit.
  if (child.exitCode !== 0) throw new Error(`Connect did not exit cleanly: ${child.exitCode}`)
} finally {
  await app.close()
}
