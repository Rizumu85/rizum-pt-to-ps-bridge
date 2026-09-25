import { createContext, memo, useContext, useRef, useSyncExternalStore } from "react"
import { LayerScroll } from "./layer-scroll"
import { AnimatePresence, motion, useIsPresent, type EventPayload, type MotionTransition } from "@gpuix/react"
import { type HostId, type LayerNode } from "./model"
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
import { visibleNodesHeight } from "./bridge-app"

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
 * Rows whose departure the pointer just caused: the source rows of a drop, or
 * a ×. Only these fold away; undo, reset and reloads swap rows instantly
 * because keyboard and bulk changes should read as immediate. Arrivals never
 * grow in: the drop gap already made their space. It is context, not a prop,
 * because a leaving row renders from its last props.
 */
export const RowMotionContext = createContext<ReadonlySet<string>>(new Set())

// Growth is the user watching something open; shrinking is dismissal, so it
// is quicker. Every height in the tree uses this one rule, which keeps nested
// folders and their ancestors moving as one surface.
const growDuration = 0.2
const shrinkDuration = 0.14

function useHeightTransition(height: number, instant: boolean): MotionTransition {
  const last = useRef({ height, duration: growDuration })
  if (last.current.height !== height) {
    const duration = instant ? 0 : height < last.current.height ? shrinkDuration : growDuration
    last.current = { height, duration }
  }
  return { duration: last.current.duration, ease: motionEase }
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
export type DropGhost = { id: string; name: string; depth: number; kind: LayerNode["kind"] }

export type TreePointer = {
  hoveredId: string | null
  dropTargetId: string | null
  /** The drop target and the folders enclosing it: every row whose height holds the gap. */
  dropPath: ReadonlySet<string>
  /** What the drop will insert, as the rows it will show; fixed for one drag. */
  ghosts: readonly DropGhost[]
  gapHeight: number
  /** The gap is closing because its rows just landed in it, so it closes at once. */
  landing: boolean
}

export const noDropPath: ReadonlySet<string> = new Set()

export function createTreePointer() {
  let state: TreePointer = {
    hoveredId: null, dropTargetId: null, dropPath: noDropPath, ghosts: [], gapHeight: 0, landing: false,
  }
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
  draggingId: string | null
  draggingHost: HostId | null
  expanded: Set<string>
  onToggle: (id: string) => void
  onDragStart: (id: string, event: EventPayload) => void
  onPointerMove: (event: EventPayload, rowId?: string) => void
  onDragEnd: () => void
  onHover: (id: string | null) => void
  onDrop: (id: string) => void
  onRemove: (id: string) => void
}

const LayerRow = memo(function LayerRow({ node, ...interaction }: TreeInteraction & { node: LayerNode }) {
  const {
    host, pointer, selectedIds, mappedIds, pendingNotes, draggingId,
    draggingHost, expanded, onToggle, onDragStart, onPointerMove,
    onDragEnd, onHover, onDrop, onRemove,
  } = interaction
  const open = node.kind === "group" && expanded.has(node.id)
  const nativeNode = node.ref.host === host
  const acceptsDrop = nativeNode && draggingHost !== null && draggingHost !== host
  const activeDrop = usePointer(pointer, state => state.dropTargetId === node.id) && acceptsDrop
  const gap = usePointer(pointer, state => state.dropPath.has(node.id) ? state.gapHeight : 0)
  const landing = usePointer(pointer, state => state.landing)
  const mapped = mappedIds.has(node.id)
  const hovered = usePointer(pointer, state => state.hoveredId === node.id)
  const selected = selectedIds.has(node.id)
  const children = node.children ?? []
  const present = useIsPresent()
  const animated = useContext(RowMotionContext).has(node.id)
  const height = metrics.rowHeight + (open ? visibleNodesHeight(children, expanded) : 0) + gap
  const heightTransition = useHeightTransition(height, landing)
  const dragging = draggingId !== null
  // A group takes drops at the end of its layers, a layer right below itself.
  const dropGap = activeDrop ? <DropGap
    pointer={pointer}
    indent={node.kind === "group"}
    onPointerMove={event => onPointerMove(event, node.id)}
    onRelease={() => { if (draggingId) onDrop(node.id); onDragEnd() }}
  /> : null

  return (
    <Motion
      testId={`layer-group:${node.id}`}
      initial={false}
      animate={{ height, opacity: 1 }}
      exit={animated ? { height: 0, opacity: 0 } : undefined}
      transition={present ? heightTransition : { duration: shrinkDuration, ease: motionEase }}
      style={{
        position: "relative", display: "flex", flexDirection: "column", minWidth: 0, flexShrink: 0,
        overflow: "hidden", borderRadius: metrics.rowRadius,
        pointerEvents: present ? undefined : "none",
      }}
    >
      {/* Hover never lights folders, so a framed folder says the drop goes
          inside it; the gap then shows exactly where the rows will land. */}
      {activeDrop && node.kind === "group" ? <div
        testId={`drop-indicator:${node.id}`}
        style={{
          position: "absolute", left: 0, right: 0, top: 0, height: metrics.rowHeight,
          borderWidth: 1, borderColor: colors.drop, borderRadius: metrics.rowRadius, pointerEvents: "none",
        }}
      /> : null}
      <div
        testId={`layer-row:${node.id}`}
        aria-selected={selected}
        // Only the header owns pointer events: a folder's descendants must not
        // replace the hovered row or its drop target through ancestor handlers.
        onMouseEnter={() => onHover(node.id)}
        onMouseLeave={() => { if (hovered) onHover(null) }}
        onMouseMove={event => {
          if (!hovered) onHover(node.id)
          onPointerMove(event, node.id)
        }}
        onMouseUp={() => {
          if (acceptsDrop && draggingId) onDrop(node.id)
          onDragEnd()
        }}
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
          onMouseDown={event => { if (event.button === 0) onDragStart(node.id, event) }}
          onMouseUp={() => { if (acceptsDrop && draggingId) onDrop(node.id); onDragEnd() }}
          style={{ minWidth: 0, flexGrow: 1, height: "100%", display: "flex", flexDirection: "row", alignItems: "center", gap: 8 }}
        >
          <LayerThumbnail node={node} />
          <div style={{ minWidth: 0, flexGrow: 1, display: "flex", flexDirection: "column" }}>
            <PrimaryText>{node.name}</PrimaryText>
            {mapped || node.locked || node.note ? <text style={{
              fontSize: typography.secondarySize, color: colors.secondary,
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
      </div>
      {open ? null : dropGap}
      {/* The row wrapper owns the folder's height, so children only fade. */}
      {node.kind === "group" ? <motion.div
        initial={false}
        animate={{ opacity: open ? 1 : 0 }}
        transition={heightTransition}
        style={{
          display: "flex", flexDirection: "column", flexShrink: 0,
          // Depth has one owner; folder decoration must not shift sibling columns.
          marginLeft: metrics.treeIndent, pointerEvents: open ? undefined : "none",
        }}
      >
        <AnimatePresence initial={false}>
          {children.map(child => <LayerRow key={child.id} node={child} {...interaction} />)}
        </AnimatePresence>
      </motion.div> : null}
      {open ? dropGap : null}
    </Motion>
  )
})

/**
 * The space a drop will fill, holding faint copies of the rows it inserts.
 * Its height equals those rows, so on release they land in it without the
 * tree moving. It keeps the drop target while the pointer is over it;
 * otherwise opening the gap would pull the target out from under the cursor.
 */
function DropGap({ pointer, indent, onPointerMove, onRelease }: {
  pointer: TreePointerStore
  indent: boolean
  onPointerMove: (event: EventPayload) => void
  onRelease: () => void
}) {
  const ghosts = usePointer(pointer, state => state.ghosts)
  const height = usePointer(pointer, state => state.gapHeight)
  return (
    <div
      testId="drop-gap"
      onMouseMove={onPointerMove}
      onMouseUp={onRelease}
      style={{
        height, flexShrink: 0, marginLeft: indent ? metrics.treeIndent : 0,
        display: "flex", flexDirection: "column",
        borderRadius: metrics.rowRadius, borderWidth: 1, borderColor: colors.dropGhostBorder,
        backgroundColor: colors.dropGhost, overflow: "hidden", cursor: "grabbing",
      }}
    >
      {ghosts.map(ghost => (
        <div
          key={ghost.id}
          style={{
            height: metrics.rowHeight, flexShrink: 0, display: "flex", flexDirection: "row",
            alignItems: "center", gap: 8, paddingLeft: 8 + 22 + ghost.depth * metrics.treeIndent,
            paddingRight: 8, opacity: 0.6, pointerEvents: "none",
          }}
        >
          {ghost.kind === "group" ? <Icon name="folder" size={14} /> : <div style={{
            width: 14, height: 14, flexShrink: 0, borderRadius: 3,
            borderWidth: 1, borderColor: colors.thumbnailBorder,
          }} />}
          <text style={{
            color: colors.secondary, fontFamily: typography.family, fontSize: typography.primarySize,
            whiteSpace: "nowrap", textOverflow: "ellipsis",
          }}>{ghost.name}</text>
        </div>
      ))}
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
  // A different document or target fades its tree in so the swap does not
  // read as a glitch. Reloads, Apply refreshes and the window's first frame
  // keep the key, so they stay instant.
  const shown = useRef({ key: contentKey, fade: false })
  if (shown.current.key !== contentKey) shown.current = { key: contentKey, fade: true }
  // Host surfaces stay borderless; background and elevation separate them from the workspace.
  return (
    <div
      // GPUiX delivers pointer moves no higher than the host panels, so the
      // drag preview is fed here; drops only land inside a panel anyway.
      onMouseMove={onTrackPointer}
      style={{
        // Rows that accept the drop override this; releasing anywhere else cancels.
        cursor: interaction.draggingId ? "no-drop" : undefined,
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
      ><LayerScroll id={panelId}><AnimatePresence initial={false}>
          {nodes.map(node => <LayerRow key={node.id} node={node} {...interaction} />)}
      </AnimatePresence></LayerScroll></motion.div>}
    </div>
  )
}

