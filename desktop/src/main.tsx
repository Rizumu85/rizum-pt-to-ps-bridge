import { useEffect, useMemo, useRef, useState } from "react"
import { LayerScroll } from "./layer-scroll"
import {
  motion,
  render,
  useGpuixRequired,
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
  type MotionEase,
  type PublicInstance,
  type EventPayload,
} from "@gpuix/react"

import iconCheck from "../../icons/checkmark.svg" with { type: "text" }
import iconChevronDown from "../../icons/chevron-down.svg" with { type: "text" }
import iconChevronRight from "../../icons/chevron-right.svg" with { type: "text" }
import iconChevronUp from "../../icons/chevron-up.svg" with { type: "text" }
import iconFolder from "../../icons/folder.svg" with { type: "text" }
import iconRedo from "../../icons/redo.svg" with { type: "text" }
import iconReset from "../../icons/reset.svg" with { type: "text" }
import iconUndo from "../../icons/undo.svg" with { type: "text" }
import iconX from "../../icons/x.svg" with { type: "text" }

import {
  cloneState,
  findNode,
  removeFromHost,
  transferSelection,
  selectLayerIds,
  visibleSourceIds,
  type BridgeState,
  type HostId,
  type LayerNode,
} from "./model"
import { colors, metrics, typography } from "./theme"
import {
  connectPhotoshop,
  createPainterLink,
  failedBridgeSession,
  loadBridgeSession,
  parseSessionOptions,
  writeTransferManifest,
  type BridgeSession,
  type PainterContext,
} from "./transport"

const icons = {
  check: iconCheck,
  chevronDown: iconChevronDown,
  chevronRight: iconChevronRight,
  chevronUp: iconChevronUp,
  folder: iconFolder,
  redo: iconRedo,
  reset: iconReset,
  undo: iconUndo,
  x: iconX,
} as const

const motionEase: MotionEase = [0.23, 1, 0.32, 1]
const maskThumbnailSource = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 8 8"><rect width="8" height="8" fill="${colors.maskDark}"/><path d="M0 8 8 0v8Z" fill="${colors.maskLight}"/></svg>`

type IconName = keyof typeof icons
type ContextOption = { value: string; label: string }

function Icon({
  name,
  size = 14,
  color = colors.secondary,
}: {
  name: IconName
  size?: number | string
  color?: string
}) {
  const source = icons[name].replace(/#[0-9a-f]{6}/gi, color)
  return <svg source={source} style={{ width: size, height: size, flexShrink: 0, color, pointerEvents: "none" }} />
}

function DisclosureIcon({ open }: { open: boolean }) {
  return (
    <div style={{ width: 12, height: 12, position: "relative" }}>
      {(["chevronRight", "chevronDown"] as const).map((name) => {
        const visible = name === (open ? "chevronDown" : "chevronRight")
        return (
          <motion.div
            key={name}
            initial={false}
            animate={{ opacity: visible ? 1 : 0 }}
            transition={{ duration: 0.12, ease: motionEase }}
            style={{
              position: "absolute",
              // GPUiX gives absolute decoration its own hitbox, even at opacity 0.
              pointerEvents: "none",
              top: 0,
              left: 0,
              width: 12,
              height: 12,
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
            }}
          >
            <Icon name={name} size={11} />
          </motion.div>
        )
      })}
    </div>
  )
}

function PrimaryText({ children }: { children: React.ReactNode }) {
  return (
    <text
      style={{
        color: colors.text,
        fontFamily: typography.family,
        fontSize: typography.primarySize,
        fontWeight: typography.primaryWeight,
        whiteSpace: "nowrap",
        textOverflow: "ellipsis",
      }}
    >
      {children}
    </text>
  )
}

function SecondaryText({ children }: { children: React.ReactNode }) {
  return (
    <text
      style={{
        color: colors.tertiary,
        fontFamily: typography.family,
        fontSize: typography.secondarySize,
        fontWeight: typography.secondaryWeight,
        whiteSpace: "nowrap",
        textOverflow: "ellipsis",
      }}
    >
      {children}
    </text>
  )
}

function InsetSeparator() {
  return (
    <div style={{ height: 1, flexShrink: 0, paddingLeft: 12, paddingRight: 12 }}>
      <div style={{ width: "100%", height: 1, backgroundColor: colors.line }} />
    </div>
  )
}

function ContextSelect({
  label,
  value,
  options,
  width,
  busy = false,
  onValueChange,
}: {
  label: string
  value: string
  options: ContextOption[]
  width: number
  busy?: boolean
  onValueChange: (value: string) => void
}) {
  const [present, setPresent] = useState(false)
  const [visuallyOpen, setVisuallyOpen] = useState(false)
  const closeTimer = useRef<ReturnType<typeof setTimeout> | null>(null)
  const disabled = busy || options.length < 2
  const selectedLabel = options.find((option) => option.value === value)?.label || value

  useEffect(
    () => () => {
      if (closeTimer.current) clearTimeout(closeTimer.current)
    },
    [],
  )

  const setOpen = (nextOpen: boolean) => {
    if (closeTimer.current) {
      clearTimeout(closeTimer.current)
      closeTimer.current = null
    }
    if (nextOpen) {
      setPresent(true)
      setVisuallyOpen(true)
      return
    }

    setVisuallyOpen(false)
    closeTimer.current = setTimeout(() => {
      setPresent(false)
      closeTimer.current = null
    }, 180)
  }

  return (
    <Select
      value={value}
      open={present}
      onOpenChange={setOpen}
      onValueChange={onValueChange}
      disabled={disabled}
      style={{ flexShrink: 0 }}
    >
      <SelectTrigger
        testId={`context-select:${label}`}
        style={{
          width,
          height: 26,
          paddingLeft: 9,
          paddingRight: 9,
          display: "flex",
          flexDirection: "row",
          alignItems: "center",
          gap: 4,
          borderRadius: metrics.rowRadius,
          backgroundColor: visuallyOpen ? colors.fieldHover : "transparent",
          opacity: disabled ? 0.72 : 1,
          cursor: disabled ? "default" : "pointer",
          hover: disabled ? undefined : { backgroundColor: colors.fieldHover },
        }}
      >
        <SecondaryText>{label}</SecondaryText>
        <div style={{ minWidth: 0, flexGrow: 1 }}>
          <PrimaryText>{selectedLabel}</PrimaryText>
        </div>
        <div style={{ width: 12, height: 12, flexShrink: 0, position: "relative" }}>
          {(["chevronDown", "chevronUp"] as const).map((name) => {
            const visible = name === (visuallyOpen ? "chevronUp" : "chevronDown")
            return (
              <motion.div
                key={name}
                initial={false}
                animate={{ opacity: visible ? 1 : 0 }}
                transition={{ duration: 0.18, ease: motionEase }}
                style={{
                  position: "absolute",
                  pointerEvents: "none",
                  top: 0,
                  left: 0,
                  width: 12,
                  height: 12,
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                }}
              >
                <Icon name={name} size={12} />
              </motion.div>
            )
          })}
        </div>
      </SelectTrigger>
      <SelectContent
        side="bottom"
        sideOffset={4}
        align="start"
        collisionPadding={8}
        style={{ width, backgroundColor: "transparent", pointerEvents: visuallyOpen ? undefined : "none" }}
      >
        <motion.div
          initial={{ opacity: 0, top: -6 }}
          animate={{ opacity: visuallyOpen ? 1 : 0, top: visuallyOpen ? 0 : -6 }}
          transition={{ duration: visuallyOpen ? 0.18 : 0.14, ease: motionEase }}
          style={{
            width: "100%",
            position: "relative",
            paddingTop: 4,
            paddingBottom: 4,
            borderRadius: metrics.rowRadius,
            borderWidth: 1,
            borderColor: colors.line,
            backgroundColor: colors.panel,
            boxShadow: {
              offsetX: 0,
              offsetY: 4,
              blurRadius: 12,
              spreadRadius: 0,
              color: "#00000066",
            },
          }}
        >
          {options.map((option, index) => (
            <SelectItem
              key={option.value}
              value={option.value}
              testId={`context-option:${label}:${index}`}
              style={({ selected, highlighted, disabled: itemDisabled }) => ({
                height: 26,
                paddingLeft: 9,
                paddingRight: 9,
                display: "flex",
                alignItems: "center",
                color: selected ? colors.text : colors.secondary,
                opacity: itemDisabled ? 0.48 : 1,
                backgroundColor: highlighted ? colors.controlHover : "transparent",
                cursor: itemDisabled ? "default" : "pointer",
                hover: itemDisabled ? undefined : { backgroundColor: colors.controlHover },
              })}
            >
              <PrimaryText>{option.label}</PrimaryText>
            </SelectItem>
          ))}
        </motion.div>
      </SelectContent>
    </Select>
  )
}

function IconAction({
  icon,
  label,
  testId,
  disabled = false,
  onClick,
}: {
  icon: IconName
  label: string
  testId?: string
  disabled?: boolean
  onClick: () => void
}) {
  const [pressed, setPressed] = useState(false)

  return (
    <Tooltip>
      <TooltipTrigger asChild>
        <div
          testId={testId ?? `action:${icon}`}
          role="button"
          aria-label={label}
          aria-disabled={disabled}
          tabIndex={disabled ? -1 : 0}
          onClick={disabled ? undefined : onClick}
          onKeyDown={event => {
            if (!disabled && (event.key === "enter" || event.key === "space")) onClick()
          }}
          onMouseDown={disabled ? undefined : () => setPressed(true)}
          onMouseUp={disabled ? undefined : () => setPressed(false)}
          onMouseLeave={() => setPressed(false)}
          style={{
            width: 28,
            height: 28,
            flexShrink: 0,
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            borderRadius: metrics.rowRadius,
            opacity: disabled ? 0.48 : 1,
            cursor: disabled ? "default" : "pointer",
            hover: disabled ? undefined : { backgroundColor: colors.controlHover },
            active: disabled ? undefined : { backgroundColor: colors.controlActive },
          }}
        >
          {/* GPUiX 0.6 has no transform tween, so scale only this fixed-size icon box. */}
          <motion.div
            initial={false}
            animate={{
              width: pressed ? 12.75 : 15,
              height: pressed ? 12.75 : 15,
              opacity: pressed ? 0.7 : 1,
            }}
            transition={{ duration: pressed ? 0.08 : 0.18, ease: motionEase }}
            style={{ display: "flex", alignItems: "center", justifyContent: "center", pointerEvents: "none" }}
          >
            <Icon name={icon} size="100%" />
          </motion.div>
        </div>
      </TooltipTrigger>
      <TooltipContent
        side="bottom"
        sideOffset={6}
        style={{
          paddingTop: 5,
          paddingRight: 8,
          paddingBottom: 5,
          paddingLeft: 8,
          borderRadius: 5,
          borderWidth: 1,
          borderColor: colors.line,
          backgroundColor: colors.control,
          boxShadow: {
            offsetX: 0,
            offsetY: 4,
            blurRadius: 12,
            spreadRadius: 0,
            color: "#00000066",
          },
        }}
      >
        <SecondaryText>{label}</SecondaryText>
      </TooltipContent>
    </Tooltip>
  )
}

function ConnectPhotoshopAction({ onClick, busy = false }: { onClick: () => void; busy?: boolean }) {
  const [pressed, setPressed] = useState(false)
  return (
    <div
      testId="connect-photoshop"
      role="button"
      aria-label="Connect Photoshop"
      aria-disabled={busy}
      tabIndex={busy ? -1 : 0}
      onClick={busy ? undefined : onClick}
      onKeyDown={event => {
        if (!busy && (event.key === "enter" || event.key === "space")) onClick()
      }}
      onMouseDown={busy ? undefined : () => setPressed(true)}
      onMouseUp={() => setPressed(false)}
      onMouseLeave={() => setPressed(false)}
      style={{
        height: 32,
        paddingLeft: 12,
        paddingRight: 12,
        display: "flex",
        flexDirection: "row",
        alignItems: "center",
        justifyContent: "center",
        gap: 7,
        borderRadius: metrics.rowRadius,
        backgroundColor: pressed ? colors.controlActive : colors.control,
        cursor: busy ? "default" : "pointer",
        opacity: busy ? 0.6 : 1,
        hover: busy ? undefined : { backgroundColor: colors.controlHover },
      }}
    >
      <Icon name="folder" size={14} />
      <PrimaryText>{busy ? "Connecting..." : "Connect Photoshop"}</PrimaryText>
    </div>
  )
}

function PopoverText({ children }: { children: React.ReactNode }) {
  return (
    <text
      style={{
        color: colors.secondary,
        fontFamily: typography.family,
        fontSize: typography.secondarySize,
        fontWeight: typography.secondaryWeight,
        whiteSpace: "nowrap",
      }}
    >
      {children}
    </text>
  )
}

function MappingHelpPopover() {
  const [open, setOpen] = useState(false)

  return (
    <div style={{ position: "relative", display: "flex", flexShrink: 0 }}>
      <div
        testId="mapping-help-trigger"
        aria-label="How mapping works"
        onClick={() => setOpen((current) => !current)}
        style={{
          width: 18,
          height: 18,
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          borderRadius: 4,
          opacity: 0.72,
          cursor: "pointer",
          hover: { opacity: 1, backgroundColor: colors.controlHover },
          active: { backgroundColor: colors.controlActive },
        }}
      >
        <text
          style={{
            color: colors.secondary,
            fontFamily: typography.family,
            fontSize: 11,
            fontWeight: 600,
          }}
        >
          ?
        </text>
      </div>
      {open ? (
        <anchored
          testId="mapping-help-popover"
          tabIndex={0}
          onMouseDownOutside={() => setOpen(false)}
          onKeyDown={(event) => {
            if (event.key === "escape") setOpen(false)
          }}
          side="bottom"
          align="end"
          gap={6}
          fit="snap"
          snapMargin={8}
          deferred
          priority={2}
          occlude
        >
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ duration: 0.14, ease: motionEase }}
            style={{
              width: 240,
              display: "flex",
              flexDirection: "column",
              gap: 7,
              padding: 12,
              borderRadius: 6,
              borderWidth: 1,
              borderColor: colors.line,
              backgroundColor: colors.control,
              boxShadow: {
                offsetX: 0,
                offsetY: 6,
                blurRadius: 18,
                spreadRadius: 0,
                color: "#00000073",
              },
            }}
          >
            <PrimaryText>Map between hosts</PrimaryText>
            <PopoverText>Drag a native layer onto the other host.</PopoverText>
            <PopoverText>Group: place inside</PopoverText>
            <PopoverText>Layer: place after</PopoverText>
            <PopoverText>Apply writes the transfer manifest.</PopoverText>
          </motion.div>
        </anchored>
      ) : null}
    </div>
  )
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
  hoveredGroupId: string | null
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
    host, selectedIds, mappedIds, hoveredId, hoveredGroupId, draggingId,
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
        backgroundColor: hoveredGroupId === node.id ? colors.groupHover : undefined,
      }}
    >
      {activeDrop ? <div
        testId={`drop-indicator:${node.id}`}
        style={{
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
          backgroundColor: selected ? colors.controlActive : hovered ? colors.controlHover : mapped ? colors.mapped : undefined,
          opacity: draggingId === node.id ? 0.65 : 1,
          cursor: "move",
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

function HostPanel({
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
  hoveredGroupId,
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
            hoveredId={hoveredId} hoveredGroupId={hoveredGroupId}
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

export function BridgeApp({
  session: initialSession,
  onApply,
  onConnectPhotoshop,
  onApplied,
}: {
  session: BridgeSession
  onApply: (state: BridgeState, painterContextId: string, session: BridgeSession) => Promise<string>
  onConnectPhotoshop: (session: BridgeSession) => Promise<BridgeSession | null>
  onApplied?: (output: string) => void
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
  const press = useRef<{ id: string; x: number; y: number } | null>(null)
  const [hoveredId, setHoveredId] = useState<string | null>(null)
  const [selectedIds, setSelectedIds] = useState<Set<string>>(() => new Set())
  const selectionAnchor = useRef<string | null>(null)
  const [dropTargetId, setDropTargetId] = useState<string | null>(null)
  const [expanded, setExpanded] = useState(() => collectExpandedIds(session.state))
  const [status, setStatus] = useState(session.status)
  const [busy, setBusy] = useState(false)
  const [failed, setFailed] = useState(false)
  const pending = useRef(false)

  const hasChanges = history.length > 0
  const canRedo = redoStack.length > 0
  const mappedIds = useMemo(
    () => new Set(bridge.mappings.map((mapping) => mapping.sourceId)),
    [bridge.mappings],
  )
  const hoveredGroupId = nearestGroup(bridge.photoshop, hoveredId) ?? nearestGroup(bridge.painter, hoveredId)
  const draggingHost = useMemo(() => {
    if (!draggingId) return null
    const node = findNode(bridge.photoshop, draggingId) ?? findNode(bridge.painter, draggingId)
    return node?.ref.host ?? null
  }, [bridge, draggingId])
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

  const mutate = (next: BridgeState, message: string) => {
    if (pending.current) return
    if (next === bridge) return
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
    mutate(next, "Layer removed from this mapping session")
  }

  const endDrag = () => {
    press.current = null
    setDraggingId(null)
    setDropTargetId(null)
  }

  const startDrag = (id: string, event: EventPayload) => {
    if (pending.current) return
    // Native row presses do not bubble focus like DOM clicks; keep editing
    // shortcuts with the staging area without stealing focus from open menus.
    if (rootRef.current) renderer.focusElement?.(rootRef.current.id)
    const nodes = findNode(bridge.photoshop, id) ? bridge.photoshop : bridge.painter
    const source = findNode(nodes, id)
    if (!source) return
    const modifiers = { toggle: event.modifiers?.ctrl || event.modifiers?.cmd, range: event.modifiers?.shift }
    const visible = visibleSourceIds(nodes, source.ref.host, expanded)
    const next = selectLayerIds(selectedIds, selectionAnchor.current, id, visible, modifiers)
    setSelectedIds(next)
    if (!modifiers.range) selectionAnchor.current = id
    press.current = next.has(id) ? { id, x: event.x ?? 0, y: event.y ?? 0 } : null
    setDraggingId(null)
    setDropTargetId(null)
  }

  const movePointer = (event: EventPayload, rowId?: string) => {
    if (event.pressedButton !== 0 || pending.current) { endDrag(); return }
    const start = press.current
    if (!start) return
    // A press is selection, not a drag. Native child controls can consume mouse-up,
    // so released-button movement also clears the gesture instead of leaving a ghost drop.
    if (Math.hypot((event.x ?? start.x) - start.x, (event.y ?? start.y) - start.y) < metrics.dragThreshold) return
    const source = findNode(bridge.photoshop, start.id) ?? findNode(bridge.painter, start.id)
    const target = rowId ? findNode(bridge.photoshop, rowId) ?? findNode(bridge.painter, rowId) : null
    setDraggingId(start.id)
    const targetHost = rowId && findNode(bridge.photoshop, rowId) ? "photoshop" : "substance_painter"
    setDropTargetId(target && target.ref.host === targetHost && source?.ref.host !== targetHost ? rowId! : null)
  }

  const drop = (targetId: string) => {
    if (!draggingId) return
    const next = transferSelection(bridge, selectedIds, targetId)
    if (next === bridge) {
      setStatus("This target has pending transfers")
      setFailed(true)
    }
    mutate(next, "Mapping updated")
    endDrag()
  }

  const undo = () => {
    if (pending.current) return
    const previous = history.at(-1)
    if (!previous) return
    setRedoStack((current) => [...current, cloneState(bridge)])
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
    setHistory((current) => [...current, cloneState(bridge)])
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
    setDraggingId(null)
    setDropTargetId(null)
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
    setBridge(next)
    setSelectedIds(new Set())
    setHistory([])
    setRedoStack([])
    setDraggingId(null)
    setDropTargetId(null)
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
    pending.current = true
    setBusy(true)
    setFailed(false)
    setStatus("Writing transfer manifest...")
    try {
      const output = await onApply(bridge, activePainterContextId, session)
      setHistory([])
      setRedoStack([])
      const filename = output.split(/[\\/]/).pop() || output
      setStatus(`Transfer manifest written · ${filename}`)
      onApplied?.(output)
    } catch (error) {
      setFailed(true)
      setStatus(error instanceof Error ? error.message : String(error))
    } finally {
      pending.current = false
      setBusy(false)
    }
  }

  const connectPhotoshop = async () => {
    if (pending.current) return
    if (bridge.mappings.length > 0) {
      setStatus("Apply or reset pending transfers before changing documents.")
      setFailed(true)
      return
    }
    pending.current = true
    setBusy(true)
    setFailed(false)
    setStatus("Choose a Photoshop document in Painter...")
    console.info("[PT Bridge] connect_clicked")
    try {
      const next = await onConnectPhotoshop(session)
      if (!next) {
        setStatus("Photoshop connection cancelled")
        return
      }
      // Reconnecting replaces only the Photoshop side. Mappings are already
      // empty here, so the Painter target the user chose stays selected.
      const context = next.painterContexts.find((candidate) => candidate.id === activePainterContextId)
        ?? next.painterContexts.find((candidate) => candidate.id === next.initialPainterContextId)
        ?? null
      const state = bridgeStateForContext(next, context)
      setSession(next)
      if (context) setActivePainterContextId(context.id)
      setBridge(state)
      setSelectedIds(new Set())
      setHistory([])
      setRedoStack([])
      setExpanded(collectExpandedIds(state))
      setStatus(next.status)
    } catch (error) {
      console.error("[PT Bridge] connect_failed", error)
      setFailed(true)
      setStatus(error instanceof Error ? error.message : String(error))
    } finally {
      pending.current = false
      setBusy(false)
    }
  }

  const toggle = (id: string) => {
    setExpanded((current) => {
      const next = new Set(current)
      if (next.has(id)) next.delete(id)
      else next.add(id)
      return next
    })
  }

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
          <IconAction
            icon="check"
            label="Apply mapping"
            disabled={busy || !hasChanges || bridge.mappings.length === 0}
            onClick={apply}
          />
        </div>
        <InsetSeparator />
        <div
          onMouseUp={endDrag}
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
              session.photoshopConnected ? (
                <IconAction
                  icon="folder"
                  label="Change Photoshop document"
                  testId="change-photoshop"
                  disabled={busy}
                  onClick={connectPhotoshop}
                />
              ) : undefined
            }
            emptyContent={
              session.photoshopConnected ? undefined : (
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
            selectedIds={selectedIds} mappedIds={mappedIds}
            hoveredId={hoveredId} hoveredGroupId={hoveredGroupId}
            draggingId={draggingId}
            draggingHost={draggingHost}
            dropTargetId={dropTargetId}
            expanded={expanded}
            onToggle={toggle}
            onDragStart={startDrag}
            onPointerMove={movePointer}
            onDragEnd={endDrag}
            onHover={setHoveredId}
            onDrop={drop}
            onRemove={(id) => removeSource("photoshop", id)}
          />
          {/* Mapping help explains both panes, while the toolbar remains reserved for real commands. */}
          <HostPanel
            panelId="painter"
            title="SUBSTANCE PAINTER"
            subtitle={activePainterContext?.subtitle || "No snapshot loaded"}
            nodes={bridge.painter}
            host="substance_painter"
            headerAction={<MappingHelpPopover />}
            selectedIds={selectedIds} mappedIds={mappedIds}
            hoveredId={hoveredId} hoveredGroupId={hoveredGroupId}
            draggingId={draggingId}
            draggingHost={draggingHost}
            dropTargetId={dropTargetId}
            expanded={expanded}
            onToggle={toggle}
            onDragStart={startDrag}
            onPointerMove={movePointer}
            onDragEnd={endDrag}
            onHover={setHoveredId}
            onDrop={drop}
            onRemove={(id) => removeSource("substance_painter", id)}
          />
        </div>
        {status !== session.status || !activePainterContext || selectedIds.size > 0 ? (
          <div testId="bridge-status" role="status" style={{ flexShrink: 0, padding: 12, paddingTop: 0 }}>
            <text style={{
              color: failed ? colors.danger : colors.secondary,
              fontSize: typography.secondarySize,
              fontFamily: typography.family,
              whiteSpace: "normal",
            }}>{failed || busy ? status : [
              selectedIds.size ? `${selectedIds.size} selected` : "",
              bridge.mappings.length ? `${bridge.mappings.length} pending transfer${bridge.mappings.length === 1 ? "" : "s"}` : "",
            ].filter(Boolean).join(" · ") || status}</text>
          </div>
        ) : null}
        </motion.div>
      </div>
    </TooltipProvider>
  )
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

function nearestGroup(nodes: LayerNode[], id: string | null, parent: string | null = null): string | null {
  if (!id) return null
  for (const node of nodes) {
    if (node.id === id) return node.kind === "group" ? node.id : parent
    const nested = node.children ? nearestGroup(node.children, id, node.id) : null
    if (nested) return nested
  }
  return null
}

function visibleNodesHeight(nodes: LayerNode[], expanded: Set<string>): number {
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

const isEntryPoint =
  typeof Bun !== "undefined" &&
  Bun.main.replaceAll("\\", "/") === import.meta.path.replaceAll("\\", "/")

if (isEntryPoint) {
  const { registerBundledFonts } = await import("./fonts")
  const { allowPainterForeground } = await import("./foreground")
  registerBundledFonts()
  const painterLink = createPainterLink(process.stdin, (line) => process.stdout.write(line))

  let session: BridgeSession
  try {
    const options = parseSessionOptions(Bun.argv.slice(2))
    session = await loadBridgeSession(options)
  } catch (error) {
    session = failedBridgeSession(error)
  }

  // Painter releases the dock action on process exit, not window disappearance.
  // Keep GPUiX's native last-window-close shutdown (requires 0.9.0 on Windows).
  render(
    <BridgeApp
      session={session}
      onApply={(state, contextId, current) => writeTransferManifest(current, state, contextId)}
      onConnectPhotoshop={(current) => {
        allowPainterForeground()
        return connectPhotoshop(current, painterLink)
      }}
      onApplied={() => {
        // Painter owns the destination mutation, so a successful atomic write
        // is the desktop process's terminal state and its unambiguous handoff.
        setTimeout(() => process.exit(0), 80)
      }}
    />,
    {
      title: "PT Bridge",
      width: metrics.windowWidth,
      height: initialWindowHeight(session.state),
      minWidth: 560,
      minHeight: 420,
      windowBackground: "opaque",
      focus: process.env.GPUIX_BACKGROUND !== "1",
    },
  )
}
