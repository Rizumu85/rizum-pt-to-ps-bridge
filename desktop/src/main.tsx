import { render } from "@gpuix/react"

import { BridgeApp, initialWindowHeight } from "./bridge-app"
import { registerBundledFonts } from "./fonts"
import { allowPainterForeground } from "./foreground"
import { metrics } from "./theme"
import {
  connectPhotoshop,
  createPainterLink,
  failedBridgeSession,
  loadBridgeSession,
  parseSessionOptions,
  writeTransferManifest,
  type BridgeSession,
} from "./transport"

registerBundledFonts()
const painterLink = createPainterLink(process.stdin, (line) => process.stdout.write(line))

let session: BridgeSession
try {
  session = await loadBridgeSession(parseSessionOptions(Bun.argv.slice(2)))
} catch (error) {
  session = failedBridgeSession(error)
}

// Painter releases the dock action on process exit, not window disappearance.
// Keep GPUiX's native last-window-close shutdown (requires 0.9.0 on Windows).
render(
  <BridgeApp
    session={session}
    onApply={(state, contextId, current) => writeTransferManifest(current, state, contextId)}
    onConnectPhotoshop={(current) => {
      allowPainterForeground()
      return connectPhotoshop(current, painterLink)
    }}
    onReloadPhotoshop={(current) => loadBridgeSession({
      photoshopDocument: current.photoshop!.path,
      painterSnapshot: current.targetSnapshotPath,
      output: current.outputPath,
    })}
    onApplied={() => {
      // Painter owns the destination mutation, so a successful atomic write
      // is the desktop process's terminal state and its unambiguous handoff.
      setTimeout(() => process.exit(0), 80)
    }}
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
