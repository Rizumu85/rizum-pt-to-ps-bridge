import { useEffect, useMemo, useRef, useState } from "react"
import {
  motion,
  render,
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
  type MotionEase,
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

const panelRootIds = {
  photoshop: "panel-root:photoshop",
  painter: "panel-root:painter",
} as const

const motionEase: MotionEase = [0.23, 1, 0.32, 1]
const panelTreeChildrenGap = 8
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
  return <svg source={source} style={{ width: size, height: size, flexShrink: 0, color }} />
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
  onValueChange,
}: {
  label: string
  value: string
  options: ContextOption[]
  width: number
  onValueChange: (value: string) => void
}) {
  const [present, setPresent] = useState(false)
  const [visuallyOpen, setVisuallyOpen] = useState(false)
  const closeTimer = useRef<ReturnType<typeof setTimeout> | null>(null)
  const disabled = options.length < 2
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
          backgroundColor: visuallyOpen ? colors.controlHover : colors.control,
          opacity: disabled ? 0.72 : 1,
          cursor: disabled ? "default" : "pointer",
          hover: disabled ? undefined : { backgroundColor: colors.controlHover },
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
        style={{ width, backgroundColor: "transparent", pointerEvents: visuallyOpen ? "auto" : "none" }}
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
          testId={testId}
          onClick={disabled ? undefined : onClick}
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
            style={{ display: "flex", alignItems: "center", justifyContent: "center" }}
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
            <PrimaryText>Map Photoshop layers</PrimaryText>
            <PopoverText>Drag a source layer onto a Painter target.</PopoverText>
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
    <div style={{ width: 25, height: 22, flexShrink: 0, position: "relative" }}>
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
          }}
        >
          {node.thumbnailPath ? (
            <img
              src={node.thumbnailPath}
              alt=""
              objectFit="cover"
              style={{ width: 18, height: 18 }}
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
          }}
        >
          <svg source={maskThumbnailSource} style={{ width: 8, height: 8 }} />
        </div>
      ) : null}
    </div>
  )
}

type LayerRowProps = {
  node: LayerNode
  source: boolean
  mappedIds: Set<string>
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
  source,
  mappedIds,
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
  const mapped = mappedIds.has(node.id)
  const children = node.children ?? []

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
        position: "relative",
        display: "flex",
        flexDirection: "column",
        marginLeft: 24,
        padding: node.kind === "group" ? 4 : 0,
        borderRadius: 8,
        backgroundColor: node.kind === "group" && hovered ? colors.groupHover : undefined,
      }}
    >
      {activeDrop ? (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ duration: 0.12, ease: motionEase }}
          style={{
            position: "absolute",
            top: 0,
            right: 5,
            left: 5,
            height: 2,
            backgroundColor: colors.drop,
          }}
        />
      ) : null}
      <div
        onMouseDown={() => {
          if (source) onDragStart(node.id)
        }}
        style={{
          height: metrics.rowHeight,
          paddingLeft: 8,
          paddingRight: 8,
          display: "flex",
          flexDirection: "row",
          alignItems: "center",
          gap: 9,
          borderRadius: metrics.rowRadius,
          // Mapping uses a quiet row wash; the former white leading stripe read as stray decoration.
          backgroundColor: mapped ? colors.mapped : undefined,
          opacity: draggingId === node.id ? 0.48 : 1,
          cursor: source ? "move" : "default",
          hover: node.kind === "group" ? undefined : { backgroundColor: colors.controlHover },
          active: source ? { backgroundColor: colors.controlActive } : undefined,
        }}
      >
        <div
          onClick={() => {
            if (node.kind === "group") onToggle(node.id)
          }}
          style={{
            width: 14,
            height: 28,
            flexShrink: 0,
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            cursor: node.kind === "group" ? "pointer" : "default",
          }}
        >
          {node.kind === "group" ? (
            <DisclosureIcon open={open} />
          ) : null}
        </div>
        <LayerThumbnail node={node} />
        <div style={{ minWidth: 0, flexGrow: 1 }}>
          <PrimaryText>{node.name}</PrimaryText>
        </div>
        {source && hovered ? (
          <div
            onClick={() => onRemove(node.id)}
            style={{
              width: 22,
              height: 22,
              flexShrink: 0,
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              borderRadius: 5,
              cursor: "pointer",
              hover: { backgroundColor: "#FF453A29" },
            }}
          >
            <Icon name="x" size={12} color={colors.danger} />
          </div>
        ) : null}
      </div>
      {/* Mounted descendants let interrupted toggles retarget the same accordion transition. */}
      {node.kind === "group" ? (
        <motion.div
          initial={false}
          animate={{
            height: open ? visibleNodesHeight(children, expanded) : 0,
            opacity: open ? 1 : 0,
          }}
          transition={{ duration: 0.3, ease: motionEase }}
          style={{
            display: "flex",
            flexDirection: "column",
            overflow: "hidden",
            pointerEvents: open ? "auto" : "none",
          }}
        >
          {children.map((child) => (
            <LayerRow
              key={child.id}
              node={child}
              source={source}
              mappedIds={mappedIds}
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
        </motion.div>
      ) : null}
    </div>
  )
}

function PanelTree({
  panelId,
  label,
  nodes,
  source,
  footerHint,
  mappedIds,
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
  panelId: keyof typeof panelRootIds
  label: string
  nodes: LayerNode[]
  source: boolean
  footerHint?: string
  mappedIds: Set<string>
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
  const [hovered, setHovered] = useState(false)
  const rootId = panelRootIds[panelId]
  const open = expanded.has(rootId)

  return (
    <div
      onMouseEnter={() => setHovered(true)}
      onMouseLeave={() => setHovered(false)}
      style={{
        display: "flex",
        flexDirection: "column",
        padding: 4,
        borderRadius: 8,
        backgroundColor: hovered ? colors.groupHover : undefined,
      }}
    >
      <div
        testId={`panel-tree-toggle:${panelId}`}
        onClick={() => onToggle(rootId)}
        style={{
          height: metrics.rowHeight,
          paddingLeft: 8,
          paddingRight: 8,
          display: "flex",
          flexDirection: "row",
          alignItems: "center",
          gap: 9,
          borderRadius: metrics.rowRadius,
          cursor: "pointer",
        }}
      >
        <div
          style={{
            width: 14,
            height: 28,
            flexShrink: 0,
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
          }}
        >
          <DisclosureIcon open={open} />
        </div>
        <Icon name="folder" size={14} />
        <div style={{ minWidth: 0, flexGrow: 1, display: "flex", flexDirection: "column", gap: 2 }}>
          <PrimaryText>{label}</PrimaryText>
          <SecondaryText>{`${countNodes(nodes)} Layers`}</SecondaryText>
        </div>
      </div>
      <motion.div
        initial={false}
        animate={{
          height: open
            ? panelTreeChildrenGap + visibleNodesHeight(nodes, expanded) + (footerHint ? 24 : 0)
            : 0,
          opacity: open ? 1 : 0,
        }}
        transition={{ duration: 0.3, ease: motionEase }}
        style={{
          display: "flex",
          flexDirection: "column",
          overflow: "hidden",
          pointerEvents: open ? "auto" : "none",
        }}
      >
        {/* The root identity needs group spacing before its child collection; rows inside stay compact. */}
        <div style={{ height: panelTreeChildrenGap, flexShrink: 0 }} />
        {nodes.map((node) => (
          <LayerRow
            key={node.id}
            node={node}
            source={source}
            mappedIds={mappedIds}
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
        {footerHint ? (
          <div
            style={{
              height: 24,
              marginLeft: 38,
              display: "flex",
              alignItems: "center",
              minWidth: 0,
            }}
          >
            <SecondaryText>{footerHint}</SecondaryText>
          </div>
        ) : null}
      </motion.div>
    </div>
  )
}

function HostPanel({
  panelId,
  title,
  subtitle,
  treeLabel,
  nodes,
  source,
  headerAction,
  footerHint,
  mappedIds,
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
  panelId: keyof typeof panelRootIds
  title: string
  subtitle: string
  treeLabel: string
  nodes: LayerNode[]
  source: boolean
  headerAction?: React.ReactNode
  footerHint?: string
  mappedIds: Set<string>
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
      <div
        style={{
          flexGrow: 1,
          minHeight: 0,
          overflow: "scroll",
          padding: 8,
        }}
      >
        <PanelTree
          panelId={panelId}
          label={treeLabel}
          nodes={nodes}
          source={source}
          footerHint={footerHint}
          mappedIds={mappedIds}
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
      </div>
    </div>
  )
}

export function BridgeApp({
  session,
  onApply,
}: {
  session: BridgeSession
  onApply: (state: BridgeState, painterContextId: string) => Promise<string>
}) {
  const [bridge, setBridge] = useState<BridgeState>(() => cloneState(session.state))
  const [activePainterContextId, setActivePainterContextId] = useState(
    session.initialPainterContextId,
  )
  const [history, setHistory] = useState<BridgeState[]>([])
  // Preview parity only earns toolbar space for commands backed by real state changes.
  const [redoStack, setRedoStack] = useState<BridgeState[]>([])
  const [draggingId, setDraggingId] = useState<string | null>(null)
  const [dropTargetId, setDropTargetId] = useState<string | null>(null)
  const [expanded, setExpanded] = useState(() => collectExpandedIds(session.state))
  const [status, setStatus] = useState(session.status)

  const hasChanges = history.length > 0
  const canRedo = redoStack.length > 0
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

  const mutate = (next: BridgeState, message: string) => {
    if (next === bridge) return
    setHistory((current) => [...current, cloneState(bridge)])
    setRedoStack([])
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
    setRedoStack((current) => [...current, cloneState(bridge)])
    setBridge(previous)
    setHistory((current) => current.slice(0, -1))
    setStatus("Last mapping undone")
  }

  const redo = () => {
    const next = redoStack.at(-1)
    if (!next) return
    setHistory((current) => [...current, cloneState(bridge)])
    setBridge(next)
    setRedoStack((current) => current.slice(0, -1))
    setStatus("Last mapping restored")
  }

  const reset = () => {
    const next = bridgeStateForContext(session, activePainterContext)
    setBridge(next)
    setHistory([])
    setRedoStack([])
    setDraggingId(null)
    setDropTargetId(null)
    setExpanded(collectExpandedIds(next))
    setStatus("Mapping reset")
  }

  const switchPainterContext = (context: PainterContext | undefined) => {
    if (!context || context.id === activePainterContextId) return
    const next = bridgeStateForContext(session, context)
    // Target references belong to one Painter context; carrying mappings across
    // a context switch would silently apply them to a different stack/channel.
    setActivePainterContextId(context.id)
    setBridge(next)
    setHistory([])
    setRedoStack([])
    setDraggingId(null)
    setDropTargetId(null)
    setExpanded(collectExpandedIds(next))
    setStatus(`Target changed · ${context.subtitle}`)
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
    setStatus("Writing transfer manifest...")
    try {
      const output = await onApply(bridge, activePainterContextId)
      setHistory([])
      setRedoStack([])
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
    <TooltipProvider delayDuration={320} skipDelayDuration={250} disableHoverableContent>
      <div
        testId="bridge-root"
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
            onValueChange={changePainterStack}
          />
          <ContextSelect
            label="Channel:"
            value={activePainterContextId}
            options={channelOptions}
            width={152}
            onValueChange={(contextId) =>
              switchPainterContext(
                session.painterContexts.find((context) => context.id === contextId),
              )
            }
          />
          <div style={{ flexGrow: 1 }} />
          <IconAction icon="reset" label="Reset mapping" disabled={!hasChanges} onClick={reset} />
          <div style={{ width: 1, height: 18, flexShrink: 0, backgroundColor: colors.line }} />
          <IconAction icon="undo" label="Undo" disabled={!hasChanges} onClick={undo} />
          <IconAction icon="redo" label="Redo" disabled={!canRedo} onClick={redo} />
          <div style={{ width: 1, height: 18, flexShrink: 0, backgroundColor: colors.line }} />
          <IconAction
            icon="check"
            label="Apply mapping"
            disabled={!hasChanges || bridge.mappings.length === 0}
            onClick={apply}
          />
        </div>
        <InsetSeparator />
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
            gap: metrics.panelGap,
            padding: metrics.contentPadding,
          }}
        >
          <HostPanel
            panelId="photoshop"
            title="SOURCE: PHOTOSHOP"
            subtitle={session.photoshopSubtitle}
            treeLabel="Selected Layers"
            nodes={bridge.photoshop}
            source
            mappedIds={mappedIds}
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
          {/* Mapping help is target context, not an edit-history action, so it stays out of the toolbar. */}
          <HostPanel
            panelId="painter"
            title="TARGET: PAINTER"
            subtitle={activePainterContext?.subtitle || "No snapshot loaded"}
            treeLabel="Painter Stack"
            nodes={bridge.painter}
            source={false}
            headerAction={<MappingHelpPopover />}
            footerHint={status === session.status ? undefined : status}
            mappedIds={mappedIds}
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
        </motion.div>
      </div>
    </TooltipProvider>
  )
}

function collectExpandedIds(state: BridgeState): Set<string> {
  const ids = new Set<string>(Object.values(panelRootIds))
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

function countNodes(nodes: LayerNode[]): number {
  return nodes.reduce((count, node) => count + 1 + countNodes(node.children ?? []), 0)
}

function visibleNodesHeight(nodes: LayerNode[], expanded: Set<string>): number {
  return nodes.reduce((height, node) => {
    const ownHeight = metrics.rowHeight + (node.kind === "group" ? 8 : 0)
    const childHeight =
      node.kind === "group" && expanded.has(node.id)
        ? visibleNodesHeight(node.children ?? [], expanded)
        : 0
    return height + ownHeight + childHeight
  }, 0)
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
  registerBundledFonts()

  let session: BridgeSession
  try {
    const options = parseSessionOptions(Bun.argv.slice(2))
    session = await loadBridgeSession(options)
  } catch (error) {
    session = failedBridgeSession(error)
  }

  render(
    <BridgeApp
      session={session}
      onApply={(state, contextId) => writeTransferManifest(session, state, contextId)}
    />,
    {
      title: "PT Bridge",
      width: metrics.windowWidth,
      height: metrics.windowHeight,
      windowBackground: "opaque",
      focus: process.env.GPUIX_BACKGROUND !== "1",
    },
  )
}
