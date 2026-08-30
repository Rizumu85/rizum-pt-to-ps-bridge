import { describe, expect, it } from "vitest"

import {
  cloneState,
  removeFromPhotoshop,
  transferToPainter,
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

describe("transferToPainter", () => {
  it("moves a nested Photoshop layer into a Painter group and records intent", () => {
    const original = fixture()
    const next = transferToPainter(original, "photoshop:color", "substance_painter:working")

    expect(next.photoshop[0].children?.map((node) => node.id)).toEqual(["photoshop:paint"])
    expect(next.painter[1].children?.at(-1)?.id).toBe("photoshop:color")
    expect(next.mappings[0]).toMatchObject({
      sourceId: "photoshop:color",
      targetId: "substance_painter:working",
      placement: "inside",
    })
  })

  it("records after placement when the target is a layer", () => {
    const next = transferToPainter(fixture(), "photoshop:cleanup", "substance_painter:maskout")

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
    transferToPainter(original, "photoshop:cleanup", "substance_painter:maskout")

    expect(original).toEqual(snapshot)
  })

  it("removes a source row without mapping it into Painter", () => {
    const original = fixture()
    const next = removeFromPhotoshop(original, "photoshop:cleanup")

    expect(next.photoshop.map((node) => node.id)).not.toContain("photoshop:cleanup")
    expect(next.painter).toEqual(original.painter)
    expect(next.mappings).toEqual([])
  })
})
