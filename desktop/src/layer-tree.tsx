import { createContext, useContext, useRef } from "react"
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
 * Rows whose arrival or departure the pointer just caused: a drop or a ×.
 * Only these grow in or fold away; undo, reset and reloads swap rows instantly
 * because keyboard and bulk changes should read as immediate. It is context,
 * not a prop, because a leaving row renders from its last props.
 */
export const RowMotionContext = createContext<ReadonlySet<string>>(new Set())

// Growth is the user watching something open; shrinking is dismissal, so it
// is quicker. Every height in the tree uses this one rule, which keeps nested
// folders and their ancestors moving as one surface.
const growDuration = 0.2
const shrinkDuration = 0.14

function useHeightTransition(height: number): MotionTransition {
  const last = useRef({ height, duration: growDuration })
  if (last.current.height !== height) {
    last.current = { height, duration: height < last.current.height ? shrinkDuration : growDuration }
  }
  return { duration: last.current.duration, ease: motionEase }
}

function typeGlyph(node: LayerNode): "paintLayer" | "fillLayer" | null {
  if (node.ref.host !== "substance_painter") return null
  if (/fill/i.test(node.ref.kind)) return "fillLayer"
  if (/paint/i.test(node.ref.kind)) return "paintLayer"
  return null
}

type TreeInteraction = {
  host: HostId
  selectedIds: Set<string>
  mappedIds: Set<string>
  hoveredId: string | null
  pendingNotes: Map<string, string>
  draggingId: string | null
  draggingHost: HostId | null
  dropTargetId: string | null
  expanded: Set<string>
  onToggle: (id: string) => void
  onDragStart: (id: string, event: EventPayload) => void
  onPointerMove: (event: EventPayload, rowId?: string) => void
  onDragEnd: () => void
  onHover: (id: string | null) => void
  onDrop: (id: string) => void
  onRemove: (id: string) => void
}

function LayerRow({ node, ...interaction }: TreeInteraction & { node: LayerNode }) {
  const {
    host, selectedIds, mappedIds, hoveredId, pendingNotes, draggingId,
    draggingHost, dropTargetId, expanded, onToggle, onDragStart, onPointerMove,
    onDragEnd, onHover, onDrop, onRemove,
  } = interaction
  const open = node.kind === "group" && expanded.has(node.id)
  const nativeNode = node.ref.host === host
  const acceptsDrop = nativeNode && draggingHost !== null && draggingHost !== host
  const activeDrop = acceptsDrop && dropTargetId === node.id
  const mapped = mappedIds.has(node.id)
  const hovered = hoveredId === node.id
  const selected = selectedIds.has(node.id)
  const children = node.children ?? []
  const present = useIsPresent()
  const animated = useContext(RowMotionContext).has(node.id)
  const height = metrics.rowHeight + (open ? visibleNodesHeight(children, expanded) : 0)
  const heightTransition = useHeightTransition(height)
  const dragging = draggingId !== null

  return (
    <motion.div
      initial={animated ? { height: 0, opacity: 0 } : false}
      animate={{ height, opacity: 1 }}
      exit={animated ? { height: 0, opacity: 0 } : undefined}
      transition={present ? heightTransition : { duration: shrinkDuration, ease: motionEase }}
      style={{
        display: "flex", flexDirection: "column", minWidth: 0, flexShrink: 0,
        overflow: "hidden", borderRadius: metrics.rowRadius,
        pointerEvents: present ? undefined : "none",
      }}
    ><div
      testId={`layer-group:${node.id}`}
      style={{ position: "relative", display: "flex", flexDirection: "column", minWidth: 0, flexShrink: 0 }}
    >
      {/* Hover never lights folders, so a drop says where it lands on its own:
          a framed folder row takes the layers inside, a line inserts after. */}
      {activeDrop ? <div
        testId={`drop-indicator:${node.id}`}
        style={node.kind === "group" ? {
          position: "absolute", left: 0, right: 0, top: 0, height: metrics.rowHeight,
          borderWidth: 1, borderColor: colors.drop, borderRadius: metrics.rowRadius, pointerEvents: "none",
        } : {
          position: "absolute", left: 5, right: 5, top: metrics.rowHeight - 2, height: 2,
          backgroundColor: colors.drop, pointerEvents: "none",
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
          opacity: node.locked ? 0.5 : draggingId === node.id ? 0.65 : 1,
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
    </div></motion.div>
  )
}

export function HostPanel({
  panelId,
  title,
  subtitle,
  nodes,
  host,
  headerAction,
  emptyContent,
  selectedIds,
  mappedIds,
  hoveredId,
  pendingNotes,
  draggingId,
  draggingHost,
  dropTargetId,
  expanded,
  onToggle,
  onDragStart,
  onPointerMove,
  onDragEnd,
  onHover,
  onDrop,
  onRemove,
  onTrackPointer,
  contentKey,
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
        cursor: draggingId ? "no-drop" : undefined,
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
          {nodes.map(node => <LayerRow
            key={node.id}
            node={node}
            host={host}
            selectedIds={selectedIds} mappedIds={mappedIds}
            hoveredId={hoveredId} pendingNotes={pendingNotes}
            draggingId={draggingId}
            draggingHost={draggingHost}
            dropTargetId={dropTargetId}
            expanded={expanded}
            onToggle={onToggle}
            onDragStart={onDragStart}
            onPointerMove={onPointerMove}
            onDragEnd={onDragEnd}
            onHover={onHover}
            onDrop={onDrop}
            onRemove={onRemove}
          />)}
      </AnimatePresence></LayerScroll></motion.div>}
    </div>
  )
}

