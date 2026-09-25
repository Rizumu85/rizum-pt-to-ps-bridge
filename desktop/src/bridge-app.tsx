import { useMemo, useRef, useState } from "react"
import {
  AnimatePresence,
  motion,
  useGpuixRequired,
  TooltipProvider,
  type ElementBounds,
  type PublicInstance,
  type EventPayload,
} from "@gpuix/react"
import {
  cloneState,
  findNode,
  defaultPlacement,
  removeFromHost,
  selectionRoots,
  transferSelection,
  selectLayerIds,
  visibleSourceIds,
  type BridgeState,
  type HostId,
  type LayerNode,
  type Placement,
} from "./model"
import { colors, metrics, typography } from "./theme"
import { normalizedBlendMode, type ApplyOutcome, type BridgeSession, type PainterContext } from "./transport"
import {
  ApplyAction,
  ConnectPhotoshopAction,
  ContextOption,
  ContextSelect,
  DragPreview,
  IconAction,
  MappingHelpPopover,
  Motion,
  WorkingSeparator,
  motionEase,
  type PointerFeed,
} from "./components"
import { createTreePointer, HostPanel, RowMotionContext, visibleLayerRows } from "./layer-tree"

export function BridgeApp({
  session: initialSession,
  onApply,
  onConnectPhotoshop,
  onReloadPhotoshop,
}: {
  session: BridgeSession
  onApply: (state: BridgeState, painterContextId: string, session: BridgeSession) => Promise<ApplyOutcome>
  onConnectPhotoshop: (session: BridgeSession) => Promise<BridgeSession | null>
  onReloadPhotoshop?: (session: BridgeSession) => Promise<BridgeSession>
}) {
  const renderer = useGpuixRequired()
  const [session, setSession] = useState(initialSession)
  const rootRef = useRef<PublicInstance | null>(null)
  const [bridge, setBridge] = useState<BridgeState>(() => cloneState(session.state))
  const [activePainterContextId, setActivePainterContextId] = useState(
    session.initialPainterContextId,
  )
  const [history, setHistory] = useState<BridgeState[]>([])
  // Preview parity only earns toolbar space for commands backed by real state changes.
  const [redoStack, setRedoStack] = useState<BridgeState[]>([])
  const [draggingId, setDraggingId] = useState<string | null>(null)
  const press = useRef<{ id: string; x: number; y: number; bounds: ElementBounds | null } | null>(null)
  const [selectedIds, setSelectedIds] = useState<Set<string>>(() => new Set())
  const selectionAnchor = useRef<string | null>(null)
  const [treePointer] = useState(createTreePointer)
  const [expanded, setExpanded] = useState(() => collectExpandedIds(session.state))
  const [status, setStatus] = useState(session.status)
  const [busy, setBusy] = useState(false)
  const [applying, setApplying] = useState(false)
  const [failed, setFailed] = useState(false)
  const pending = useRef(false)
  const [motionIds, setMotionIds] = useState<ReadonlySet<string>>(() => new Set())
  const pointer = useRef<PointerFeed>({ x: 0, y: 0, follow: null, origin: null, returnTo: null })

  const hasChanges = history.length > 0
  const canRedo = redoStack.length > 0
  // Say before Apply what Painter will change, instead of only reporting it after.
  const pendingNotes = useMemo(
    () => photoshopPendingNotes(bridge, session.importBlendModes),
    [bridge, session.importBlendModes],
  )
  const mappedIds = useMemo(
    () => new Set(bridge.mappings.map((mapping) => mapping.sourceId)),
    [bridge.mappings],
  )
  const draggingHost = useMemo(() => {
    if (!draggingId) return null
    const node = findNode(bridge.photoshop, draggingId) ?? findNode(bridge.painter, draggingId)
    return node?.ref.host ?? null
  }, [bridge, draggingId])
  const carried = useMemo(
    () => draggingHost ? selectionRoots(bridge, draggingHost, selectedIds) : [],
    [bridge, draggingHost, selectedIds],
  )
  const activePainterContext = useMemo(
    () => session.painterContexts.find((context) => context.id === activePainterContextId) ?? null,
    [activePainterContextId, session.painterContexts],
  )
  const painterStackOptions = useMemo(
    () => uniqueStackOptions(session.painterContexts),
    [session.painterContexts],
  )
  const activeStackId = activePainterContext ? painterStackId(activePainterContext) : ""
  const channelOptions = useMemo(
    () =>
      session.painterContexts
        .filter((context) => painterStackId(context) === activeStackId)
        .map((context) => ({ value: context.id, label: context.channelLabel })),
    [activeStackId, session.painterContexts],
  )

  const mutate = (next: BridgeState, message: string, moved: ReadonlySet<string> = new Set()) => {
    if (pending.current) return
    if (next === bridge) return
    setMotionIds(moved)
    setHistory((current) => [...current, cloneState(bridge)])
    setRedoStack([])
    setBridge(next)
    setSelectedIds(new Set())
    setStatus(message)
    setFailed(false)
  }

  const removeSource = (host: HostId, id: string) => {
    const next = removeFromHost(bridge, host, id)
    if (next === bridge) {
      setStatus("This target has pending transfers")
      setFailed(true)
      return
    }
    mutate(next, "Layer removed from this mapping session", new Set([id]))
  }

  const endDrag = (landed = false) => {
    pointer.current.returnTo = !landed && draggingId ? press.current?.bounds ?? null : null
    press.current = null
    if (draggingId !== null) setDraggingId(null)
    treePointer.set({ dropTargetId: null, dropPlacement: null })
  }

  const startDrag = (id: string, event: EventPayload) => {
    if (pending.current) return
    // Native row presses do not bubble focus like DOM clicks; keep editing
    // shortcuts with the staging area without stealing focus from open menus.
    if (rootRef.current) renderer.focusElement?.(rootRef.current.id)
    const nodes = findNode(bridge.photoshop, id) ? bridge.photoshop : bridge.painter
    const source = findNode(nodes, id)
    if (!source || source.locked) return
    const modifiers = { toggle: event.modifiers?.ctrl || event.modifiers?.cmd, range: event.modifiers?.shift }
    const visible = visibleSourceIds(nodes, source.ref.host, expanded)
    const next = selectLayerIds(selectedIds, selectionAnchor.current, id, visible, modifiers)
    setSelectedIds(next)
    if (!modifiers.range) selectionAnchor.current = id
    press.current = next.has(id)
      ? { id, x: event.x ?? 0, y: event.y ?? 0, bounds: renderer.getElementBounds?.(event.elementId) ?? null }
      : null
    if (draggingId !== null) setDraggingId(null)
    treePointer.set({ dropTargetId: null, dropPlacement: null })
  }

  const movePointer = (event: EventPayload, rowId?: string, placement?: Placement) => {
    if (event.pressedButton !== 0 || pending.current) {
      if (press.current || draggingId) endDrag()
      return
    }
    const start = press.current
    if (!start) return
    // A press is selection, not a drag. Native child controls can consume mouse-up,
    // so released-button movement also clears the gesture instead of leaving a ghost drop.
    if (Math.hypot((event.x ?? start.x) - start.x, (event.y ?? start.y) - start.y) < metrics.dragThreshold) return
    const source = findNode(bridge.photoshop, start.id) ?? findNode(bridge.painter, start.id)
    if (!source) return
    if (draggingId !== start.id) {
      pointer.current.origin = start.bounds
      setDraggingId(start.id)
    }
    const targetHost: HostId = rowId && findNode(bridge.photoshop, rowId) ? "photoshop" : "substance_painter"
    const targetTree = targetHost === "photoshop" ? bridge.photoshop : bridge.painter
    const target = rowId ? findNode(targetTree, rowId) : null
    const dropTargetId = target && target.ref.host === targetHost && source.ref.host !== targetHost ? target.id : null
    treePointer.set({
      dropTargetId,
      dropPlacement: target && dropTargetId ? placement ?? defaultPlacement(target) : null,
    })
  }

  const drop = (targetId: string) => {
    if (!draggingId) return
    const aimed = treePointer.get()
    const next = transferSelection(
      bridge, selectedIds, targetId, aimed.dropTargetId === targetId ? aimed.dropPlacement ?? undefined : undefined,
    )
    if (next === bridge) {
      setStatus("This target has pending transfers")
      setFailed(true)
    }
    mutate(next, "Mapping updated", selectedIds)
    endDrag(next !== bridge)
  }

  const undo = () => {
    if (pending.current) return
    const previous = history.at(-1)
    if (!previous) return
    // A replaced tree invalidates the pressed row and its original geometry.
    endDrag(true)
    selectionAnchor.current = null
    setRedoStack((current) => [...current, cloneState(bridge)])
    setMotionIds(new Set())
    setBridge(previous)
    setSelectedIds(new Set())
    setHistory((current) => current.slice(0, -1))
    setStatus("Last mapping undone")
    setFailed(false)
  }

  const redo = () => {
    if (pending.current) return
    const next = redoStack.at(-1)
    if (!next) return
    endDrag(true)
    selectionAnchor.current = null
    setHistory((current) => [...current, cloneState(bridge)])
    setMotionIds(new Set())
    setBridge(next)
    setSelectedIds(new Set())
    setRedoStack((current) => current.slice(0, -1))
    setStatus("Last mapping restored")
    setFailed(false)
  }

  const reset = () => {
    if (pending.current) return
    const next = bridgeStateForContext(session, activePainterContext)
    // Reset is an edit to the staging area, not a destructive history boundary.
    if (JSON.stringify(next) === JSON.stringify(bridge)) return
    mutate(next, "Mapping reset")
    endDrag(true)
    selectionAnchor.current = null
    setExpanded(collectExpandedIds(next))
    setStatus("Mapping reset")
    setFailed(false)
  }

  const switchPainterContext = (context: PainterContext | undefined) => {
    if (pending.current) return
    if (!context || context.id === activePainterContextId) return
    if (bridge.mappings.length > 0) {
      setStatus("Apply or reset pending transfers before changing the target.")
      setFailed(true)
      return
    }
    const next = bridgeStateForContext(session, context)
    // Target references belong to one Painter context; carrying mappings across
    // a context switch would silently apply them to a different stack/channel.
    setActivePainterContextId(context.id)
    setMotionIds(new Set())
    setBridge(next)
    setSelectedIds(new Set())
    setHistory([])
    setRedoStack([])
    endDrag(true)
    selectionAnchor.current = null
    setExpanded(collectExpandedIds(next))
    setStatus(`Target changed · ${context.subtitle}`)
    setFailed(false)
  }

  const changePainterStack = (stackId: string) => {
    const contexts = session.painterContexts.filter(
      (context) => painterStackId(context) === stackId,
    )
    const preferred = contexts.find(
      (context) => context.channel === activePainterContext?.channel,
    )
    switchPainterContext(preferred ?? contexts[0])
  }

  const apply = async () => {
    if (pending.current) return
    endDrag(true)
    pending.current = true
    setBusy(true)
    setApplying(true)
    setFailed(false)
    setStatus("Applying in Painter...")
    try {
      const outcome = await onApply(bridge, activePainterContextId, session)
      if (outcome.session) adoptSession(outcome.session, outcome.message)
      else setStatus(outcome.message)
      setFailed(outcome.failed)
    } catch (error) {
      setFailed(true)
      setStatus(error instanceof Error ? error.message : String(error))
    } finally {
      pending.current = false
      setBusy(false)
      setApplying(false)
    }
  }

  // Taking a new session keeps the Painter target the user chose; mappings
  // are always empty here, so nothing staged can land on the wrong document.
  const adoptSession = (next: BridgeSession, message: string) => {
    endDrag(true)
    selectionAnchor.current = null
    const context = next.painterContexts.find((candidate) => candidate.id === activePainterContextId)
      ?? next.painterContexts.find((candidate) => candidate.id === next.initialPainterContextId)
      ?? null
    const state = bridgeStateForContext(next, context)
    setSession(next)
    if (context) setActivePainterContextId(context.id)
    setMotionIds(new Set())
    setBridge(state)
    setSelectedIds(new Set())
    setHistory([])
    setRedoStack([])
    setExpanded(collectExpandedIds(state))
    setStatus(message)
  }

  const replacePhotoshop = async (
    working: string,
    load: () => Promise<BridgeSession | null>,
    cancelled: string,
  ) => {
    if (pending.current) return
    if (bridge.mappings.length > 0) {
      setStatus("Apply or reset pending transfers before changing documents.")
      setFailed(true)
      return
    }
    pending.current = true
    setBusy(true)
    setFailed(false)
    setStatus(working)
    endDrag(true)
    try {
      const next = await load()
      if (next) adoptSession(next, next.status)
      else setStatus(cancelled)
    } catch (error) {
      setFailed(true)
      setStatus(error instanceof Error ? error.message : String(error))
    } finally {
      pending.current = false
      setBusy(false)
    }
  }

  const connectPhotoshop = () => replacePhotoshop(
    "Choose a Photoshop document in Painter...",
    () => onConnectPhotoshop(session),
    "Photoshop connection cancelled",
  )

  // Photoshop edits reach the mapper only through the saved file, so a reload
  // is the way to pick them up without choosing the document again.
  const reloadPhotoshop = () => replacePhotoshop(
    "Reading the saved PSD...",
    async () => onReloadPhotoshop ? onReloadPhotoshop(session) : null,
    "",
  )

  const toggle = (id: string) => {
    const folder = findNode(bridge.photoshop, id) ?? findNode(bridge.painter, id)
    setMotionIds(new Set(visibleLayerRows(folder?.children ?? [], expanded).map(row => row.node.id)))
    setExpanded((current) => {
      const next = new Set(current)
      if (next.has(id)) next.delete(id)
      else next.add(id)
      return next
    })
  }

  // Rows are memoized, so the tree receives handlers that never change and
  // reach the latest state through this ref.
  const latest = useRef({ toggle, startDrag, movePointer, endDrag, drop, removeSource })
  latest.current = { toggle, startDrag, movePointer, endDrag, drop, removeSource }
  const tree = useMemo(() => ({
    pointer: treePointer,
    onToggle: (id: string) => latest.current.toggle(id),
    onDragStart: (id: string, event: EventPayload) => latest.current.startDrag(id, event),
    onPointerMove: (event: EventPayload, rowId?: string, placement?: Placement) =>
      latest.current.movePointer(event, rowId, placement),
    onDragEnd: () => latest.current.endDrag(),
    onHover: (id: string | null) => treePointer.set({ hoveredId: id }),
    onDrop: (id: string) => latest.current.drop(id),
    onTrackPointer: (event: EventPayload) => {
      pointer.current.x = event.x ?? pointer.current.x
      pointer.current.y = event.y ?? pointer.current.y
      pointer.current.follow?.(pointer.current.x, pointer.current.y)
    },
  }), [treePointer])
  const removePhotoshop = useMemo(() => (id: string) => latest.current.removeSource("photoshop", id), [])
  const removePainter = useMemo(() => (id: string) => latest.current.removeSource("substance_painter", id), [])

  return (
    <TooltipProvider delayDuration={320} skipDelayDuration={250} disableHoverableContent>
      <div
        testId="bridge-root"
        ref={rootRef}
        tabIndex={0}
        onKeyDown={(event) => {
          if (pending.current) return
          if (event.key === "escape") { endDrag(); return }
          if (!(event.modifiers?.ctrl || event.modifiers?.cmd)) return
          if (event.key === "z") { if (event.modifiers.shift) redo(); else undo() }
          if (event.key === "y") redo()
        }}
        style={{ width: "100%", height: "100%", backgroundColor: colors.canvas }}
      >
        <RowMotionContext.Provider value={motionIds}>
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ duration: 0.22, ease: motionEase }}
          style={{
            width: "100%",
            height: "100%",
            display: "flex",
            flexDirection: "column",
            backgroundColor: colors.canvas,
            color: colors.text,
            fontFamily: typography.family,
            fontSize: typography.primarySize,
            fontWeight: typography.primaryWeight,
            userSelect: "none",
          }}
        >
        <div
          style={{
            height: metrics.toolbarHeight,
            flexShrink: 0,
            paddingLeft: 16,
            paddingRight: 16,
            display: "flex",
            flexDirection: "row",
            alignItems: "center",
            gap: 8,
          }}
        >
          <ContextSelect
            label="Texture Set:"
            value={activeStackId}
            options={painterStackOptions}
            width={176}
            busy={busy}
            onValueChange={changePainterStack}
          />
          <ContextSelect
            label="Channel:"
            value={activePainterContextId}
            options={channelOptions}
            width={152}
            busy={busy}
            onValueChange={(contextId) =>
              switchPainterContext(
                session.painterContexts.find((context) => context.id === contextId),
              )
            }
          />
          <div style={{ flexGrow: 1 }} />
          <IconAction icon="reset" label="Reset mapping" disabled={busy || !hasChanges} onClick={reset} />
          <div style={{ width: 1, height: 18, flexShrink: 0, backgroundColor: colors.line }} />
          <IconAction icon="undo" label="Undo" disabled={busy || !hasChanges} onClick={undo} />
          <IconAction icon="redo" label="Redo" disabled={busy || !canRedo} onClick={redo} />
          <div style={{ width: 1, height: 18, flexShrink: 0, backgroundColor: colors.line }} />
          <ApplyAction
            count={bridge.mappings.length}
            disabled={busy || !hasChanges || bridge.mappings.length === 0}
            onClick={apply}
          />
        </div>
        <WorkingSeparator active={applying} />
        <div
          onMouseUp={() => endDrag()}
          style={{
            flexGrow: 1,
            minHeight: 0,
            display: "flex",
            flexDirection: "row",
            gap: metrics.panelGap,
            padding: metrics.contentPadding,
          }}
        >
          <HostPanel
            panelId="photoshop"
            title="PHOTOSHOP"
            subtitle={session.photoshopSubtitle}
            nodes={bridge.photoshop}
            host="photoshop"
            headerAction={
              session.photoshop !== null ? (
                <div style={{ display: "flex", flexDirection: "row", gap: 2 }}>
                  {onReloadPhotoshop ? <IconAction
                    icon="refresh"
                    label="Reload the saved PSD"
                    testId="reload-photoshop"
                    disabled={busy}
                    onClick={reloadPhotoshop}
                  /> : null}
                  <IconAction
                    icon="folder"
                    label="Change Photoshop document"
                    testId="change-photoshop"
                    disabled={busy}
                    onClick={connectPhotoshop}
                  />
                </div>
              ) : undefined
            }
            emptyContent={
              session.photoshop !== null ? undefined : (
                <div
                  style={{
                    width: "100%",
                    height: "100%",
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "center",
                  }}
                >
                  <ConnectPhotoshopAction onClick={connectPhotoshop} busy={busy} />
                </div>
              )
            }
            {...tree}
            selectedIds={selectedIds} mappedIds={mappedIds}
            pendingNotes={pendingNotes}
            draggingId={draggingId}
            draggingHost={draggingHost}
            expanded={expanded}
            onRemove={removePhotoshop}
            contentKey={session.photoshop?.path ?? ""}
          />
          {/* Mapping help explains both panes, while the toolbar remains reserved for real commands. */}
          <HostPanel
            panelId="painter"
            title="SUBSTANCE PAINTER"
            subtitle={activePainterContext?.subtitle || "No snapshot loaded"}
            nodes={bridge.painter}
            host="substance_painter"
            headerAction={<MappingHelpPopover />}
            {...tree}
            selectedIds={selectedIds} mappedIds={mappedIds}
            pendingNotes={pendingNotes}
            draggingId={draggingId}
            draggingHost={draggingHost}
            expanded={expanded}
            onRemove={removePainter}
            contentKey={activePainterContextId}
          />
        </div>
        {/* The status line keeps its space while idle so the first click does
            not shrink both panels; it only fades. */}
        <Motion
          testId="bridge-status"
          role="status"
          initial={false}
          animate={{ opacity: status !== session.status || !activePainterContext || selectedIds.size > 0 ? 1 : 0 }}
          transition={{ duration: 0.14, ease: motionEase }}
          style={{ flexShrink: 0, padding: 12, paddingTop: 0 }}
        >
            <text style={{
              color: failed ? colors.danger : colors.secondary,
              fontSize: typography.secondarySize,
              fontFamily: typography.family,
              whiteSpace: "normal",
            }}>{failed || busy ? status : [
              selectedIds.size ? `${selectedIds.size} selected` : "",
              bridge.mappings.length ? `${bridge.mappings.length} pending transfer${bridge.mappings.length === 1 ? "" : "s"}` : "",
            ].filter(Boolean).join(" · ") || status}</text>
        </Motion>
        </motion.div>
        </RowMotionContext.Provider>
        <AnimatePresence>
          {draggingId && carried.length ? <DragPreview key="drag" items={carried} pointer={pointer} /> : null}
        </AnimatePresence>
      </div>
    </TooltipProvider>
  )
}

function photoshopPendingNotes(state: BridgeState, importBlendModes: Set<string> | null): Map<string, string> {
  const notes = new Map<string, string>()
  for (const mapping of state.mappings) {
    if (mapping.direction !== "photoshop_to_painter") continue
    const root = findNode(state.painter, mapping.sourceId)
    if (!root) continue
    const renamed = new Set<string>()
    let skipped = 0
    const visit = (node: LayerNode) => {
      if (node.locked) {
        if (!node.mergedIntoBase) skipped += 1
        return
      }
      const mode = node.ref.blendMode ?? "normal"
      if (importBlendModes && !importBlendModes.has(normalizedBlendMode(mode))) renamed.add(mode)
      node.children?.forEach(visit)
    }
    visit(root)
    const parts = ["Pending"]
    for (const mode of renamed) parts.push(`${mode.replace(/\b\w/g, (letter) => letter.toUpperCase())} becomes Normal`)
    if (skipped) parts.push(`${skipped} layer${skipped === 1 ? "" : "s"} skipped`)
    if (parts.length > 1) notes.set(mapping.sourceId, parts.join(" · "))
  }
  return notes
}

function collectExpandedIds(state: BridgeState): Set<string> {
  const ids = new Set<string>()
  const visit = (nodes: LayerNode[]) => {
    for (const node of nodes) {
      if (node.kind === "group") ids.add(node.id)
      if (node.children) visit(node.children)
    }
  }
  visit(state.photoshop)
  visit(state.painter)
  return ids
}

export function visibleNodesHeight(nodes: LayerNode[], expanded: Set<string>): number {
  return nodes.reduce((height, node) => {
    const ownHeight = metrics.rowHeight
    const childHeight =
      node.kind === "group" && expanded.has(node.id)
        ? visibleNodesHeight(node.children ?? [], expanded)
        : 0
    return height + ownHeight + childHeight
  }, 0)
}

export function initialWindowHeight(state: BridgeState): number {
  const expanded = collectExpandedIds(state)
  const content = Math.max(visibleNodesHeight(state.photoshop, expanded), visibleNodesHeight(state.painter, expanded))
  // Shared proportions fit content at a stable density; long data trees scroll
  // rather than forcing every session into the previous tall, narrow silhouette.
  return Math.max(metrics.minWindowHeight, Math.min(metrics.maxInitialHeight, content + 160))
}

function bridgeStateForContext(
  session: BridgeSession,
  context: PainterContext | null,
): BridgeState {
  return cloneState({
    photoshop: session.state.photoshop,
    painter: context?.nodes ?? [],
    mappings: [],
  })
}

function painterStackId(context: PainterContext): string {
  return context.stack ? `${context.textureSet} / ${context.stack}` : context.textureSet
}

function uniqueStackOptions(contexts: PainterContext[]): ContextOption[] {
  const options = new Map<string, ContextOption>()
  for (const context of contexts) {
    const value = painterStackId(context)
    if (options.has(value)) continue
    options.set(value, {
      value,
      label: context.stack ? `${context.textureSet} / ${context.stack}` : context.textureSet,
    })
  }
  return [...options.values()]
}

