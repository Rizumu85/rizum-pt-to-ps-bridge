export type LayerKind = "group" | "layer"

export type LayerNode = {
  id: string
  kind: LayerKind
  name: string
  detail: string
  masked?: boolean
  children?: LayerNode[]
}

export type BridgeState = {
  photoshop: LayerNode[]
  painter: LayerNode[]
}

export const initialBridgeState: BridgeState = {
  photoshop: [
    {
      id: "ps-group",
      kind: "group",
      name: "Group",
      detail: "2 Layers",
      masked: true,
      children: [
        { id: "ps-paint", kind: "layer", name: "Paint edit", detail: "Normal · 100%" },
        {
          id: "ps-color",
          kind: "layer",
          name: "Color pass",
          detail: "Overlay · 65%",
          masked: true,
        },
      ],
    },
    { id: "ps-detail", kind: "layer", name: "Loose detail", detail: "Soft Light · 40%" },
    {
      id: "ps-cleanup",
      kind: "layer",
      name: "Mask cleanup",
      detail: "Normal · 100%",
      masked: true,
    },
  ],
  painter: [
    { id: "sp-locator", kind: "layer", name: "Locator", detail: "Normal · 100%", masked: true },
    { id: "sp-maskout", kind: "layer", name: "MaskOut", detail: "Multiply · 100%" },
    {
      id: "sp-working",
      kind: "group",
      name: "Working",
      detail: "6 Layers",
      children: [
        { id: "sp-lighten", kind: "layer", name: "Lighten", detail: "Overlay · 55%", masked: true },
        { id: "sp-recolor", kind: "layer", name: "Recolor", detail: "Color · 100%" },
        {
          id: "sp-strokes",
          kind: "layer",
          name: "Paint strokes",
          detail: "Normal · 100%",
          masked: true,
        },
      ],
    },
    { id: "sp-base", kind: "layer", name: "LC_BaseTextures", detail: "Normal · 100%" },
  ],
}

export function cloneState(state: BridgeState): BridgeState {
  return structuredClone(state)
}

export function removeNode(nodes: LayerNode[], id: string): [LayerNode[], LayerNode | null] {
  let removed: LayerNode | null = null
  const next: LayerNode[] = []

  for (const node of nodes) {
    if (node.id === id) {
      removed = node
      continue
    }

    if (!removed && node.children) {
      const [children, child] = removeNode(node.children, id)
      if (child) {
        removed = child
        next.push({ ...node, children })
        continue
      }
    }

    next.push(node)
  }

  return [next, removed]
}

export function insertAtTarget(
  nodes: LayerNode[],
  targetId: string,
  nodeToInsert: LayerNode,
): LayerNode[] {
  const next: LayerNode[] = []

  for (const node of nodes) {
    if (node.id === targetId) {
      if (node.kind === "group") {
        next.push({ ...node, children: [...(node.children ?? []), nodeToInsert] })
      } else {
        next.push(node, nodeToInsert)
      }
      continue
    }

    next.push(
      node.children
        ? { ...node, children: insertAtTarget(node.children, targetId, nodeToInsert) }
        : node,
    )
  }

  return next
}

export function transferToPainter(
  state: BridgeState,
  sourceId: string,
  targetId: string,
): BridgeState {
  const [photoshop, source] = removeNode(state.photoshop, sourceId)
  if (!source) return state

  return {
    photoshop,
    painter: insertAtTarget(state.painter, targetId, source),
  }
}

export function removeFromPhotoshop(state: BridgeState, sourceId: string): BridgeState {
  const [photoshop, removed] = removeNode(state.photoshop, sourceId)
  return removed ? { ...state, photoshop } : state
}
