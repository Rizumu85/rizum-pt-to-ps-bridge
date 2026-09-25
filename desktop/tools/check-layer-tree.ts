import { launch } from "@gpuix/react/automation"
import path from "node:path"
import assert from "node:assert/strict"

const app = await launch({
  command: process.execPath,
  args: ["src/main.tsx", "--psd", "test-fixtures/photoshop_document.psd", "--painter", "test-fixtures/painter_snapshot.json", "--output", "screenshots/tree-check-transfer.json"],
  env: { GPUIX_BACKGROUND: "1" },
})
try {
  await app.getByTestId("bridge-root").waitFor({ timeoutMs: 60000 })
  await Bun.sleep(400)
  assert.equal(await app.getByText("Painter Stack").count(), 0)
  assert.equal(await app.getByText("Selected Layers").count(), 0)
  await app.getByText("Paint edit").click()
  await app.getByText("Working").hover()
  assert.equal(await app.getByTestId("drop-indicator:substance_painter:sp-working").count(), 0)
  await app.screenshot({ path: path.resolve("screenshots/tree-click.png") })
  await app.mouse.down(app.getByText("Paint edit"))
  await Bun.sleep(100)
  await app.mouse.move(app.getByText("Working"), { pressedButton: 0 })
  await Bun.sleep(150)
  await app.screenshot({ path: path.resolve("screenshots/tree-drag.png") })
  assert.equal(await app.getByTestId("drop-indicator:substance_painter:sp-working").count(), 1)
  await app.mouse.up(app.getByText("Working"))
  await Bun.sleep(100)
  await app.screenshot({ path: path.resolve("screenshots/tree-drop.png") })
  assert.equal(await app.getByText("Pending").count(), 1)
  assert.equal(await app.getByTestId("drop-indicator:substance_painter:sp-working").count(), 0)
  await app.getByTestId("layer-toggle:substance_painter:sp-working").click()
  await Bun.sleep(250)
  await app.getByText("Retouch group").hover()
  assert.equal(await app.getByTestId("drop-indicator:photoshop:ps:103").count(), 0)
  console.log("Native layer-tree click, drag, release, and collapse checks passed.")
} finally { await app.close() }
