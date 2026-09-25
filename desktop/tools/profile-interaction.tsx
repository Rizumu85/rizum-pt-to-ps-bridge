import path from "node:path"
import { createTestRoot } from "../src/test-root"
import { BridgeApp } from "../src/bridge-app"
import { loadBridgeSession } from "../src/transport"
import type { LayerNode } from "../src/model"

const fixtures = path.resolve(import.meta.dirname, "../test-fixtures")
const sizes = process.argv.slice(2).map(Number)
const quantile = (values: number[], fraction: number) => Number([...values].sort((a, b) => a - b)[Math.floor((values.length - 1) * fraction)].toFixed(2))

for (const size of sizes.length ? sizes : [32, 160]) {
  const session = await loadBridgeSession({
    painterSnapshot: path.join(fixtures, "painter_snapshot.json"),
    photoshopDocument: path.join(fixtures, "photoshop_document.psd"),
  })
  const sample = session.state.painter[0]
  const nodes: LayerNode[] = Array.from({ length: size }, (_, i) => ({ ...sample, id: `perf-${i}`, name: `Layer ${i}` }))
  session.state.painter = nodes
  const root = createTestRoot({ width: 700, height: 580 })
  try {
    root.render(<BridgeApp session={session} onApply={async () => ({ session: null, message: "", failed: false })} onConnectPhotoshop={async () => null} />)
    await Bun.sleep(300)
    root.renderer.clockFastForward(1000)
    root.renderer.flush()
    const point = (id: string) => {
      const node = root.renderer.findByTestId(id)!
      const box = root.renderer.getElementBounds(node.id)!
      return { x: box.x + box.width / 2, y: box.y + box.height / 2 }
    }
    const targets = Array.from({ length: 8 }, (_, i) => point(`layer-row:perf-${i}`))
    for (const phase of ["hover", "drag", "scroll"] as const) {
      if (phase === "drag") {
        const source = point("layer-thumbnail:photoshop:ps:100")
        root.renderer.nativeSimulateMouseDown(source.x, source.y)
      }
      const dispatch: number[] = [], paint: number[] = [], total: number[] = []
      for (let i = 0; i < 40; i++) {
        const at = targets[i % targets.length]
        const start = performance.now()
        if (phase === "scroll") root.renderer.dispatchScrollWheel(at.x, at.y, 0, i % 2 ? 20 : -20)
        else root.renderer.dispatchMouseMove(at.x + i % 3, at.y, phase === "drag" ? 0 : undefined)
        const updated = performance.now()
        root.renderer.flush()
        const end = performance.now()
        if (i >= 8) { dispatch.push(updated - start); paint.push(end - updated); total.push(end - start) }
      }
      console.log(JSON.stringify({ rows: size, phase, updateMs: quantile(dispatch, 0.5), paintMs: quantile(paint, 0.5), medianMs: quantile(total, 0.5), p95Ms: quantile(total, 0.95) }))
      root.renderer.simulateKeystrokes("escape")
      root.renderer.dispatchNativeEvents()
      root.renderer.flush()
    }
  } finally { root.unmount() }
}
