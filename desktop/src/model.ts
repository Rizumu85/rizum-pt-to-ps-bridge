export type LayerKind = "group" | "layer"
export type HostId = "photoshop" | "substance_painter"
export type Placement = "inside" | "after"
export type TransferDirection = "photoshop_to_painter" | "painter_to_photoshop"

export type HostLayerRef = {
  host: HostId
  externalId: string
  nativeId?: string | null
  kind: string
  path: string
  assetPath?: string | null
  maskPath?: string | null
  blendMode?: string | null
  opacity?: number | null
  visible?: boolean | null
  hasMask?: boolean
}

export type LayerNode = {
  id: string
  kind: LayerKind
  name: string
  detail: string
  masked?: boolean
  thumbnailPath?: string | null
  ref: HostLayerRef
  children?: LayerNode[]
}

export type TransferMapping = {
  direction: TransferDirection
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

export function transferBetweenHosts(
  state: BridgeState,
  sourceId: string,
  targetId: string,
): BridgeState {
  const sourceHost = sourceId.startsWith("photoshop:")
    ? "photoshop"
    : "substance_painter"
  const targetHost = sourceHost === "photoshop" ? "substance_painter" : "photoshop"
  const sourceNodes = state[hostCollection(sourceHost)]
  const targetNodes = state[hostCollection(targetHost)]
  const source = findNode(sourceNodes, sourceId)
  const target = findNode(targetNodes, targetId)
  if (!source || !target) return state
  if (source.ref.host !== sourceHost || target.ref.host !== targetHost) return state

  const [remainingSource, removed] = removeNode(sourceNodes, sourceId)
  if (!removed) return state
  const nextTarget = insertAtTarget(targetNodes, targetId, removed)
  const direction: TransferDirection =
    sourceHost === "photoshop" ? "photoshop_to_painter" : "painter_to_photoshop"

  return {
    photoshop: sourceHost === "photoshop" ? remainingSource : nextTarget,
    painter: sourceHost === "substance_painter" ? remainingSource : nextTarget,
    mappings: [
      ...state.mappings,
      {
        direction,
        sourceId,
        targetId,
        placement: target.kind === "group" ? "inside" : "after",
        source: removed.ref,
        target: target.ref,
      },
    ],
  }
}

export function removeFromHost(
  state: BridgeState,
  host: HostId,
  sourceId: string,
): BridgeState {
  const collection = hostCollection(host)
  const source = findNode(state[collection], sourceId)
  if (!source || source.ref.host !== host) return state
  const [nodes, removed] = removeNode(state[collection], sourceId)
  return removed ? { ...state, [collection]: nodes } : state
}

function hostCollection(host: HostId): "photoshop" | "painter" {
  return host === "photoshop" ? "photoshop" : "painter"
}
