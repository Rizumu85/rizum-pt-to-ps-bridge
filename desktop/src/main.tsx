import { useMemo, useState } from "react"
import { motion, render } from "@gpuix/react"

import iconCheck from "../../icons/checkmark.svg" with { type: "text" }
import iconChevronDown from "../../icons/chevron-down.svg" with { type: "text" }
import iconChevronRight from "../../icons/chevron-right.svg" with { type: "text" }
import iconUndo from "../../icons/undo.svg" with { type: "text" }
import iconX from "../../icons/x.svg" with { type: "text" }

import {
  cloneState,
  removeFromPhotoshop,
  transferToPainter,
  type BridgeState,
  type LayerNode,
} from "./model"
import { colors, metrics, typography } from "./theme"
import {
  failedBridgeSession,
  loadBridgeSession,
  parseSessionOptions,
  writeTransferManifest,
  type BridgeSession,
} from "./transport"

const icons = {
  check: iconCheck,
  chevronDown: iconChevronDown,
  chevronRight: iconChevronRight,
  undo: iconUndo,
  x: iconX,
} as const

type IconName = keyof typeof icons

function Icon({ name, size = 14, color }: { name: IconName; size?: number; color: string }) {
  return <svg source={icons[name]} style={{ width: size, height: size, flexShrink: 0, color }} />
}

function PrimaryText({ children }: { children: React.ReactNode }) {
  return (
    <text
      style={{
        color: colors.text,
        fontFamily: typography.family,
        fontSize: typography.primarySize,
        fontWeight: typography.primaryWeight,
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
        color: colors.secondary,
        fontFamily: typography.family,
        fontSize: typography.secondarySize,
        fontWeight: typography.secondaryWeight,
      }}
    >
      {children}
    </text>
  )
}

function ActionButton({
  icon,
  label,
  primary = false,
  disabled = false,
  onClick,
}: {
  icon: IconName
  label: string
  primary?: boolean
  disabled?: boolean
  onClick: () => void
}) {
  const base = primary ? colors.accent : colors.panelRaised
  const hover = primary ? colors.accentHover : colors.hover

  return (
    <div
      onClick={disabled ? undefined : onClick}
      style={{
        minWidth: 86,
        height: 34,
        paddingLeft: 14,
        paddingRight: 14,
        borderRadius: metrics.rowRadius,
        display: "flex",
        flexDirection: "row",
        alignItems: "center",
        justifyContent: "center",
        gap: 7,
        backgroundColor: base,
        opacity: disabled ? 0.38 : 1,
        cursor: disabled ? "default" : "pointer",
        hover: disabled ? undefined : { backgroundColor: hover },
        active: disabled ? undefined : { opacity: 0.82 },
      }}
    >
      <Icon name={icon} size={13} color={colors.text} />
      <PrimaryText>{label}</PrimaryText>
    </div>
  )
}

function HostBadge({ label }: { label: string }) {
  return (
    <div
      style={{
        width: 32,
        height: 32,
        flexShrink: 0,
        borderRadius: 6,
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        backgroundColor: colors.panelRaised,
      }}
    >
      <text
        style={{
          color: colors.text,
          fontFamily: typography.family,
          fontSize: 12,
          fontWeight: 600,
        }}
      >
        {label}
      </text>
    </div>
  )
}

function Thumbnail({ masked = false }: { masked?: boolean }) {
  return (
    <div style={{ width: 38, height: 38, flexShrink: 0, position: "relative" }}>
      <div
        style={{
          width: 34,
          height: 34,
          borderRadius: 4,
          borderWidth: 1,
          borderColor: colors.mask,
          backgroundColor: "#66666A",
        }}
      />
      {masked ? (
        <div
          style={{
            position: "absolute",
            right: 0,
            bottom: 0,
            width: 17,
            height: 17,
            borderRadius: 3,
            borderWidth: 1,
            borderColor: colors.borderStrong,
            backgroundColor: colors.mask,
          }}
        />
      ) : null}
    </div>
  )
}

type LayerRowProps = {
  node: LayerNode
  depth: number
  source: boolean
  draggingId: string | null
  dropTargetId: string | null
  expanded: Set<string>
  onToggle: (id: string) => void
  onDragStart: (id: string) => void
  onDragEnd: () => void
  onDropTarget: (id: string | null) => void
  onDrop: (id: string) => void
  onRemove: (id: string) => void
}

function LayerRow({
  node,
  depth,
  source,
  draggingId,
  dropTargetId,
  expanded,
  onToggle,
  onDragStart,
  onDragEnd,
  onDropTarget,
  onDrop,
  onRemove,
}: LayerRowProps) {
  const [hovered, setHovered] = useState(false)
  const open = node.kind === "group" && expanded.has(node.id)
  const activeDrop = !source && draggingId !== null && dropTargetId === node.id

  return (
    <div
      onMouseEnter={() => {
        setHovered(true)
        if (!source && draggingId) onDropTarget(node.id)
      }}
      onMouseLeave={() => {
        setHovered(false)
        if (!source && dropTargetId === node.id) onDropTarget(null)
      }}
      onMouseUp={() => {
        if (!source && draggingId) onDrop(node.id)
        onDragEnd()
      }}
      style={{
        display: "flex",
        flexDirection: "column",
        marginLeft: depth === 0 ? 0 : 26,
        borderRadius: metrics.rowRadius,
        borderWidth: node.kind === "group" && hovered ? 1 : 0,
        borderColor: node.kind === "group" && hovered ? colors.borderStrong : undefined,
        backgroundColor: node.kind === "group" && hovered ? colors.panelRaised : undefined,
      }}
    >
      {activeDrop ? (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ duration: 0.12, ease: "easeOut" }}
          style={{ height: 2, backgroundColor: colors.drop }}
        />
      ) : null}
      <div
        onMouseDown={() => {
          if (source) onDragStart(node.id)
        }}
        style={{
          minHeight: 54,
          paddingLeft: 8,
          paddingRight: 8,
          display: "flex",
          flexDirection: "row",
          alignItems: "center",
          gap: 9,
          borderRadius: metrics.rowRadius,
          opacity: draggingId === node.id ? 0.48 : 1,
          cursor: source ? "pointer" : "default",
          hover: { backgroundColor: colors.hover },
          active: source ? { backgroundColor: colors.active } : undefined,
        }}
      >
        <div
          onClick={() => {
            if (node.kind === "group") onToggle(node.id)
          }}
          style={{
            width: 14,
            height: 28,
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
          }}
        >
          {node.kind === "group" ? (
            <Icon
              name={open ? "chevronDown" : "chevronRight"}
              size={11}
              color={colors.secondary}
            />
          ) : null}
        </div>
        <Thumbnail masked={node.masked} />
        <div style={{ minWidth: 0, flexGrow: 1, display: "flex", flexDirection: "column", gap: 3 }}>
          <PrimaryText>{node.name}</PrimaryText>
          <SecondaryText>{node.detail}</SecondaryText>
        </div>
        {source && hovered ? (
          <div
            onClick={() => onRemove(node.id)}
            style={{
              width: 26,
              height: 26,
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              borderRadius: 5,
              cursor: "pointer",
              hover: { backgroundColor: colors.active },
            }}
          >
            <Icon name="x" size={12} color={colors.secondary} />
          </div>
        ) : null}
      </div>
      {open
        ? node.children?.map((child) => (
            <LayerRow
              key={child.id}
              node={child}
              depth={depth + 1}
              source={source}
              draggingId={draggingId}
              dropTargetId={dropTargetId}
              expanded={expanded}
              onToggle={onToggle}
              onDragStart={onDragStart}
              onDragEnd={onDragEnd}
              onDropTarget={onDropTarget}
              onDrop={onDrop}
              onRemove={onRemove}
            />
          ))
        : null}
    </div>
  )
}

function HostPanel({
  title,
  subtitle,
  badge,
  nodes,
  source,
  draggingId,
  dropTargetId,
  expanded,
  onToggle,
  onDragStart,
  onDragEnd,
  onDropTarget,
  onDrop,
  onRemove,
}: {
  title: string
  subtitle: string
  badge: string
  nodes: LayerNode[]
  source: boolean
  draggingId: string | null
  dropTargetId: string | null
  expanded: Set<string>
  onToggle: (id: string) => void
  onDragStart: (id: string) => void
  onDragEnd: () => void
  onDropTarget: (id: string | null) => void
  onDrop: (id: string) => void
  onRemove: (id: string) => void
}) {
  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      transition={{ duration: 0.2, ease: "easeOut" }}
      style={{
        width: source ? metrics.photoshopWidth : undefined,
        flexGrow: source ? 0 : 1,
        minWidth: 0,
        height: "100%",
        display: "flex",
        flexDirection: "column",
        borderRadius: metrics.cardRadius,
        borderWidth: 1,
        borderColor: colors.border,
        backgroundColor: colors.panel,
        overflow: "hidden",
      }}
    >
      <div
        style={{
          height: 66,
          flexShrink: 0,
          display: "flex",
          flexDirection: "row",
          alignItems: "center",
          gap: 11,
          paddingLeft: 16,
          paddingRight: 16,
          borderBottomWidth: 1,
          borderColor: colors.border,
        }}
      >
        <HostBadge label={badge} />
        <div style={{ display: "flex", flexDirection: "column", gap: 3 }}>
          <PrimaryText>{title}</PrimaryText>
          <SecondaryText>{subtitle}</SecondaryText>
        </div>
      </div>
      <div
        style={{
          flexGrow: 1,
          minHeight: 0,
          overflow: "scroll",
          paddingTop: 10,
          paddingBottom: 10,
          paddingLeft: 10,
          paddingRight: 10,
        }}
      >
        {nodes.map((node) => (
          <LayerRow
            key={node.id}
            node={node}
            depth={0}
            source={source}
            draggingId={draggingId}
            dropTargetId={dropTargetId}
            expanded={expanded}
            onToggle={onToggle}
            onDragStart={onDragStart}
            onDragEnd={onDragEnd}
            onDropTarget={onDropTarget}
            onDrop={onDrop}
            onRemove={onRemove}
          />
        ))}
      </div>
    </motion.div>
  )
}

export function BridgeApp({
  session,
  onApply,
}: {
  session: BridgeSession
  onApply: (state: BridgeState) => Promise<string>
}) {
  const [bridge, setBridge] = useState<BridgeState>(() => cloneState(session.state))
  const [history, setHistory] = useState<BridgeState[]>([])
  const [draggingId, setDraggingId] = useState<string | null>(null)
  const [dropTargetId, setDropTargetId] = useState<string | null>(null)
  const [expanded, setExpanded] = useState(() => collectGroupIds(session.state))
  const [status, setStatus] = useState(session.status)

  const hasChanges = history.length > 0
  const photoshopCount = useMemo(() => bridge.photoshop.length, [bridge.photoshop])

  const mutate = (next: BridgeState, message: string) => {
    if (next === bridge) return
    setHistory((current) => [...current, cloneState(bridge)])
    setBridge(next)
    setStatus(message)
  }

  const removeSource = (id: string) => {
    const next = removeFromPhotoshop(bridge, id)
    mutate(next, "Source row removed")
  }

  const drop = (targetId: string) => {
    if (!draggingId) return
    const next = transferToPainter(bridge, draggingId, targetId)
    mutate(next, "Mapping updated")
    setDraggingId(null)
    setDropTargetId(null)
  }

  const undo = () => {
    const previous = history.at(-1)
    if (!previous) return
    setBridge(previous)
    setHistory((current) => current.slice(0, -1))
    setStatus("Last mapping undone")
  }

  const cancel = () => {
    setBridge(cloneState(session.state))
    setHistory([])
    setDraggingId(null)
    setDropTargetId(null)
    setStatus("Mapping reset")
  }

  const apply = async () => {
    setStatus("Writing transfer manifest...")
    try {
      const output = await onApply(bridge)
      setHistory([])
      const filename = output.split(/[\\/]/).pop() || output
      setStatus(`Transfer manifest written · ${filename}`)
    } catch (error) {
      setStatus(error instanceof Error ? error.message : String(error))
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
    <div
      testId="bridge-root"
      style={{
        width: "100%",
        height: "100%",
        display: "flex",
        flexDirection: "column",
        backgroundColor: colors.canvas,
      }}
    >
      <div
        style={{
          height: metrics.toolbarHeight,
          flexShrink: 0,
          paddingLeft: 18,
          paddingRight: 18,
          display: "flex",
          flexDirection: "row",
          alignItems: "center",
          gap: 9,
          borderBottomWidth: 1,
          borderColor: colors.border,
        }}
      >
        <PrimaryText>PT Bridge</PrimaryText>
        <text
          style={{
            color: colors.tertiary,
            fontFamily: typography.family,
            fontSize: typography.secondarySize,
            fontWeight: typography.secondaryWeight,
            maxWidth: 390,
            whiteSpace: "nowrap",
            textOverflow: "ellipsis",
          }}
        >
          {`${photoshopCount} source rows · ${status}`}
        </text>
        <div style={{ flexGrow: 1 }} />
        <ActionButton icon="x" label="Cancel" disabled={!hasChanges} onClick={cancel} />
        <ActionButton icon="undo" label="Undo" disabled={!hasChanges} onClick={undo} />
        <ActionButton
          icon="check"
          label="Apply"
          primary
          disabled={!hasChanges || bridge.mappings.length === 0}
          onClick={apply}
        />
      </div>
      <div
        onMouseUp={() => {
          setDraggingId(null)
          setDropTargetId(null)
        }}
        style={{
          flexGrow: 1,
          minHeight: 0,
          display: "flex",
          flexDirection: "row",
          gap: 16,
          padding: 18,
        }}
      >
        <HostPanel
          title="Photoshop"
          subtitle={session.photoshopSubtitle}
          badge="P"
          nodes={bridge.photoshop}
          source
          draggingId={draggingId}
          dropTargetId={dropTargetId}
          expanded={expanded}
          onToggle={toggle}
          onDragStart={setDraggingId}
          onDragEnd={() => setDraggingId(null)}
          onDropTarget={setDropTargetId}
          onDrop={drop}
          onRemove={removeSource}
        />
        <HostPanel
          title="Substance Painter"
          subtitle={session.painterSubtitle}
          badge="SP"
          nodes={bridge.painter}
          source={false}
          draggingId={draggingId}
          dropTargetId={dropTargetId}
          expanded={expanded}
          onToggle={toggle}
          onDragStart={setDraggingId}
          onDragEnd={() => setDraggingId(null)}
          onDropTarget={setDropTargetId}
          onDrop={drop}
          onRemove={removeSource}
        />
      </div>
    </div>
  )
}

function collectGroupIds(state: BridgeState): Set<string> {
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

const isEntryPoint = Bun.isStandaloneExecutable || Bun.main === import.meta.path

if (isEntryPoint) {
  let session: BridgeSession
  try {
    const options = parseSessionOptions(Bun.argv.slice(2))
    session = await loadBridgeSession(options)
  } catch (error) {
    session = failedBridgeSession(error)
  }

  render(<BridgeApp session={session} onApply={(state) => writeTransferManifest(session, state)} />, {
    title: "PT Bridge",
    width: metrics.windowWidth,
    height: metrics.windowHeight,
    windowBackground: "opaque",
    focus: process.env.GPUIX_BACKGROUND !== "1",
  })
}
