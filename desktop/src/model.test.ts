import { describe, expect, it } from "vitest"

import {
  cloneState,
  initialBridgeState,
  removeFromPhotoshop,
  transferToPainter,
} from "./model"

describe("transferToPainter", () => {
  it("moves a nested Photoshop layer into a Painter group", () => {
    const original = cloneState(initialBridgeState)
    const next = transferToPainter(original, "ps-color", "sp-working")

    expect(next.photoshop[0].children?.map((node) => node.id)).toEqual(["ps-paint"])
    expect(next.painter[2].children?.at(-1)?.id).toBe("ps-color")
  })

  it("does not mutate the current bridge state", () => {
    const original = cloneState(initialBridgeState)
    transferToPainter(original, "ps-detail", "sp-maskout")

    expect(original).toEqual(initialBridgeState)
  })

  it("removes a source row without mapping it into Painter", () => {
    const original = cloneState(initialBridgeState)
    const next = removeFromPhotoshop(original, "ps-cleanup")

    expect(next.photoshop.map((node) => node.id)).not.toContain("ps-cleanup")
    expect(next.painter).toEqual(original.painter)
  })
})
