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
  opacity?: number | null // Percent in both directions; never a Painter API fraction.
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
  const source = findNode(state.photoshop, sourceId) ?? findNode(state.painter, sourceId)
  if (!source) return state
  const sourceHost = source.ref.host
  const targetHost = sourceHost === "photoshop" ? "substance_painter" : "photoshop"
  const sourceNodes = state[hostCollection(sourceHost)]
  const targetNodes = state[hostCollection(targetHost)]
  const target = findNode(targetNodes, targetId)
  if (!target || target.ref.host !== targetHost) return state
  const remapping = state.mappings.some(mapping => mapping.sourceId === sourceId)
  // A host target cannot also be moved out of the staging tree: its dependent
  // transfers would no longer have the destination shown in the preview.
  if (!remapping && state.mappings.some(mapping => findNode([source], mapping.targetId))) return state

  const [remaining, removed] = removeNode(remapping ? targetNodes : sourceNodes, sourceId)
  if (!removed) return state
  // Host transfer renders a group as one visual bitmap. Showing its editable
  // descendants here would promise a hierarchy the Apply operation never creates.
  const preview = removed.kind === "group"
    ? { ...removed, kind: "layer" as const, children: undefined }
    : removed
  const nextTarget = insertAtTarget(remapping ? remaining : targetNodes, targetId, preview)
  const remainingSource = remapping ? sourceNodes : remaining
  const direction: TransferDirection =
    sourceHost === "photoshop" ? "photoshop_to_painter" : "painter_to_photoshop"

  return {
    photoshop: sourceHost === "photoshop" ? remainingSource : nextTarget,
    painter: sourceHost === "substance_painter" ? remainingSource : nextTarget,
    mappings: [
      ...state.mappings.filter(mapping => mapping.sourceId !== sourceId),
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
  if (state.mappings.some(mapping => findNode([source], mapping.targetId))) return state
  const [nodes, removed] = removeNode(state[collection], sourceId)
  return removed ? { ...state, [collection]: nodes } : state
}

export function transferSelection(state: BridgeState, sourceIds: Set<string>, targetId: string): BridgeState {
  const target = findNode(state.photoshop, targetId) ?? findNode(state.painter, targetId)
  if (!target) return state
  const sourceHost = target.ref.host === "photoshop" ? "substance_painter" : "photoshop"
  const roots: string[] = []
  const visit = (nodes: LayerNode[]) => {
    for (const node of nodes) {
      if (node.ref.host === sourceHost && sourceIds.has(node.id)) roots.push(node.id)
      else if (node.children) visit(node.children)
    }
  }
  visit(state[hostCollection(sourceHost)])
  visit(state[hostCollection(target.ref.host)])
  // After-drops insert against the same anchor; replay bottom-up to preserve
  // the user's top-to-bottom selection order as one undoable batch.
  if (target.kind === "layer") roots.reverse()
  return roots.reduce((next, id) => transferBetweenHosts(next, id, targetId), state)
}

export function visibleSourceIds(nodes: LayerNode[], host: HostId, expanded: Set<string>): string[] {
  const ids: string[] = []
  for (const node of nodes) {
    if (node.ref.host === host) ids.push(node.id)
    if (node.children && expanded.has(node.id)) ids.push(...visibleSourceIds(node.children, host, expanded))
  }
  return ids
}

export function selectLayerIds(
  current: Set<string>, anchor: string | null, id: string, visible: string[],
  modifiers: { toggle?: boolean; range?: boolean },
): Set<string> {
  const sameHost = new Set([...current].filter(value => visible.includes(value)))
  if (modifiers.range && anchor && visible.includes(anchor)) {
    const start = visible.indexOf(anchor)
    const end = visible.indexOf(id)
    return new Set([...(modifiers.toggle ? sameHost : []), ...visible.slice(Math.min(start, end), Math.max(start, end) + 1)])
  }
  if (modifiers.toggle) {
    if (sameHost.has(id)) sameHost.delete(id)
    else sameHost.add(id)
    return sameHost
  }
  return sameHost.has(id) ? sameHost : new Set([id])
}

function hostCollection(host: HostId): "photoshop" | "painter" {
  return host === "photoshop" ? "photoshop" : "painter"
}
