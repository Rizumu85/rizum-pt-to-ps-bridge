export type LayerKind = "group" | "layer"
export type HostId = "photoshop" | "substance_painter"
export type Placement = "inside" | "before" | "after"

/** A group takes drops inside it and a layer below it, unless the pointer aims elsewhere. */
export function defaultPlacement(target: LayerNode): Placement {
  return target.kind === "group" ? "inside" : "after"
}
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
  /** Sibling indices from the document root, top first, as Photoshop's DOM counts them. */
  indexPath?: number[]
}

export type LayerNode = {
  id: string
  kind: LayerKind
  name: string
  detail: string
  masked?: boolean
  thumbnailPath?: string | null
  /** Why this node cannot be transferred; locked rows stay visible but inert. */
  locked?: string
  /** What changes on transfer (merged clipping, dropped styles); shown under the name. */
  note?: string
  /** A clipped Photoshop layer that travels inside its base, not on its own. */
  mergedIntoBase?: boolean
  ref: HostLayerRef
  children?: LayerNode[]
  /** A folder is shown open where its host shows it open; unknown is open. */
  open?: boolean
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

export function indexLayerTrees(state: BridgeState): Map<string, { node: LayerNode; host: HostId }> {
  const index = new Map<string, { node: LayerNode; host: HostId }>()
  const visit = (nodes: LayerNode[], host: HostId) => {
    for (const node of nodes) {
      // Staged rows keep their source host, but hit testing needs the panel
      // they currently occupy so they can be repositioned after a transfer.
      index.set(node.id, { node, host })
      if (node.children) visit(node.children, host)
    }
  }
  visit(state.photoshop, "photoshop")
  visit(state.painter, "substance_painter")
  return index
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
  placement: Placement,
): LayerNode[] {
  const next: LayerNode[] = []

  for (const node of nodes) {
    if (node.id === targetId) {
      if (placement === "inside") next.push({ ...node, children: [...(node.children ?? []), nodeToInsert] })
      else if (placement === "before") next.push(nodeToInsert, node)
      else next.push(node, nodeToInsert)
      continue
    }

    next.push(
      node.children
        ? { ...node, children: insertAtTarget(node.children, targetId, nodeToInsert, placement) }
        : node,
    )
  }

  return next
}

export function transferBetweenHosts(
  state: BridgeState,
  sourceId: string,
  targetId: string,
  placement?: Placement,
): BridgeState {
  const source = findNode(state.photoshop, sourceId) ?? findNode(state.painter, sourceId)
  if (!source || source.locked) return state
  const sourceHost = source.ref.host
  const targetHost = sourceHost === "photoshop" ? "substance_painter" : "photoshop"
  const sourceNodes = state[hostCollection(sourceHost)]
  const targetNodes = state[hostCollection(targetHost)]
  const target = findNode(targetNodes, targetId)
  if (!target || targetId === sourceId) return state
  const staged = stagedMapping(state, target, targetHost)
  if (target.ref.host !== targetHost && !staged) return state
  const place = placement ?? (staged ? "after" : defaultPlacement(target))
  // A staged folder does not exist in its target host yet, so nothing can go inside it.
  if (place === "inside" && (staged || target.kind !== "group")) return state
  const remapping = state.mappings.some(mapping => mapping.sourceId === sourceId)
  // A host target cannot also be moved out of the staging tree: its dependent
  // transfers would no longer have the destination shown in the preview.
  if (!remapping && state.mappings.some(mapping => findNode([source], mapping.targetId))) return state

  const [remaining, removed] = removeNode(remapping ? targetNodes : sourceNodes, sourceId)
  if (!removed) return state
  // Groups cross in both directions as folders of their layers, which is the
  // hierarchy Apply creates and so the one the preview promises.
  const nextTarget = insertAtTarget(remapping ? remaining : targetNodes, targetId, removed, place)
  const remainingSource = remapping ? sourceNodes : remaining
  const direction: TransferDirection =
    sourceHost === "photoshop" ? "photoshop_to_painter" : "painter_to_photoshop"

  const others = state.mappings.filter(mapping => mapping.sourceId !== sourceId)
  const record: TransferMapping = staged
    // A staged row does not exist in its target host until Apply, so a drop
    // beside it takes the same host anchor and is ordered against it. Rows on
    // one anchor are inserted in mapping order: "before" and "inside" stack in
    // that order, "after" in reverse, in both Painter and Photoshop.
    ? { direction, sourceId, targetId: staged.targetId, placement: staged.placement, source: removed.ref, target: staged.target }
    : { direction, sourceId, targetId, placement: place, source: removed.ref, target: target.ref }
  let index = others.length
  if (staged) {
    const at = others.indexOf(staged)
    index = (place === "before") === (staged.placement !== "after") ? at : at + 1
  }

  return {
    photoshop: sourceHost === "photoshop" ? remainingSource : nextTarget,
    painter: sourceHost === "substance_painter" ? remainingSource : nextTarget,
    mappings: [...others.slice(0, index), record, ...others.slice(index)],
  }
}

/** The mapping that staged this row in the target host, when the row is a staged root. */
export function stagedMapping(state: BridgeState, node: LayerNode, host: HostId): TransferMapping | null {
  if (node.ref.host === host) return null
  return state.mappings.find(mapping => mapping.sourceId === node.id) ?? null
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

/** The selected rows a drop carries: topmost selected nodes of the source host, top to bottom. */
export function selectionRoots(state: BridgeState, sourceHost: HostId, sourceIds: ReadonlySet<string>): LayerNode[] {
  const roots: LayerNode[] = []
  const visit = (nodes: LayerNode[]) => {
    for (const node of nodes) {
      if (node.ref.host === sourceHost && sourceIds.has(node.id)) roots.push(node)
      else if (node.children) visit(node.children)
    }
  }
  const targetHost = sourceHost === "photoshop" ? "substance_painter" : "photoshop"
  visit(state[hostCollection(sourceHost)])
  visit(state[hostCollection(targetHost)])
  return roots
}

export function transferSelection(
  state: BridgeState,
  sourceIds: Set<string>,
  targetId: string,
  placement?: Placement,
): BridgeState {
  // The panel holding the target decides the direction, not the target's own
  // host: a row staged by an earlier drop sits in the other host's panel.
  const inPainter = findNode(state.painter, targetId)
  const target = inPainter ?? findNode(state.photoshop, targetId)
  if (!target) return state
  const targetHost: HostId = inPainter ? "substance_painter" : "photoshop"
  const place = placement ?? (stagedMapping(state, target, targetHost) ? "after" : defaultPlacement(target))
  const sourceHost = targetHost === "photoshop" ? "substance_painter" : "photoshop"
  const roots = selectionRoots(state, sourceHost, sourceIds).map(node => node.id)
  // After-drops insert against the same anchor; replay bottom-up to preserve
  // the user's top-to-bottom selection order as one undoable batch.
  if (place === "after") roots.reverse()
  return roots.reduce((next, id) => transferBetweenHosts(next, id, targetId, place), state)
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
  if (!modifiers.range && !modifiers.toggle) {
    if (!current.has(id)) return new Set([id])
    if (current.size === 1) return current
  }
  const visibleSet = new Set(visible)
  const sameHost = new Set([...current].filter(value => visibleSet.has(value)))
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
  if (!sameHost.has(id)) return new Set([id])
  return sameHost.size === current.size ? current : sameHost
}

function hostCollection(host: HostId): "photoshop" | "painter" {
  return host === "photoshop" ? "photoshop" : "painter"
}
