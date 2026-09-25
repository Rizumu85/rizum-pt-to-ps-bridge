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
const painterLink = createPainterLink(process.stdin, (line) => process.stdout.write(line))

// Painter releases the dock action on process exit, not window disappearance.
// Keep GPUiX's native last-window-close shutdown (requires 0.9.0 on Windows).
render(
  <BridgeApp
    session={session}
    onApply={(state, contextId, current) => applyTransfer(current, state, contextId, painterLink)}
    onConnectPhotoshop={(current) => {
      allowPainterForeground()
      return connectPhotoshop(current, painterLink)
    }}
    onReloadPhotoshop={(current) => loadBridgeSession({
      photoshopDocument: current.photoshop!.path,
      painterSnapshot: current.targetSnapshotPath,
      output: current.outputPath,
    })}
  />,
  {
    title: "PT Bridge",
    width: metrics.windowWidth,
    height: initialWindowHeight(session.state),
    minWidth: 560,
    minHeight: 420,
    windowBackground: "opaque",
    focus: process.env.GPUIX_BACKGROUND !== "1",
  },
)
