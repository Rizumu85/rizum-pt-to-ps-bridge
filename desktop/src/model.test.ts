import { describe, expect, it } from "vitest"

import {
  cloneState,
  removeFromHost,
  transferBetweenHosts,
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
