import { render } from "@gpuix/react"

import { BridgeApp, initialWindowHeight } from "./bridge-app"
import { registerBundledFonts } from "./fonts"
import { allowPainterForeground } from "./foreground"
import { metrics } from "./theme"
import {
  applyTransfer,
  connectPhotoshop,
  createPainterLink,
  failedBridgeSession,
  loadBridgeSession,
  parseSessionOptions,
  type BridgeSession,
} from "./transport"

registerBundledFonts()

let session: BridgeSession
try {
  session = await loadBridgeSession(parseSessionOptions(Bun.argv.slice(2)))
} catch (error) {
  session = failedBridgeSession(error)
}

// Keep stdin buffered during asynchronous file loading. Starting its flow
// earlier loses the automation handshake before GPUiX subscribes in render().
// The mapper can do nothing once Painter's end of the pipe is gone, and an
// orphan kept its window and files open after Painter quit or crashed.
const painterLink = createPainterLink(process.stdin, (line) => process.stdout.write(line), () => process.exit(0))

// Painter releases the dock action on process exit, not window disappearance.
// Keep GPUiX's native last-window-close shutdown (requires 0.9.0 on Windows).
render(
  <BridgeApp
    session={session}
    onApply={(state, contextId, current, onProgress) => applyTransfer(current, state, contextId, painterLink, onProgress)}
    onConnectPhotoshop={(current, context) => {
      allowPainterForeground()
      return connectPhotoshop(current, painterLink, context)
    }}
    onLoadPhotoshop={(current, document) => loadBridgeSession({
      photoshopDocument: document,
      painterSnapshot: current.targetSnapshotPath,
      documents: current.documentsPath,
      output: current.outputPath,
    })}
  />,
  {
    title: "PT Bridge",
    width: metrics.windowWidth,
    height: initialWindowHeight(session.state),
    minWidth: 560,
    minHeight: metrics.minWindowHeight,
    windowBackground: "opaque",
    focus: process.env.GPUIX_BACKGROUND !== "1",
  },
)
