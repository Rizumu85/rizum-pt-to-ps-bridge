import { LayerScroll } from "./layer-scroll"
import { motion, type EventPayload } from "@gpuix/react"
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

type TreeInteraction = {
  host: HostId
  selectedIds: Set<string>
  mappedIds: Set<string>
  hoveredId: string | null
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
    host, selectedIds, mappedIds, hoveredId, draggingId,
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

  return (
    <div
      testId={`layer-group:${node.id}`}
      style={{
        position: "relative", display: "flex", flexDirection: "column", minWidth: 0,
        borderRadius: metrics.rowRadius,
      }}
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
          cursor: node.locked ? "default" : "move",
        }}
      >
        <div
          testId={`layer-toggle:${node.id}`}
          onClick={() => { onDragEnd(); if (node.kind === "group") onToggle(node.id) }}
          style={{
            width: 14, height: 28, flexShrink: 0,
            display: "flex", alignItems: "center", justifyContent: "center",
            cursor: node.kind === "group" ? "pointer" : "default",
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
            {mapped ? <text style={{ fontSize: typography.secondarySize, color: colors.secondary }}>Pending</text> : null}
          </div>
        </div>
        {nativeNode ? <div
          testId={`layer-remove:${node.id}`}
          onClick={() => { onDragEnd(); onRemove(node.id) }}
          style={{
            width: 22, height: 22, flexShrink: 0, display: "flex",
            alignItems: "center", justifyContent: "center", borderRadius: 5,
            cursor: "pointer", hover: { backgroundColor: "#FF453A29" },
            opacity: hovered ? 1 : 0, pointerEvents: hovered ? undefined : "none",
          }}
        >
          <Icon name="x" size={12} color={colors.danger} />
        </div> : null}
      </div>
      {node.kind === "group" ? <motion.div
        initial={false}
        animate={{ height: open ? visibleNodesHeight(children, expanded) : 0, opacity: open ? 1 : 0 }}
        transition={{ duration: 0.2, ease: motionEase }}
        style={{
          display: "flex", flexDirection: "column", overflow: "hidden",
          // Depth has one owner; folder decoration must not shift sibling columns.
          marginLeft: metrics.treeIndent, pointerEvents: open ? undefined : "none",
        }}
      >
        {children.map(child => <LayerRow key={child.id} node={child} {...interaction} />)}
      </motion.div> : null}
    </div>
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
}: {
  panelId: "photoshop" | "painter"
  title: string
  subtitle: string
  nodes: LayerNode[]
  headerAction?: React.ReactNode
  emptyContent?: React.ReactNode
} & TreeInteraction) {
  // Host surfaces stay borderless; background and elevation separate them from the workspace.
  return (
    <div
      style={{
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
      ) : <LayerScroll id={panelId}>
          {nodes.map(node => <LayerRow
            key={node.id}
            node={node}
            host={host}
            selectedIds={selectedIds} mappedIds={mappedIds}
            hoveredId={hoveredId}
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
      </LayerScroll>}
    </div>
  )
}

