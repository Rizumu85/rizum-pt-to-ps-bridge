# Rizum PT-to-PS Bridge Plan

Directions first, concrete open steps second. Technical constraints live in
`analysis.md`; user-facing behavior lives in `design.md`. Completed history is
in `docs/archive/plan-history.md`.

## Working Agreement

- Rizum Guidelines are active for this project/thread until the user says otherwise.
- Karpathy Guidelines are active for this project/thread until the user says otherwise.
- The user's project rules in `AGENTS.md` take precedence.

## Direction 1: Painter Export

Goal: Painter writes reliable build bundles, with lossless per-node layer and
mask PNGs, for every chosen stack and channel.

- [ ] Host-test representative projects: non-UDIM, multi-UDIM, grouped layers,
      masks, anchor references, and at least one blend mode that must bake.
- [ ] Decide how to populate `normal_map_format` for already-open projects.
- [ ] Store project workflow metadata in build requests if UDIM export needs to
      distinguish `UVTile` from `TextureSetPerUVTile`.

## Direction 2: Photoshop Automation

Goal: Painter drives Photoshop through ExtendScript with no plugin install:
every export builds PSDs automatically, and the mapper can connect and insert
into PSDs.

- [ ] Host-test PSD fidelity gaps: nested groups, baked unsupported modes,
      color-layer behavior, and normal-channel output.
- [ ] Validate whether an Action Manager descriptor can set document-level
      "Blend RGB Colors Using Gamma 1.0" without host modal errors. Keep it off
      until proven safe.

## Direction 3: Desktop Mapper

Goal: The native mapper (`desktop/`) lets the user map layers between Painter
and Photoshop and applies them only on an explicit Apply.

- [ ] Host-test the full round trip: Painter to Photoshop, Photoshop to
      Painter, retargeting, undo, reconnecting a PSD, and failure recovery.
- [ ] Connect a PSD without opening Photoshop by reading it in the mapper.
      Decided so far: clipped layers merge with their base when transferred
      and the UI says so; Painter has no adjustment layers or layer styles; the
      mapper does not need group composite previews. The handling of layers
      that need Photoshop's renderer is still open.
