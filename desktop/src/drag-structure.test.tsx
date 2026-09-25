import type { ReactNode } from "react"
import { createRoot, flushSync, type EventPayload, type NativeRenderer, type StyleDesc } from "@gpuix/react"
import { createRendererState, type MutationTuple } from "@gpuix/native/host"
import { describe, expect, it, vi } from "vitest"
import { BridgeApp } from "./bridge-app"
import { LayerScroll } from "./layer-scroll"
import { failedBridgeSession } from "./transport"
import type { BridgeState, HostId, LayerNode } from "./model"

// This host records real reconciler work without opening a GPUI window. It
// verifies state ownership/work counts, not native paint speed or hit testing.
function memoryRoot() {
  const nodes = new Map<number, { id: number; style: StyleDesc; props: Record<string, unknown> }>()
  const mutations: MutationTuple[] = []
  const renderer = {
    applyBatch(json: string) {
      const batch: MutationTuple[] = JSON.parse(json)
      mutations.push(...batch)
      const destroyed: number[] = []
      for (const [op, id, arg, value] of batch) {
        if (typeof id !== "number") continue
        if (op === "createElement") nodes.set(id, { id, style: {}, props: {} })
        if (op === "destroyElement") { nodes.delete(id); destroyed.push(id) }
        const node = nodes.get(id)
        if (node && op === "setStyle") node.style = arg as StyleDesc
        if (node && op === "setCustomProp") node.props[String(arg)] = value
      }
      return destroyed
    },
    getElementBounds: vi.fn((_id: number) => ({ x: 10, y: 100, width: 260, height: 36 })),
    getWindowSize: () => ({ width: 700, height: 560 }),
    getListScrollTop: () => [0, 0, 400],
  } satisfies NativeRenderer
  const root = createRoot(renderer, { onUncaughtError: error => { throw error } })
  const find = (testId: string) => [...nodes.values()].find(node => node.props.testId === testId)!
  const event = (testId: string, eventType: string, values: Partial<EventPayload> = {}) => {
    const node = find(testId)
    expect(node, testId).toBeDefined()
    createRendererState(renderer).dispatch({ elementId: node.id, eventType, ...values })
  }
  return {
    ...root, renderer, mutations, nodes, find, event,
    render(node: ReactNode) { flushSync(() => root.render(node)) },
    frame: () => flushSync(() => {}),
  }
}

function layer(host: HostId, id: string, children?: LayerNode[]): LayerNode {
  return { id, name: id, kind: children ? "group" : "layer", children, detail: "",
    ref: { host, externalId: id, path: id, kind: children ? "group" : "layer" } }
}

function setup() {
  const session = failedBridgeSession("")
  session.state.photoshop = [layer("photoshop", "ps-1"), layer("photoshop", "ps-2")]
  session.state.painter = [layer("substance_painter", "pt-group", Array.from({ length: 1000 }, (_, i) => layer("substance_painter", `pt-${i}`)))]
  session.photoshop = {
    path: "fixture.psd", name: "fixture", width: 1024, height: 1024, bitDepth: 8,
    nodes: session.state.photoshop, layers: new Map(), clipped: new Map(), merged: new Set(), colors: new Map(),
  }
  session.painterContexts = [{ id: "body", textureSet: "body", stack: "", channel: "basecolor", channelLabel: "Base Color", subtitle: "body", nodes: session.state.painter }]
  session.initialPainterContextId = "body"
  const root = memoryRoot()
  const apply = vi.fn(async (_state: BridgeState) => ({ session: null, message: "Applied", failed: false }))
  root.render(<BridgeApp session={session} onApply={apply} onConnectPhotoshop={async () => null} />)
  const press = (id: string, modifiers?: EventPayload["modifiers"]) => root.event(`layer-drag:${id}`, "mouseDown", { button: 0, x: 20, y: 110, modifiers })
  const move = (id: string, y = 120) => root.event(`layer-row:${id}`, "mouseMove", { pressedButton: 0, x: 200, y })
  const release = (id: string, y = 120) => root.event(`layer-row:${id}`, "mouseUp", { button: 0, x: 200, y })
  return { root, apply, press, move, release }
}

describe("drag structure without native windows", () => {
  it("creates only the visible slice and preserves overlapping row instances when scrolling", () => {
    const root = memoryRoot()
    const renderRow = vi.fn((i: number) => <div key={i} testId={`row-${i}`} style={{ height: 36 }} />)
    try {
      root.render(<LayerScroll id="test" rowCount={1000} layoutKey="fixed" renderRow={renderRow} />)
      expect(renderRow.mock.calls.length).toBeLessThan(100)
      expect(root.find("row-999")).toBeUndefined()
      const oldId = root.find("row-20").id
      renderRow.mockClear()
      flushSync(() => root.event("layer-scroll:test", "visibleRange", { startIndex: 20, endIndex: 40 }))
      expect(root.find("row-20").id).toBe(oldId)
      expect(root.find("row-0")).toBeUndefined()
      expect(renderRow.mock.calls.length).toBeLessThan(100)
    } finally { root.unmount() }
  })

  it("skips invalid-target geometry, caches valid targets, and does not rerender the app on pickup", () => {
    const { root, press, move } = setup()
    try {
      flushSync(() => press("ps-1"))
      root.renderer.getElementBounds.mockClear()
      root.mutations.length = 0
      flushSync(() => move("ps-2"))
      expect(root.renderer.getElementBounds).not.toHaveBeenCalled()
      expect(root.mutations.some(([op, id]) => op === "setStyle" && id === root.find("bridge-root").id)).toBe(false)
      expect(root.find("drag-preview")).toBeDefined()
      for (let i = 0; i < 100; i++) move("pt-0", 120 + i % 3)
      expect(root.renderer.getElementBounds).toHaveBeenCalledTimes(1)
    } finally { root.unmount() }
  })

  it.each(["ps-1", "pt-group"])("commits a burst from %s without a React frame, then allows repositioning", async source => {
    const { root, apply, press, move, release } = setup()
    const first = source === "ps-1" ? "pt-group" : "ps-1"
    const second = source === "ps-1" ? "pt-0" : "ps-2"
    try {
      flushSync(() => { press(source); move(first); release(first) })
      flushSync(() => { press(source); move(second); release(second) })
      root.event("apply-mapping", "click")
      await vi.waitFor(() => expect(apply).toHaveBeenCalledOnce())
      expect(apply.mock.calls[0][0].mappings).toMatchObject([{ sourceId: source, targetId: second }])
    } finally { root.unmount() }
  })

  it("uses fresh release geometry even if the final move was cached", async () => {
    const { root, apply, press, move, release } = setup()
    try {
      flushSync(() => {
        press("ps-1"); move("pt-0", 130)
        root.renderer.getElementBounds.mockReturnValue({ x: 10, y: 125, width: 260, height: 36 })
        release("pt-0", 130)
      })
      root.event("apply-mapping", "click")
      await vi.waitFor(() => expect(apply).toHaveBeenCalledOnce())
      expect(apply.mock.calls[0][0].mappings[0].placement).toBe("before")
    } finally { root.unmount() }
  })

  it("carries a multi-selection as one ordered batch", async () => {
    const { root, apply, press, move, release } = setup()
    try {
      flushSync(() => { press("ps-1"); release("ps-1") })
      flushSync(() => { press("ps-2", { ctrl: true, shift: false, alt: false, cmd: false }); release("ps-2") })
      flushSync(() => { press("ps-1"); move("pt-group"); release("pt-group") })
      root.event("apply-mapping", "click")
      await vi.waitFor(() => expect(apply).toHaveBeenCalledOnce())
      expect(apply.mock.calls[0][0].mappings.map(mapping => mapping.sourceId)).toEqual(["ps-1", "ps-2"])
    } finally { root.unmount() }
  })

  it("invalidates cached row bounds when the visible range moves", () => {
    const { root, press, move } = setup()
    try {
      flushSync(() => { press("ps-1"); move("pt-0") })
      root.renderer.getElementBounds.mockClear()
      root.event("layer-scroll:painter", "visibleRange", { startIndex: 1, endIndex: 10 })
      move("pt-0")
      expect(root.renderer.getElementBounds).toHaveBeenCalledOnce()
    } finally { root.unmount() }
  })

  it("moves the card through one native wrapper without reconciling its contents", async () => {
    const { root, press, move } = setup()
    try {
      flushSync(() => press("ps-1"))
      flushSync(() => move("pt-0"))
      const carrier = root.find("drag-carrier").id
      root.mutations.length = 0
      for (let i = 0; i < 100; i++) root.event("layer-panel:painter", "mouseMove", { pressedButton: 0, x: 210 + i, y: 130 })
      await new Promise(resolve => setTimeout(resolve, 20))
      expect(root.mutations).toHaveLength(1)
      expect(root.mutations[0]).toMatchObject(["setStyle", carrier, { left: 309, top: 130 }])
    } finally { root.unmount() }
  })
})
