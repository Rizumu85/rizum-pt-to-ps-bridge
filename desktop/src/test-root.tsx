import type { ReactNode } from "react"
import { createTestRoot as createNativeRoot } from "@gpuix/react/testing"

export function createTestRoot(size: { width: number; height: number }) {
  const root = createNativeRoot(size)
  return {
    ...root,
    // GPUiX 0.9's Windows test window can report monitor work-area dimensions
    // despite the requested size. Constrain content so hit tests exercise the
    // same viewport as the live mapper, not off-window synthetic coordinates.
    render: (node: ReactNode) => root.render(<div style={size}>{node}</div>),
  }
}
