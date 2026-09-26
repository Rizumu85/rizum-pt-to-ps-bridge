import { useEffect, useLayoutEffect, useRef, useState, type ComponentProps, type ForwardRefExoticComponent } from "react"
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
  useGpuixRequired,
  useIsPresent,
  type MotionEase,
  type PublicInstance,
} from "@gpuix/react"
import { colors, metrics, typography } from "./theme"
import { createPointerFollower } from "./drag-feedback"

import iconCheck from "../../icons/checkmark.svg" with { type: "text" }
import iconChevronDown from "../../icons/chevron-down.svg" with { type: "text" }
import iconChevronRight from "../../icons/chevron-right.svg" with { type: "text" }
import iconChevronUp from "../../icons/chevron-up.svg" with { type: "text" }
import iconFolder from "../../icons/folder.svg" with { type: "text" }
import iconRedo from "../../icons/redo.svg" with { type: "text" }
import iconRefresh from "../../icons/refresh.svg" with { type: "text" }
import iconEraser from "../../icons/eraser.svg" with { type: "text" }
import iconHelp from "../../icons/help.svg" with { type: "text" }
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
  // Reset mapping clears pending work; a circular arrow read as Reload PSD.
  eraser: iconEraser,
  help: iconHelp,
  undo: iconUndo,
  x: iconX,
  paintLayer: iconPaintLayer,
  fillLayer: iconFillLayer,
} as const

export const motionEase: MotionEase = [0.23, 1, 0.32, 1]

/**
 * motion.div forwards every host prop, but GPUiX 0.10's types drop testId and
 * role. Keep them on the animated element itself: an extra div only to carry
 * them doubled the layer tree's depth, and nested flex layout grows costly
 * with depth fast enough to cut the frame rate by more than half.
 */
export const Motion = motion.div as ForwardRefExoticComponent<
  ComponentProps<typeof motion.div> & { testId?: string; role?: string }
>
// Something travelling back to where it belongs decelerates into place.
const settleEase: MotionEase = [0.32, 0.72, 0, 1]
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

export function PrimaryText({ children, lineHeight }: { children: React.ReactNode; lineHeight?: number }) {
  return (
    <text
      style={{
        color: colors.text,
        fontFamily: typography.family,
        fontSize: typography.primarySize,
        fontWeight: typography.primaryWeight,
        lineHeight,
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

// Host phases have different units. Show their real counts, never a synthetic
// overall percentage; saving and host waits remain indeterminate.
export function ApplyProgressDialog({ progress }: { progress: import("./transport").ApplyProgress }) {
  const track = useRef<PublicInstance>(null)
  const counted = progress.total !== undefined && progress.total > 0 && progress.completed !== undefined
  const fraction = counted ? Math.max(0, Math.min(1, progress.completed! / progress.total!)) : null
  return (
    <div testId="apply-progress" role="dialog" aria-label="Applying changes"
      style={{ position: "absolute", left: 0, right: 0, top: 0, bottom: 0, backgroundColor: "#00000055",
        display: "flex", alignItems: "center", justifyContent: "center" }}>
      <div style={{ width: 320, padding: 20, borderRadius: 8, backgroundColor: colors.panel,
        display: "flex", flexDirection: "column", gap: 12 }}>
        <PrimaryText>Applying changes</PrimaryText>
        <text style={{ fontFamily: typography.family, fontSize: typography.secondarySize,
          fontWeight: typography.secondaryWeight, color: colors.secondary, whiteSpace: "normal" }}>{progress.message}</text>
        <div ref={track} testId="apply-progress-bar" role="progressbar" aria-label={progress.message}
          aria-valuetext={counted ? `${progress.completed} / ${progress.total}` : "Working"}
          style={{ position: "relative", height: 4, width: "100%", overflow: "hidden", borderRadius: 2, backgroundColor: colors.line }}>
          {fraction === null ? <WorkingSweep key="sweep" track={track} /> : <div
            testId="apply-progress-fill" style={{ height: 4, width: `${fraction * 100}%`, backgroundColor: colors.text }} />}
        </div>
        {counted ? <SecondaryText>{`${progress.completed} / ${progress.total}`}</SecondaryText> : null}
      </div>
    </div>
  )
}

function WorkingSweep({ track }: { track: { current: PublicInstance | null } }) {
  const renderer = useGpuixRequired()
  // GPUiX motion has no repeat, so each pass remounts the light; measuring per
  // pass keeps the sweep spanning the separator after window resizes.
  const [pass, setPass] = useState(0)
  const width = (track.current && renderer.getElementBounds?.(track.current.id)?.width) || 0
  const segment = Math.max(48, width * 0.28)
  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      transition={{ duration: 0.12, ease: motionEase }}
      style={{ position: "absolute", top: 0, right: 0, bottom: 0, left: 0, pointerEvents: "none" }}
    >
      <motion.div
        key={pass}
        initial={{ left: -segment }}
        animate={{ left: width }}
        transition={{ duration: 1.1, ease: "linear" }}
        onMotionComplete={() => setPass(current => current + 1)}
        style={{ position: "absolute", top: 0, width: segment, height: "100%", backgroundColor: colors.text }}
      />
    </motion.div>
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
 * instead of another toolbar glyph. The pending count lives in the status
 * line; in the label it made the button's width jump with every drop.
 */
export function ApplyAction({ disabled, onClick }: { disabled: boolean; onClick: () => void }) {
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
        // MiSans sits low in its line box; this centres the word optically.
        paddingBottom: 3,
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
        fontWeight: typography.primaryWeight,
        whiteSpace: "nowrap",
      }}>Apply</text>
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
        // Sentences wrap inside the popover's fixed width instead of running past it.
        whiteSpace: "normal",
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
      {/* The same icon button as the Photoshop header's actions: a smaller,
          fainter "?" beside them read as a mismatch, not as quieter help. */}
      <IconAction
        icon="help"
        label="How mapping works"
        testId="mapping-help-trigger"
        onClick={() => setOpen((current) => !current)}
      />
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
            <PrimaryText>How mapping works</PrimaryText>
            <PopoverText>Drag layers from one side to the other.</PopoverText>
            <PopoverText>Aim at the top of a row to place them above it, or lower to place them below.</PopoverText>
            <PopoverText>Drop onto a folder to put them inside.</PopoverText>
            <PopoverText>Nothing is copied until you press Apply.</PopoverText>
          </motion.div>
        </anchored>
      ) : null}</AnimatePresence>
    </div>
  )
}


type Bounds = { x: number; y: number; width: number; height: number }

/**
 * Position is an input feed, not React state. Only pickup and release render
 * the card; continuous moves update its native wrapper alone.
 */
export type PointerFeed = {
  x: number
  y: number
  follow: ((x: number, y: number) => void) | null
  flush: (() => void) | null
  /** Where a drag that did not land began; the cards settle back into it. */
  returnTo: Bounds | null
}

const cardWidth = 180
const cardHeight = 30
// The stack hangs off the pointer's lower right, like a system drag image.
const cardGap = { x: 14, y: 10 }

/**
 * Carried layers follow the pointer immediately, leaving the target visible.
 * A cancelled drag settles them back into their row; a landed one fades in
 * place while its rows fade in at the target.
 */
export function DragPreview({ items, pointer }: {
  items: readonly { id: string; name: string; thumbnailPath?: string | null }[]
  pointer: { current: PointerFeed }
}) {
  const renderer = useGpuixRequired()
  // Where the lower right would leave the window, the stack moves to the
  // pointer's lower left and keeps following. Pinning it to the edge instead
  // froze it across most of the right panel, which read as the app hanging.
  // The 40px band stops it flipping back and forth at the boundary. The flip
  // moves the carrier, never the cards' offset, so no move restarts motion.
  const [bounds] = useState(() => renderer.getWindowSize?.() ?? null)
  const flipped = useRef(false)
  const anchor = (x: number, y: number) => {
    if (!bounds) return { x, y }
    const room = bounds.width - 12 - (x + cardGap.x + cardWidth)
    if (room < 0) flipped.current = true
    else if (room > 40) flipped.current = false
    return {
      x: flipped.current ? Math.max(12 - cardGap.x, x - 2 * cardGap.x - cardWidth) : x,
      y: Math.min(y, bounds.height - cardGap.y - cardHeight - 12),
    }
  }
  const position = useRef(anchor(pointer.current.x, pointer.current.y))
  const carrier = useRef<PublicInstance>(null)
  const carrierStyle = (point: { x: number; y: number }) => ({
    position: "absolute", left: point.x, top: point.y, width: 0, height: 0, pointerEvents: "none" as const,
  })
  const writePosition = (point: { x: number; y: number }) => {
    position.current = point
    if (carrier.current) renderer.applyBatch(JSON.stringify([["setStyle", carrier.current.id, carrierStyle(point)]]))
  }
  const present = useIsPresent()
  // GPUiX resends host styles on React commits. Restore the input-owned
  // position after those rare commits, so unrelated updates cannot snap it back.
  useLayoutEffect(() => writePosition(position.current))
  useLayoutEffect(() => {
    // A leaving stack stops following, so the pointer cannot fight its exit.
    if (!present) return
    const follower = createPointerFollower(position.current, writePosition)
    const follow = (x: number, y: number) => {
      const point = anchor(x, y)
      follower.move(point.x, point.y)
    }
    pointer.current.follow = follow
    pointer.current.flush = follower.flush
    follow(pointer.current.x, pointer.current.y)
    follower.flush()
    // A preview still leaving must not detach the next drag's preview.
    return () => {
      follower.dispose()
      if (pointer.current.follow === follow) {
        pointer.current.follow = null
        pointer.current.flush = null
      }
    }
  }, [pointer, present, renderer])
  const home = present ? null : pointer.current.returnTo
  const depth = Math.min(items.length, 3)
  const first = items[0]
  const card = (layer: number) => {
    const offset = layer * 4
    const carried = {
      left: cardGap.x + offset, top: cardGap.y + offset, width: cardWidth, height: cardHeight,
      opacity: [1, 0.7, 0.45][layer],
    }
    const rowAt = (bounds: Bounds, x: number, y: number) => ({
      left: bounds.x - x, top: bounds.y - y, width: bounds.width, height: bounds.height,
    })
    return {
      // Pickup is continuous input, not an entrance to wait for. Only a
      // cancelled drop animates home; the carried card starts at the pointer.
      initial: carried,
      animate: carried,
      exit: home ? { ...rowAt(home, position.current.x, position.current.y), opacity: 0 } : { ...carried, opacity: 0 },
      transition: home || present ? { duration: 0.2, ease: settleEase } : { duration: 0.12, ease: motionEase },
    }
  }
  const cardStyle = {
    position: "absolute" as const,
    borderRadius: metrics.rowRadius,
    borderWidth: 1,
    borderColor: colors.line,
    backgroundColor: colors.control,
    boxShadow: { offsetX: 0, offsetY: 6, blurRadius: 16, spreadRadius: 0, color: "#00000073" },
    pointerEvents: "none" as const,
  }
  return (
    // The stack rides with the pointer; it must never become the hit target.
    <div ref={carrier} testId="drag-carrier" style={carrierStyle(position.current)}>
      {Array.from({ length: depth - 1 }, (_, index) => depth - 1 - index).map(layer => (
        <motion.div key={layer} {...card(layer)} style={cardStyle} />
      ))}
      <Motion
        testId="drag-preview"
        {...card(0)}
        style={{
          ...cardStyle, overflow: "hidden", paddingLeft: 8, paddingRight: 8,
          display: "flex", flexDirection: "row", alignItems: "center", gap: 8,
        }}
      >
        {first.thumbnailPath ? <img
          src={first.thumbnailPath}
          alt=""
          objectFit="cover"
          style={{ width: 16, height: 16, flexShrink: 0, borderRadius: 3, pointerEvents: "none" }}
        /> : null}
        <div style={{ minWidth: 0, flexGrow: 1 }}><PrimaryText>{first.name}</PrimaryText></div>
        {items.length > 1 ? <div style={{
          height: 16, minWidth: 16, paddingLeft: 5, paddingRight: 5, flexShrink: 0, borderRadius: 8,
          display: "flex", alignItems: "center", justifyContent: "center", backgroundColor: colors.text,
        }}>
          <text style={{ color: colors.canvas, fontFamily: typography.family, fontSize: 11, fontWeight: 600 }}>
            {items.length}
          </text>
        </div> : null}
      </Motion>
    </div>
  )
}
