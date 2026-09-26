import { createContext, memo, useCallback, useContext, useMemo, useRef, useState, useSyncExternalStore } from "react"
import { LayerScroll, RowBoundsContext } from "./layer-scroll"
import {
  motion,
  type ElementBounds,
  type EventPayload,
  type PublicInstance,
} from "@gpuix/react"
import { findNode, type HostId, type LayerNode, type Placement } from "./model"
import { colors, metrics, typography } from "./theme"
import {
  DisclosureIcon,
  Icon,
  InsetSeparator,
  PrimaryText,
  SecondaryText,
  maskThumbnailSource,
  Motion,
  motionEase,
} from "./components"

// Native list items must be individual rows: a nested folder otherwise paints
// all descendants as one item, defeating viewport culling for large stacks.
export function visibleLayerRows(nodes: LayerNode[], expanded: ReadonlySet<string>, depth = 0): { node: LayerNode; depth: number }[] {
  return nodes.flatMap(node => [{ node, depth }, ...(node.kind === "group" && expanded.has(node.id)
    ? visibleLayerRows(node.children ?? [], expanded, depth + 1) : [])])
}

function LayerThumbnail({ node }: { node: LayerNode }) {
  const isGroup = node.kind === "group"
  // The corner tile is semantic mask state and only appears for nodes backed by a real mask.
  return (
    <div testId={`layer-thumbnail:${node.id}`} style={{ width: 25, height: 22, flexShrink: 0, position: "relative" }}>
      {isGroup ? (
        <div
          style={{
            width: 20,
            height: 20,
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
          }}
        >
          <Icon name="folder" size={16} />
        </div>
      ) : (
        <div
          style={{
            width: 20,
            height: 20,
            overflow: "hidden",
            borderRadius: 3,
            borderWidth: 1,
            borderColor: colors.thumbnailBorder,
            backgroundColor: colors.thumbnail,
            pointerEvents: "none",
          }}
        >
          {node.thumbnailPath ? (
            <img
              src={node.thumbnailPath}
              alt=""
              objectFit="cover"
              style={{ width: 18, height: 18, pointerEvents: "none" }}
            />
          ) : typeGlyph(node) ? (
            <div style={{ width: 18, height: 18, display: "flex", alignItems: "center", justifyContent: "center" }}>
              <Icon name={typeGlyph(node)!} size={12} />
            </div>
          ) : null}
        </div>
      )}
      {node.masked ? (
        <div
          style={{
            position: "absolute",
            right: 0,
            bottom: 0,
            width: 10,
            height: 10,
            overflow: "hidden",
            borderRadius: 2,
            borderWidth: 1,
            borderColor: colors.thumbnailBorder,
            backgroundColor: colors.maskDark,
            pointerEvents: "none",
          }}
        >
          <svg source={maskThumbnailSource} style={{ width: 8, height: 8 }} />
        </div>
      ) : null}
    </div>
  )
}

/**
 * Rows whose arrival or departure the pointer just caused: a drop or a ×.
 * Only these fade in or out; undo, reset and reloads swap rows instantly
 * because keyboard and bulk changes should read as immediate.
 */
export const RowMotionContext = createContext<ReadonlySet<string>>(new Set())

const growDuration = 0.2
const shrinkDuration = 0.14

type ShownRow = { node: LayerNode; depth: number; leaving?: boolean }
type LeavingRow = ShownRow & { index: number }

/**
 * Rows the pointer removed from the tree stay in place while they fade, then
 * go. Only opacity moves: the virtual list needs every item at the fixed row
 * height, so a folding exit would leave phantom items. A removed folder's
 * visible children fade with it. Rows only hidden by a collapse, or removed
 * by undo or reset, are not in motion and leave at once.
 */
function useLeavingRows(nodes: LayerNode[], rows: ShownRow[], departing: ReadonlySet<string>) {
  const [track, setTrack] = useState<{ rows: ShownRow[]; leaving: LeavingRow[] }>({ rows, leaving: [] })
  let leaving = track.leaving
  if (track.rows !== rows) {
    // Derived during render, so a leaving row never unmounts for one commit.
    const present = new Set(rows.map(row => row.node.id))
    const gone: LeavingRow[] = []
    let rootDepth: number | null = null
    track.rows.forEach((row, index) => {
      if (rootDepth !== null && row.depth <= rootDepth) rootDepth = null
      const removed = !present.has(row.node.id) && !findNode(nodes, row.node.id)
      if (removed && (rootDepth !== null || departing.has(row.node.id))) {
        gone.push({ ...row, leaving: true, index })
        rootDepth ??= row.depth
      }
    })
    leaving = [...track.leaving.filter(row => !present.has(row.node.id)), ...gone]
    setTrack({ rows, leaving })
  }
  const left = useCallback((id: string) => {
    setTrack(current => ({ ...current, leaving: current.leaving.filter(row => row.node.id !== id) }))
  }, [])
  const shown = useMemo(() => {
    const merged: ShownRow[] = [...rows]
    for (const row of [...leaving].sort((a, b) => a.index - b.index)) merged.splice(Math.min(row.index, merged.length), 0, row)
    return merged
  }, [rows, leaving])
  return { shown, left }
}

function typeGlyph(node: LayerNode): "paintLayer" | "fillLayer" | null {
  if (node.ref.host !== "substance_painter") return null
  if (/fill/i.test(node.ref.kind)) return "fillLayer"
  if (/paint/i.test(node.ref.kind)) return "paintLayer"
  return null
}

/**
 * Hover and the drop target change on nearly every pointer move. They live in
 * this store instead of app state so a move re-renders the two rows whose
 * flag flipped, not both trees: every re-rendered row resends its style and
 * motion to GPUiX, which made pointer feedback lag behind the cursor.
 */
export type TreePointer = {
  draggingId: string | null
  draggingHost: HostId | null
  hoveredId: string | null
  dropTargetId: string | null
  dropPlacement: Placement | null
}

export function createTreePointer() {
  let state: TreePointer = { draggingId: null, draggingHost: null, hoveredId: null, dropTargetId: null, dropPlacement: null }
  const listeners = new Set<() => void>()
  return {
    get: () => state,
    set(next: Partial<TreePointer>) {
      const merged = { ...state, ...next }
      if ((Object.keys(merged) as (keyof TreePointer)[]).every(key => merged[key] === state[key])) return
      state = merged
      for (const listener of listeners) listener()
    },
    subscribe(listener: () => void) {
      listeners.add(listener)
      return () => { listeners.delete(listener) }
    },
  }
}

export type TreePointerStore = ReturnType<typeof createTreePointer>

/** Selectors return primitives or stored references, so unchanged rows skip rendering. */
function usePointer<T>(store: TreePointerStore, select: (state: TreePointer) => T) {
  return useSyncExternalStore(store.subscribe, () => select(store.get()))
}

/** Every value here must stay referentially stable between pointer moves. */
export type TreeInteraction = {
  host: HostId
  pointer: TreePointerStore
  selectedIds: Set<string>
  mappedIds: Set<string>
  pendingNotes: Map<string, string>
  expanded: Set<string>
  onToggle: (id: string) => void
  onDragStart: (id: string, event: EventPayload, readBounds: () => ElementBounds | null) => void
  onPointerMove: (event: EventPayload, rowId?: string, readBounds?: () => ElementBounds | null) => void
  onDragEnd: () => void
  onHover: (id: string | null) => void
  onDrop: (id: string) => void
  onRemove: (id: string) => void
}

type LayerRowProps = TreeInteraction & {
  node: LayerNode
  depth: number
  leaving?: boolean
  onLeft?: (id: string) => void
}

const LayerRow = memo(function LayerRow({ node, depth, leaving = false, onLeft, ...interaction }: LayerRowProps) {
  const {
    host, pointer, selectedIds, mappedIds, pendingNotes,
    expanded, onToggle, onDragStart, onPointerMove,
    onDragEnd, onHover, onDrop, onRemove,
  } = interaction
  const open = node.kind === "group" && expanded.has(node.id)
  const nativeNode = node.ref.host === host
  // A leaving row shows what it was, not the mapping its layer now belongs to elsewhere.
  const selected = !leaving && selectedIds.has(node.id)
  const draggingHost = usePointer(pointer, state => state.hoveredId === node.id || state.dropTargetId === node.id || selected ? state.draggingHost : null)
  const dragging = draggingHost !== null
  // Native rows and rows staged here by an earlier drop both take drops.
  const dropCandidate = nativeNode || (!leaving && mappedIds.has(node.id))
  const acceptsDrop = dropCandidate && draggingHost !== null && draggingHost !== host
  const placement = usePointer(pointer, state => state.dropTargetId === node.id ? state.dropPlacement : null)
  const dropAt = acceptsDrop ? placement : null
  const boundsCache = useContext(RowBoundsContext)!
  const header = useRef<PublicInstance>(null)
  const mapped = !leaving && mappedIds.has(node.id)
  const hovered = usePointer(pointer, state => state.hoveredId === node.id)
  const animated = useContext(RowMotionContext).has(node.id)
  const height = metrics.rowHeight
  const readBounds = (fresh = false) => header.current ? boundsCache.read(header.current.id, fresh) : null
  const release = (event: EventPayload) => {
    const current = pointer.get()
    if (dropCandidate && current.draggingId && current.draggingHost !== host) {
      // A wheel event or window resize can race the last move. The final drop
      // uses fresh geometry, without forcing every intermediate move to read it.
      onPointerMove({ ...event, pressedButton: 0 }, node.id, () => readBounds(true))
      onDrop(node.id)
    }
    onDragEnd()
  }

  return (
    <Motion
      testId={`layer-group:${node.id}`}
      initial={animated ? { opacity: 0 } : false}
      animate={{ opacity: leaving ? 0 : 1 }}
      transition={{ duration: leaving ? shrinkDuration : growDuration, ease: motionEase }}
      onMotionComplete={leaving ? () => onLeft?.(node.id) : undefined}
      style={{
        pointerEvents: leaving ? "none" : undefined,
        // Fixed row geometry keeps virtual-list indices and cached drop bounds
        // valid; height exits would retain phantom items while recycling rows.
        height,
        position: "relative", display: "flex", flexDirection: "column", minWidth: 0, flexShrink: 0,
        overflow: "hidden", borderRadius: metrics.rowRadius,
        width: "100%", paddingLeft: depth * metrics.treeIndent,
      }}
    >
      <div
        ref={header}
        testId={`layer-row:${node.id}`}
        aria-selected={selected}
        // Only the header owns pointer events: a folder's descendants must not
        // replace the hovered row or its drop target through ancestor handlers.
        onMouseEnter={() => onHover(node.id)}
        onMouseLeave={() => { if (pointer.get().hoveredId === node.id) onHover(null) }}
        onMouseMove={event => {
          if (pointer.get().hoveredId !== node.id) onHover(node.id)
          onPointerMove(event, node.id, readBounds)
        }}
        onMouseUp={release}
        style={{
          position: "relative",
          height: metrics.rowHeight, flexShrink: 0,
          paddingLeft: 8, paddingRight: 8,
          display: "flex", flexDirection: "row", alignItems: "center", gap: 8,
          borderRadius: metrics.rowRadius,
          backgroundColor: selected ? colors.controlActive : hovered && !node.locked ? colors.controlHover : mapped ? colors.mapped : undefined,
          // Locked rows stay in the tree so the Photoshop hierarchy reads true,
          // while their detail line explains why they cannot be dragged.
          // Every carried row dims, not only the pressed one: they left together.
          opacity: node.locked ? 0.5 : dragging && selected ? 0.65 : 1,
          // The cursor answers "can I drop here" before the button is released.
          cursor: dragging ? (acceptsDrop ? "grabbing" : "no-drop") : node.locked ? "default" : "grab",
        }}
      >
        <div
          testId={`layer-toggle:${node.id}`}
          onClick={() => { onDragEnd(); if (node.kind === "group") onToggle(node.id) }}
          style={{
            width: 14, height: 28, flexShrink: 0,
            display: "flex", alignItems: "center", justifyContent: "center",
            cursor: dragging ? undefined : node.kind === "group" ? "pointer" : "default",
          }}
        >
          {node.kind === "group" ? <DisclosureIcon open={open} /> : null}
        </div>
        <div
          testId={`layer-drag:${node.id}`}
          onMouseDown={event => { if (event.button === 0) onDragStart(node.id, event, readBounds) }}
          onMouseUp={release}
          style={{ minWidth: 0, flexGrow: 1, height: "100%", display: "flex", flexDirection: "row", alignItems: "center", gap: 8,
            active: node.locked ? undefined : { cursor: "grabbing" } }}
        >
          <LayerThumbnail node={node} />
          <div style={{ minWidth: 0, flexGrow: 1, display: "flex", flexDirection: "column" }}>
            {/* Explicit line heights: the default leading stacked two lines taller than the row. */}
            <PrimaryText lineHeight={16}>{node.name}</PrimaryText>
            {mapped || node.locked || node.note ? <text style={{
              fontSize: typography.secondarySize, lineHeight: 14, color: colors.secondary,
              whiteSpace: "nowrap", textOverflow: "ellipsis",
            }}>{mapped ? pendingNotes.get(node.id) ?? "Pending" : node.locked ?? node.note}</text> : null}
          </div>
        </div>
        {nativeNode ? <div
          testId={`layer-remove:${node.id}`}
          onClick={() => { onDragEnd(); onRemove(node.id) }}
          style={{
            width: 22, height: 22, flexShrink: 0, display: "flex",
            alignItems: "center", justifyContent: "center", borderRadius: 5,
            cursor: "pointer", hover: { backgroundColor: colors.controlActive },
            opacity: hovered ? 1 : 0, pointerEvents: hovered ? undefined : "none",
          }}
        >
          <Icon name="x" size={12} color={colors.secondary} />
        </div> : null}
        {/* Hover never lights folders, so a drop says where it lands on its own:
            a framed folder takes the layers inside, a line marks above or below.
            Drawn inside the header, after its content, so the marks share the
            hover box exactly and its fill cannot cover them. */}
        {dropAt === "inside" ? <div
          testId={`drop-indicator:${node.id}`}
          style={{
            position: "absolute", left: 0, right: 0, top: 0, bottom: 0,
            borderWidth: 1, borderColor: colors.drop, borderRadius: metrics.rowRadius, pointerEvents: "none",
          }}
        /> : dropAt ? <DropLine testId={`drop-indicator:${node.id}`} top={dropAt === "before" ? 0 : metrics.rowHeight - 6} /> : null}
      </div>
    </Motion>
  )
}, (previous, next) => {
  // Collection identity changes on every selection. Only this row's flags
  // matter; drag feedback comes from the pointer store, not stale memo props.
  const { selectedIds: a, mappedIds: b, pendingNotes: c, expanded: d, ...rest } = previous
  const { selectedIds: e, mappedIds: f, pendingNotes: g, expanded: h, ...nextRest } = next
  const id = next.node.id
  return a.has(id) === e.has(id) && b.has(id) === f.has(id) && c.get(id) === g.get(id) && d.has(id) === h.has(id)
    && (Object.keys(rest) as (keyof typeof rest)[]).every(key => rest[key] === nextRest[key])
})

/**
 * A 2px insertion line with a dot at its start, inside the row header so it
 * spans exactly the hover box, like the folder frame.
 */
function DropLine({ testId, top }: { testId: string; top: number }) {
  return (
    <div testId={testId} style={{
      position: "absolute", left: 0, right: 0, top, height: 6, pointerEvents: "none",
      display: "flex", flexDirection: "row", alignItems: "center",
    }}>
      <div style={{ width: 6, height: 6, flexShrink: 0, borderRadius: 3, borderWidth: 1.5, borderColor: colors.drop }} />
      <div style={{ flexGrow: 1, height: 2, backgroundColor: colors.drop }} />
    </div>
  )
}

export function HostPanel({
  panelId,
  title,
  subtitle,
  nodes,
  headerAction,
  emptyContent,
  onTrackPointer,
  contentKey,
  ...interaction
}: {
  panelId: "photoshop" | "painter"
  title: string
  subtitle: string
  nodes: LayerNode[]
  headerAction?: React.ReactNode
  emptyContent?: React.ReactNode
  onTrackPointer: (event: EventPayload) => void
  /** Names what the tree shows: a document or a Painter target. */
  contentKey: string
} & TreeInteraction) {
  const dragging = usePointer(interaction.pointer, state => state.draggingId !== null)
  // A different document or target fades its tree in so the swap does not
  // read as a glitch. Reloads, Apply refreshes and the window's first frame
  // keep the key, so they stay instant.
  const shown = useRef({ key: contentKey, fade: false })
  const rows = useMemo(() => visibleLayerRows(nodes, interaction.expanded), [nodes, interaction.expanded])
  const { shown: shownRows, left } = useLeavingRows(nodes, rows, useContext(RowMotionContext))
  const layoutKey = useMemo(() => ({}), [shownRows])
  if (shown.current.key !== contentKey) shown.current = { key: contentKey, fade: true }
  // Host surfaces stay borderless; background and elevation separate them from the workspace.
  return (
    <div
      testId={`layer-panel:${panelId}`}
      // GPUiX delivers pointer moves no higher than the host panels, so the
      // drag preview is fed here; drops only land inside a panel anyway.
      onMouseMove={onTrackPointer}
      style={{
        // Rows that accept the drop override this; releasing anywhere else cancels.
        cursor: dragging ? "no-drop" : undefined,
        flexGrow: 1,
        flexBasis: 0,
        minWidth: 0,
        height: "100%",
        display: "flex",
        flexDirection: "column",
        borderRadius: metrics.cardRadius,
        backgroundColor: colors.panel,
        boxShadow: {
          offsetX: 0,
          offsetY: 7,
          blurRadius: 18,
          spreadRadius: 0,
          color: "#00000045",
        },
        overflow: "hidden",
      }}
    >
      <div
        style={{
          flexShrink: 0,
          display: "flex",
          flexDirection: "row",
          alignItems: "flex-start",
          justifyContent: "space-between",
          gap: 8,
          paddingTop: 12,
          paddingRight: 16,
          paddingBottom: 10,
          paddingLeft: 16,
        }}
      >
        <div
          style={{
            minWidth: 0,
            display: "flex",
            flexDirection: "column",
            gap: 2,
          }}
        >
          <text
            style={{
              color: colors.text,
              fontFamily: typography.family,
              fontSize: typography.labelSize,
              fontWeight: typography.labelWeight,
              whiteSpace: "nowrap",
              textOverflow: "ellipsis",
            }}
          >
            {title}
          </text>
          <SecondaryText>{subtitle}</SecondaryText>
        </div>
        {headerAction}
      </div>
      <InsetSeparator />
      {emptyContent ? (
        <div style={{ flexGrow: 1, flexBasis: 0, minHeight: 0 }}>{emptyContent}</div>
      ) : <motion.div
        key={contentKey}
        initial={shown.current.fade ? { opacity: 0 } : false}
        animate={{ opacity: 1 }}
        transition={{ duration: 0.16, ease: motionEase }}
        style={{ flexGrow: 1, flexBasis: 0, minHeight: 0, display: "flex", flexDirection: "column" }}
      ><LayerScroll id={panelId} layoutKey={layoutKey} rowCount={shownRows.length} renderRow={index => {
        const { node, depth, leaving } = shownRows[index]
        return <LayerRow key={node.id} node={node} depth={depth} leaving={leaving} onLeft={left} {...interaction} />
      }} /></motion.div>}
    </div>
  )
}

