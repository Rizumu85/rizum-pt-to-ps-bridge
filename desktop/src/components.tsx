import { useEffect, useLayoutEffect, useRef, useState } from "react"
import {
  AnimatePresence,
  motion,
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  Tooltip,
  TooltipContent,
  TooltipTrigger,
  type MotionEase,
} from "@gpuix/react"
import { colors, metrics, typography } from "./theme"

import iconCheck from "../../icons/checkmark.svg" with { type: "text" }
import iconChevronDown from "../../icons/chevron-down.svg" with { type: "text" }
import iconChevronRight from "../../icons/chevron-right.svg" with { type: "text" }
import iconChevronUp from "../../icons/chevron-up.svg" with { type: "text" }
import iconFolder from "../../icons/folder.svg" with { type: "text" }
import iconRedo from "../../icons/redo.svg" with { type: "text" }
import iconRefresh from "../../icons/refresh.svg" with { type: "text" }
import iconReset from "../../icons/reset.svg" with { type: "text" }
import iconUndo from "../../icons/undo.svg" with { type: "text" }
import iconX from "../../icons/x.svg" with { type: "text" }

// Painter layers carry no rendered thumbnail in the snapshot; a type glyph
// reads better than an empty tile that looks like a failed load.
const iconPaintLayer = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 16 16" fill="none"><path d="M12.5 3.5 7.6 8.4" stroke="#9E9E9E" stroke-width="1.5" stroke-linecap="round"/><path d="M6.6 9.4c-1.9 0-2.9 1.3-3 3.1 1.8 0 3.1-1 3.1-2.9Z" fill="#9E9E9E"/></svg>`
const iconFillLayer = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 16 16" fill="none"><rect x="3.25" y="3.25" width="9.5" height="9.5" rx="2" stroke="#9E9E9E" stroke-width="1.5"/><path d="M3.5 12.5 12.5 3.5v7a2 2 0 0 1-2 2Z" fill="#9E9E9E"/></svg>`

const icons = {
  check: iconCheck,
  chevronDown: iconChevronDown,
  chevronRight: iconChevronRight,
  chevronUp: iconChevronUp,
  folder: iconFolder,
  redo: iconRedo,
  refresh: iconRefresh,
  reset: iconReset,
  undo: iconUndo,
  x: iconX,
  paintLayer: iconPaintLayer,
  fillLayer: iconFillLayer,
} as const

export const motionEase: MotionEase = [0.23, 1, 0.32, 1]
export const maskThumbnailSource = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 8 8"><rect width="8" height="8" fill="${colors.maskDark}"/><path d="M0 8 8 0v8Z" fill="${colors.maskLight}"/></svg>`

type IconName = keyof typeof icons
export type ContextOption = { value: string; label: string }

export function Icon({
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

export function DisclosureIcon({ open }: { open: boolean }) {
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

export function PrimaryText({ children }: { children: React.ReactNode }) {
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

export function SecondaryText({ children }: { children: React.ReactNode }) {
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

export function InsetSeparator() {
  return (
    <div style={{ height: 1, flexShrink: 0, paddingLeft: 12, paddingRight: 12 }}>
      <div style={{ width: "100%", height: 1, backgroundColor: colors.line }} />
    </div>
  )
}

export function ContextSelect({
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
    // SelectContent renders nothing once its Select is closed, so
    // AnimatePresence cannot hold it through the fade; the Select stays open
    // until the exit has played instead.
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

export function IconAction({
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
          {/* GPUiX has no transform tween, so scale only this fixed-size icon box. */}
          <motion.div
            initial={false}
            animate={{
              width: pressed ? 13.5 : 15,
              height: pressed ? 13.5 : 15,
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

/**
 * Apply is the one commit in the mapper, so it is a labelled primary button
 * with the pending count instead of another toolbar glyph.
 */
export function ApplyAction({ count, disabled, onClick }: { count: number; disabled: boolean; onClick: () => void }) {
  return (
    <div
      testId="apply-mapping"
      role="button"
      aria-disabled={disabled}
      tabIndex={disabled ? -1 : 0}
      onClick={disabled ? undefined : onClick}
      onKeyDown={event => {
        if (!disabled && (event.key === "enter" || event.key === "space")) onClick()
      }}
      style={{
        position: "relative",
        height: 28,
        paddingLeft: 14,
        paddingRight: 14,
        flexShrink: 0,
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        borderRadius: metrics.rowRadius,
        backgroundColor: disabled ? colors.control : colors.text,
        cursor: disabled ? "default" : "pointer",
        hover: disabled ? undefined : { backgroundColor: colors.textHover },
        active: disabled ? undefined : { backgroundColor: colors.textPressed },
      }}
    >
      {/* When work becomes pending, the dark face fades off the lit button
          instead of the brightest surface in the window flashing on. Losing
          the lit state is the system answering Apply or Undo, so that side is
          instant. The face has no hitbox: it must not take the button's click. */}
      <motion.div
        initial={false}
        animate={{ opacity: disabled ? 1 : 0 }}
        transition={{ duration: disabled ? 0 : 0.2, ease: motionEase }}
        style={{
          position: "absolute",
          top: 0,
          right: 0,
          bottom: 0,
          left: 0,
          borderRadius: metrics.rowRadius,
          backgroundColor: colors.control,
          pointerEvents: "none",
        }}
      />
      <text style={{
        color: disabled ? colors.tertiary : colors.canvas,
        fontFamily: typography.family,
        fontSize: typography.primarySize,
        fontWeight: 600,
        whiteSpace: "nowrap",
      }}>{count > 0 ? `Apply ${count}` : "Apply"}</text>
    </div>
  )
}

export function ConnectPhotoshopAction({ onClick, busy = false }: { onClick: () => void; busy?: boolean }) {
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

export function MappingHelpPopover() {
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
      <AnimatePresence>{open ? (
        <anchored
          key="help"
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
          {/* Enters and leaves the way the context menus do: a short drop from its trigger. */}
          <motion.div
            initial={{ opacity: 0, top: -4 }}
            animate={{ opacity: 1, top: 0 }}
            exit={{ opacity: 0, top: -4 }}
            transition={{ duration: 0.14, ease: motionEase }}
            style={{
              position: "relative",
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
            <PopoverText>Apply transfers them and refreshes both trees.</PopoverText>
          </motion.div>
        </anchored>
      ) : null}</AnimatePresence>
    </div>
  )
}


/**
 * The layer the pointer is carrying. It follows the pointer through its own
 * state so a drag re-renders one chip per move, not both layer trees.
 */
export type PointerFeed = { x: number; y: number; follow: ((x: number, y: number) => void) | null }

export function DragPreview({ label, pointer }: { label: string; pointer: { current: PointerFeed } }) {
  const [position, setPosition] = useState(() => ({ x: pointer.current.x, y: pointer.current.y }))
  useLayoutEffect(() => {
    const follow = (x: number, y: number) => setPosition({ x, y })
    pointer.current.follow = follow
    // A preview still fading out must not detach the next drag's preview.
    return () => { if (pointer.current.follow === follow) pointer.current.follow = null }
  }, [pointer])
  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      transition={{ duration: 0.12, ease: motionEase }}
      style={{
        position: "absolute",
        left: position.x + 14,
        top: position.y + 10,
        maxWidth: 220,
        height: 26,
        paddingLeft: 9,
        paddingRight: 9,
        display: "flex",
        alignItems: "center",
        borderRadius: metrics.rowRadius,
        borderWidth: 1,
        borderColor: colors.line,
        backgroundColor: colors.control,
        boxShadow: { offsetX: 0, offsetY: 4, blurRadius: 12, spreadRadius: 0, color: "#00000066" },
        // The chip rides under the pointer; it must never become the hit target.
        pointerEvents: "none",
      }}
    >
      <div testId="drag-preview" style={{ minWidth: 0 }}><PrimaryText>{label}</PrimaryText></div>
    </motion.div>
  )
}
