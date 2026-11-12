import type { ReactNode } from "react"
import { createRoot, flushSync } from "@gpuix/react"
import { TestRenderer } from "@gpuix/react/testing"
import { createRendererState } from "@gpuix/native/host"

export function createTestRoot(size: { width: number; height: number }, synchronousInput = true) {
  const renderer = new TestRenderer({
    ...size,
    dispatchEvent: event => {
      const dispatch = () => { createRendererState(renderer).dispatch(event) }
      // The default native test root forces a React commit per event. Opt out
      // to reproduce production bursts that arrive before the next UI frame.
      if (synchronousInput) flushSync(dispatch)
      else dispatch()
    },
  })
  const root = createRoot(renderer)
  return {
    root,
    renderer,
    unmount: root.unmount,
    // GPUiX's Windows test window reported monitor work-area dimensions
    // despite the requested size (seen on 0.9, not rechecked on the pinned
    // 0.10). Constrain content so hit tests exercise the
    // same viewport as the live mapper, not off-window synthetic coordinates.
    render: (node: ReactNode) => {
      flushSync(() => root.render(<div style={size}>{node}</div>))
      renderer.flush()
    },
  }
}
