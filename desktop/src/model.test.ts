import { describe, expect, it } from "vitest"

import {
  cloneState,
  findNode,
  removeFromHost,
  transferBetweenHosts,
  transferSelection,
  selectLayerIds,
  visibleSourceIds,
  type BridgeState,
  type HostId,
  type LayerNode,
} from "./model"

function layer(host: HostId, id: string, kind: "group" | "layer", children?: LayerNode[]): LayerNode {
  return {
    id: `${host}:${id}`,
    kind,
    name: id,
    detail: kind === "group" ? "Group" : "Normal · 100%",
    ref: { host, externalId: id, kind, path: id },
    children,
  }
}

function fixture(): BridgeState {
  return {
    photoshop: [
      layer("photoshop", "group", "group", [
        layer("photoshop", "paint", "layer"),
        layer("photoshop", "color", "layer"),
      ]),
      layer("photoshop", "cleanup", "layer"),
    ],
    painter: [
      layer("substance_painter", "maskout", "layer"),
      layer("substance_painter", "working", "group", [
        layer("substance_painter", "recolor", "layer"),
      ]),
    ],
    mappings: [],
  }
}

describe("transferBetweenHosts", () => {
  it("retargets pending batches without duplicating transfers or changing their order", () => {
    const ids = new Set(["photoshop:paint", "photoshop:color"])
    const staged = transferSelection(fixture(), ids, "substance_painter:working")
    const next = transferSelection(staged, ids, "substance_painter:maskout")
    expect(next.mappings).toHaveLength(2)
    expect(next.mappings.every(mapping => mapping.targetId === "substance_painter:maskout")).toBe(true)
    expect(next.painter.map(node => node.id)).toEqual([
      "substance_painter:maskout", "photoshop:paint", "photoshop:color", "substance_painter:working",
    ])
    expect(next.painter[3].children?.map(node => node.id)).toEqual(["substance_painter:recolor"])
    expect(visibleSourceIds(staged.painter, "photoshop", new Set(["substance_painter:working"]))).toEqual([...ids])
  })

  it("retargets a Painter group as a folder of its layers and keeps its source reference", () => {
    const working = findNode(fixture().painter, "substance_painter:working")!
    const staged = transferBetweenHosts(fixture(), "substance_painter:working", "photoshop:group")
    const next = transferBetweenHosts(staged, "substance_painter:working", "photoshop:cleanup")
    expect(next.mappings).toHaveLength(1)
    expect(next.mappings[0]).toMatchObject({ targetId: "photoshop:cleanup", source: { kind: "group" } })
    const moved = next.photoshop.at(-1)
    expect(moved?.id).toBe("substance_painter:working")
    expect(moved?.kind).toBe("group")
    expect(moved?.children?.map(node => node.id)).toEqual(working.children?.map(node => node.id))
  })

  it("drops a batch above a layer in selection order and records the placement", () => {
    const first = fixture().painter[0].id
    const next = transferSelection(fixture(), new Set(["photoshop:paint", "photoshop:color"]), first, "before")
    expect(next.painter.map(node => node.id).slice(0, 3)).toEqual(["photoshop:paint", "photoshop:color", first])
    expect(next.mappings.map(mapping => mapping.placement)).toEqual(["before", "before"])
  })

  it("cannot transfer away a destination of another pending transfer", () => {
    const staged = transferBetweenHosts(fixture(), "photoshop:paint", "substance_painter:working")
    expect(transferBetweenHosts(staged, "substance_painter:working", "photoshop:cleanup")).toBe(staged)
  })

  it("keeps a multi-layer drop ordered and records one transfer per selected root", () => {
    const next = transferSelection(fixture(), new Set(["photoshop:paint", "photoshop:color"]), "substance_painter:maskout")
    expect(next.painter.map(node => node.id).slice(0, 3)).toEqual([
      "substance_painter:maskout", "photoshop:paint", "photoshop:color",
    ])
    expect(next.mappings).toHaveLength(2)
  })

  it("previews a Photoshop group as the Painter folder of layers Apply creates", () => {
    const next = transferSelection(fixture(), new Set(["photoshop:group", "photoshop:paint"]), "substance_painter:working")
    expect(next.mappings).toHaveLength(1)
    const pending = next.painter[1].children?.at(-1)
    expect(pending?.kind).toBe("group")
    expect(pending?.children?.map(node => node.id)).toEqual(["photoshop:paint", "photoshop:color"])
  })

  it("never transfers locked Photoshop rows", () => {
    const state = fixture()
    state.photoshop[1].locked = "Adjustment layer · not supported"
    expect(transferBetweenHosts(state, "photoshop:cleanup", "substance_painter:maskout")).toBe(state)
  })

  it("cannot hide a destination that contains pending transfers", () => {
    const mapped = transferBetweenHosts(fixture(), "photoshop:paint", "substance_painter:working")
    expect(removeFromHost(mapped, "substance_painter", "substance_painter:working")).toBe(mapped)
  })

  it("selects ranges, toggles membership, and preserves a selected batch on drag", () => {
    const visible = ["a", "b", "c", "d"]
    const range = selectLayerIds(new Set(["a"]), "a", "c", visible, { range: true })
    expect([...range]).toEqual(["a", "b", "c"])
    expect([...selectLayerIds(range, "a", "b", visible, { toggle: true })]).toEqual(["a", "c"])
    expect(selectLayerIds(range, "a", "b", visible, {})).toEqual(range)
  })

  it("moves a nested Photoshop layer into a Painter group and records intent", () => {
    const original = fixture()
    const next = transferBetweenHosts(original, "photoshop:color", "substance_painter:working")

    expect(next.photoshop[0].children?.map((node) => node.id)).toEqual(["photoshop:paint"])
    expect(next.painter[1].children?.at(-1)?.id).toBe("photoshop:color")
    expect(next.mappings[0]).toMatchObject({
      sourceId: "photoshop:color",
      targetId: "substance_painter:working",
      placement: "inside",
      direction: "photoshop_to_painter",
    })
  })

  it("records after placement when the target is a layer", () => {
    const next = transferBetweenHosts(
      fixture(),
      "photoshop:cleanup",
      "substance_painter:maskout",
    )

    expect(next.mappings[0].placement).toBe("after")
    expect(next.painter.map((node) => node.id)).toEqual([
      "substance_painter:maskout",
      "photoshop:cleanup",
      "substance_painter:working",
    ])
  })

  it("does not mutate the current bridge state", () => {
    const original = fixture()
    const snapshot = cloneState(original)
    transferBetweenHosts(original, "photoshop:cleanup", "substance_painter:maskout")

    expect(original).toEqual(snapshot)
  })

  it("moves a Painter layer into Photoshop and records the reverse direction", () => {
    const next = transferBetweenHosts(
      fixture(),
      "substance_painter:recolor",
      "photoshop:group",
    )

    expect(next.painter[1].children).toEqual([])
    expect(next.photoshop[0].children?.at(-1)?.id).toBe("substance_painter:recolor")
    expect(next.mappings[0]).toMatchObject({
      direction: "painter_to_photoshop",
      sourceId: "substance_painter:recolor",
      targetId: "photoshop:group",
      placement: "inside",
    })
  })

  it("removes a native row from either host without creating a mapping", () => {
    const original = fixture()
    const withoutPhotoshop = removeFromHost(original, "photoshop", "photoshop:cleanup")
    const withoutPainter = removeFromHost(
      withoutPhotoshop,
      "substance_painter",
      "substance_painter:maskout",
    )

    expect(withoutPainter.photoshop.map((node) => node.id)).not.toContain("photoshop:cleanup")
    expect(withoutPainter.painter.map((node) => node.id)).not.toContain(
      "substance_painter:maskout",
    )
    expect(withoutPainter.mappings).toEqual([])
  })
})
