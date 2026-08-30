export type LayerKind = "group" | "layer"
export type HostId = "photoshop" | "substance_painter"
export type Placement = "inside" | "after"

export type HostLayerRef = {
  host: HostId
  externalId: string
  kind: string
  path: string
  assetPath?: string | null
  maskPath?: string | null
}

export type LayerNode = {
  id: string
  kind: LayerKind
  name: string
  detail: string
  masked?: boolean
  ref: HostLayerRef
  children?: LayerNode[]
}

export type TransferMapping = {
  sourceId: string
  targetId: string
  placement: Placement
  source: HostLayerRef
  target: HostLayerRef
}

export type BridgeState = {
  photoshop: LayerNode[]
  painter: LayerNode[]
  mappings: TransferMapping[]
}

export const emptyBridgeState: BridgeState = {
  photoshop: [],
  painter: [],
  mappings: [],
}

export function cloneState(state: BridgeState): BridgeState {
  return structuredClone(state)
}

export function findNode(nodes: LayerNode[], id: string): LayerNode | null {
  for (const node of nodes) {
    if (node.id === id) return node
    const child = node.children ? findNode(node.children, id) : null
    if (child) return child
  }
  return null
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
  const target = findNode(state.painter, targetId)
  if (!target) return state

  const [photoshop, source] = removeNode(state.photoshop, sourceId)
  if (!source) return state

  return {
    photoshop,
    painter: insertAtTarget(state.painter, targetId, source),
    mappings: [
      ...state.mappings,
      {
        sourceId,
        targetId,
        placement: target.kind === "group" ? "inside" : "after",
        source: source.ref,
        target: target.ref,
      },
    ],
  }
}

export function removeFromPhotoshop(state: BridgeState, sourceId: string): BridgeState {
  const [photoshop, removed] = removeNode(state.photoshop, sourceId)
  return removed ? { ...state, photoshop } : state
}
