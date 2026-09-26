import { useMemo, useRef, useState, useSyncExternalStore } from "react"
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
  indexLayerTrees,
  defaultPlacement,
  removeFromHost,
  stagedMapping,
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
import { normalizedBlendMode, renderScalesFor, sameDocument, stagesFor, type ApplyOutcome, type ApplyProgress, type ApplyStage, type BridgeSession, type PainterContext, type RenderScale } from "./transport"
import {
  ApplyAction,
  ConnectPhotoshopAction,
  ContextOption,
  ContextSelect,
  DragPreview,
  IconAction,
  MappingHelpPopover,
  Motion,
  ApplyProgressDialog,
  InsetSeparator,
  motionEase,
  type PointerFeed,
} from "./components"
import { createTreePointer, HostPanel, RowMotionContext, visibleLayerRows, type TreePointerStore } from "./layer-tree"

export function BridgeApp({
  session: initialSession,
  onApply,
  defaultRenderScale = 1,
  onConnectPhotoshop,
  onLoadPhotoshop,
}: {
  session: BridgeSession
  onApply: (state: BridgeState, painterContextId: string, session: BridgeSession, onProgress: (progress: ApplyProgress) => void, renderScale: RenderScale) => Promise<ApplyOutcome>
  /** Settings' default. The window changes it for its own Applies only, since
   *  not every transfer is worth a larger render. */
  defaultRenderScale?: RenderScale
  onConnectPhotoshop: (session: BridgeSession, context: PainterContext | null) => Promise<BridgeSession | null>
  /** Reads a PSD afresh, or none for null: a reload, or a target with its own PSD. */
  onLoadPhotoshop?: (session: BridgeSession, document: string | null) => Promise<BridgeSession>
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
  const press = useRef<{ node: LayerNode; x: number; y: number; bounds: ElementBounds | null; selectedIds: Set<string> } | null>(null)
  const [selectedIds, setSelectedIds] = useState<Set<string>>(() => new Set())
  const selectionAnchor = useRef<string | null>(null)
  const [treePointer] = useState(createTreePointer)
  const [expanded, setExpanded] = useState(() => collectExpandedIds(session.state))
  const [status, setStatus] = useState(session.status)
  const [busy, setBusy] = useState(false)
  const [applying, setApplying] = useState(false)
  const [applyProgress, setApplyProgress] = useState<ApplyProgress>({ message: "Preparing mapped items..." })
  const [applySteps, setApplySteps] = useState<ApplyStage[]>([])
  const [renderScale, setRenderScale] = useState<RenderScale>(defaultRenderScale)
  const scaleOptions = useMemo(() => renderScalesFor(session.photoshop).map(scale => ({
    value: String(scale), label: `${scale}\u00d7`,
  })), [session.photoshop])
  // A PSD too large for a scale offers only what Painter can render.
  const appliedScale = renderScalesFor(session.photoshop).includes(renderScale) ? renderScale : 1
  const [failed, setFailed] = useState(false)
  const pending = useRef(false)
  const [motionIds, setMotionIds] = useState<ReadonlySet<string>>(() => new Set())
  const pointer = useRef<PointerFeed>({ x: 0, y: 0, follow: null, flush: null, returnTo: null })
  const layerIndex = useMemo(() => indexLayerTrees(bridge), [bridge.photoshop, bridge.painter])
  const visibleSelection = useMemo(() => ({
    photoshop: {
      photoshop: visibleSourceIds(bridge.photoshop, "photoshop", expanded),
      substance_painter: visibleSourceIds(bridge.photoshop, "substance_painter", expanded),
    },
    substance_painter: {
      photoshop: visibleSourceIds(bridge.painter, "photoshop", expanded),
      substance_painter: visibleSourceIds(bridge.painter, "substance_painter", expanded),
    },
  }), [bridge.photoshop, bridge.painter, expanded])

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
    pointer.current.flush?.()
    pointer.current.returnTo = !landed && treePointer.get().draggingId ? press.current?.bounds ?? null : null
    press.current = null
    treePointer.set({ draggingId: null, draggingHost: null, dropTargetId: null, dropPlacement: null })
  }

  const startDrag = (id: string, event: EventPayload, readBounds: () => ElementBounds | null) => {
    if (pending.current) return
    // Native row presses do not bubble focus like DOM clicks; keep editing
    // shortcuts with the staging area without stealing focus from open menus.
    if (rootRef.current) renderer.focusElement?.(rootRef.current.id)
    const source = layerIndex.get(id)
    if (!source || source.node.locked) return
    const modifiers = { toggle: event.modifiers?.ctrl || event.modifiers?.cmd, range: event.modifiers?.shift }
    const visible = visibleSelection[source.host][source.node.ref.host]
    const next = selectLayerIds(selectedIds, selectionAnchor.current, id, visible, modifiers)
    setSelectedIds(next)
    if (!modifiers.range) selectionAnchor.current = id
    press.current = next.has(id)
      ? { node: source.node, x: event.x ?? 0, y: event.y ?? 0, bounds: readBounds(), selectedIds: next }
      : null
    treePointer.set({ draggingId: null, draggingHost: null, dropTargetId: null, dropPlacement: null })
  }

  const movePointer = (event: EventPayload, rowId?: string, readBounds?: () => ElementBounds | null) => {
    if (event.pressedButton !== 0 || pending.current) {
      if (press.current || treePointer.get().draggingId) endDrag()
      return
    }
    const start = press.current
    if (!start) return
    // A press is selection, not a drag. Native child controls can consume mouse-up,
    // so released-button movement also clears the gesture instead of leaving a ghost drop.
    const source = start.node
    if (!treePointer.get().draggingId) {
      if (Math.hypot((event.x ?? start.x) - start.x, (event.y ?? start.y) - start.y) < metrics.dragThreshold) return
      pointer.current.x = event.x ?? start.x
      pointer.current.y = event.y ?? start.y
      treePointer.set({ draggingId: source.id, draggingHost: source.ref.host })
    }
    // Pickup belongs to the whole workspace, not a row hit target: a fast
    // first move can already be in the gutter. Only row events choose a drop.
    if (!rowId) return
    const target = layerIndex.get(rowId)
    // A row staged by an earlier drop takes drops above or below it, so the
    // top of a list stays reachable after something was dropped there.
    const staged = target ? stagedMapping(bridge, target.node, target.host) : null
    const dropTargetId = target && source.ref.host !== target.host && target.node.id !== source.id
      && (target.node.ref.host === target.host || staged) ? target.node.id : null
    let placement: Placement | null = null
    if (target && dropTargetId) {
      placement = staged ? "after" : defaultPlacement(target.node)
      const box = readBounds?.()
      if (box && box.height > 0 && event.y !== undefined) {
        const share = (event.y - box.y) / box.height
        placement = staged ? share < 0.5 ? "before" : "after"
          : target.node.kind === "group" ? share < 0.3 ? "before" : "inside" : share < 0.4 ? "before" : "after"
      }
    }
    treePointer.set({
      dropTargetId,
      dropPlacement: placement,
    })
  }

  const drop = (targetId: string) => {
    const aimed = treePointer.get()
    const gesture = press.current
    // Windows can deliver pickup and release before React commits a frame.
    // The gesture owns its selection; rendered feedback is not input state.
    if (!aimed.draggingId || !gesture) return
    const next = transferSelection(
      bridge, gesture.selectedIds, targetId, aimed.dropTargetId === targetId ? aimed.dropPlacement ?? undefined : undefined,
    )
    if (next === bridge) {
      setStatus("This target has pending transfers")
      setFailed(true)
    }
    mutate(next, "Mapping updated", gesture.selectedIds)
    endDrag(next !== bridge)
  }

  // A release beside the rows (the list's margins, below the last row) makes
  // the drop the preview shows. The user saw a line above the first row and
  // got nothing on release; what is shown and what is done must agree.
  const releaseInPanel = (host: HostId) => {
    const aimed = treePointer.get()
    if (aimed.draggingId && aimed.dropTargetId && layerIndex.get(aimed.dropTargetId)?.host === host) {
      drop(aimed.dropTargetId)
    } else {
      endDrag()
    }
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
    // A target with its own PSD brings it along: PSDs belong to a texture set,
    // or to one channel where the artist connected a different one there.
    if (onLoadPhotoshop && !sameDocument(context.photoshopDocument, session.photoshop?.path ?? null)) {
      void replacePhotoshop(
        "Reading this target's Photoshop document...",
        () => onLoadPhotoshop(session, context.photoshopDocument),
        "",
        { contextId: context.id, message: `Target changed · ${context.subtitle}` },
      )
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
    const steps = stagesFor(bridge.mappings)
    setApplySteps(steps)
    setApplyProgress({ stage: steps[0], message: "Preparing mapped items..." })
    setFailed(false)
    setStatus("Applying in Painter...")
    try {
      const outcome = await onApply(bridge, activePainterContextId, session, (next) =>
        setApplyProgress(current => ({ ...next, stage: next.stage ?? current.stage })), appliedScale)
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
  const adoptSession = (next: BridgeSession, message: string, contextId = activePainterContextId) => {
    endDrag(true)
    selectionAnchor.current = null
    const context = next.painterContexts.find((candidate) => candidate.id === contextId)
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
    target?: { contextId: string; message: string },
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
      if (next) adoptSession(next, target?.message ?? next.status, target?.contextId)
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
    () => onConnectPhotoshop(session, activePainterContext),
    "Photoshop connection cancelled",
  )

  // Photoshop edits reach the mapper only through the saved file, so a reload
  // is the way to pick them up without choosing the document again.
  const reloadPhotoshop = () => replacePhotoshop(
    "Reading the saved PSD...",
    async () => onLoadPhotoshop && session.photoshop ? onLoadPhotoshop(session, session.photoshop.path) : null,
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
  const latest = useRef({ toggle, startDrag, movePointer, endDrag, drop, releaseInPanel, removeSource })
  latest.current = { toggle, startDrag, movePointer, endDrag, drop, releaseInPanel, removeSource }
  // Real Win32 moves over a row stay with the row's handler inside the native
  // list and do not reach the panel, so rows feed the carried card too;
  // without it the card froze over every row. The follower drops repeated
  // coordinates when both report the same move.
  const carry = (event: EventPayload) => {
    pointer.current.x = event.x ?? pointer.current.x
    pointer.current.y = event.y ?? pointer.current.y
    pointer.current.follow?.(pointer.current.x, pointer.current.y)
  }
  const tree = useMemo(() => ({
    pointer: treePointer,
    onToggle: (id: string) => latest.current.toggle(id),
    onDragStart: (id: string, event: EventPayload, readBounds: () => ElementBounds | null) => latest.current.startDrag(id, event, readBounds),
    onPointerMove: (event: EventPayload, rowId?: string, readBounds?: () => ElementBounds | null) => {
      latest.current.movePointer(event, rowId, readBounds)
      carry(event)
    },
    onDragEnd: () => latest.current.endDrag(),
    onHover: (id: string | null) => treePointer.set({ hoveredId: id }),
    onDrop: (id: string) => latest.current.drop(id),
    onRelease: (host: HostId) => latest.current.releaseInPanel(host),
    onTrackPointer: (event: EventPayload) => {
      if (!treePointer.get().draggingId || event.pressedButton !== 0) latest.current.movePointer(event)
      carry(event)
    },
  }), [treePointer])
  // Between the panels no drop can land, so the preview line goes too.
  const trackGutter = useMemo(() => (event: EventPayload) => {
    if (treePointer.get().dropTargetId) treePointer.set({ dropTargetId: null, dropPlacement: null })
    tree.onTrackPointer(event)
  }, [tree, treePointer])
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
        style={{ position: "relative", width: "100%", height: "100%", backgroundColor: colors.canvas }}
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
            minWidth={104}
            busy={busy}
            onValueChange={changePainterStack}
          />
          <ContextSelect
            label="Channel:"
            value={activePainterContextId}
            options={channelOptions}
            width={152}
            minWidth={96}
            busy={busy}
            onValueChange={(contextId) =>
              switchPainterContext(
                session.painterContexts.find((context) => context.id === contextId),
              )
            }
          />
          <div style={{ width: 1, height: 18, flexShrink: 0, backgroundColor: colors.line }} />
          <ContextSelect
            label="Render:"
            value={String(appliedScale)}
            options={scaleOptions}
            width={96}
            busy={busy}
            onValueChange={(value) => setRenderScale(Number(value) as RenderScale)}
          />
          <div style={{ flexGrow: 1 }} />
          <IconAction icon="eraser" label="Reset mapping" testId="action:reset" disabled={busy || !hasChanges} onClick={reset} />
          <div style={{ width: 1, height: 18, flexShrink: 0, backgroundColor: colors.line }} />
          <IconAction icon="undo" label="Undo" disabled={busy || !hasChanges} onClick={undo} />
          <IconAction icon="redo" label="Redo" disabled={busy || !canRedo} onClick={redo} />
          <div style={{ width: 1, height: 18, flexShrink: 0, backgroundColor: colors.line }} />
          <ApplyAction
            disabled={busy || !hasChanges || bridge.mappings.length === 0}
            onClick={apply}
          />
        </div>
        <InsetSeparator />
        <div
          onMouseMove={trackGutter}
          onMouseUp={() => endDrag()}
          style={{
            flexGrow: 1,
            minHeight: 0,
            display: "flex",
            flexDirection: "row",
            gap: metrics.panelGap,
            padding: metrics.contentPadding,
            // MiSans sits low in its line box, so equal padding left the status
            // text visibly nearer the window edge than the panels; these two
            // values balance the glyphs, not the boxes.
            paddingBottom: 12,
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
                  {onLoadPhotoshop ? <IconAction
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
          // On the panels' edges, the workspace's one horizontal grid.
          style={{ flexShrink: 0, paddingLeft: metrics.contentPadding, paddingRight: metrics.contentPadding, paddingBottom: 13 }}
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
        <DragOverlay bridge={bridge} gesture={press} pointer={pointer} store={treePointer} />
        {applying ? <ApplyProgressDialog progress={applyProgress} steps={applySteps} /> : null}
      </div>
    </TooltipProvider>
  )
}

function DragOverlay({ bridge, gesture, pointer, store }: {
  bridge: BridgeState
  gesture: { current: { node: LayerNode; selectedIds: Set<string> } | null }
  pointer: { current: PointerFeed }
  store: TreePointerStore
}) {
  // Pickup changes only the overlay and panel cursors, not the toolbar and
  // both complete trees. The common single-row drag needs no tree traversal.
  const id = useSyncExternalStore(store.subscribe, () => store.get().draggingId)
  const source = gesture.current?.node
  const selectedIds = gesture.current?.selectedIds
  const carried = useMemo(() => {
    return !id || !source || !selectedIds ? [] : selectedIds.size === 1 ? [source] : selectionRoots(bridge, source.ref.host, selectedIds)
  }, [id, source, bridge, selectedIds])
  return <AnimatePresence>{id && carried.length ? <DragPreview key="drag" items={carried} pointer={pointer} /> : null}</AnimatePresence>
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

// Folders open as Painter and Photoshop show them, so a long stack the
// artist keeps folded does not arrive fully expanded.
function collectExpandedIds(state: BridgeState): Set<string> {
  const ids = new Set<string>()
  const visit = (nodes: LayerNode[]) => {
    for (const node of nodes) {
      if (node.kind === "group" && node.open !== false) ids.add(node.id)
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
  // Short trees still open taller than the resize floor: a first open often
  // has no PSD yet, and a window sized to a few rows looked cramped.
  return Math.max(metrics.minInitialHeight, Math.min(metrics.maxInitialHeight, content + 160))
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

