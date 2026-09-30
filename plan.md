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

## Direction 3: Desktop Mapper

Goal: The native mapper (`desktop/`) lets the user map layers between Painter
and Photoshop and applies them only on an explicit Apply.

- [ ] Host-test the full round trip: Painter to Photoshop, Photoshop to
      Painter, retargeting, undo, reconnecting a PSD, and failure recovery.
- [x] Connect a PSD without opening Photoshop by reading it in the mapper
      (clipping merges into the base, styles are dropped, adjustment and fill
      layers are locked, folders arrive as folders; see `design.md §6.1`).
- [ ] Host-test PSD connect and Apply on production PSDs, including files
      without persistent layer ids and 16-bit documents.

## Direction 4: Painter-Look PSDs

Goal: PSDs from Export and Bridge look like Painter at hand-off while staying
ordinary sRGB documents (`design.md §4`, `analysis.md §6.2-6.3`).

- [x] Probe Painter group isolation: Normal-mode groups with non-Normal
      children, group opacity, and group masks.
- [x] Native compositor and pixel rewrite in `native/`: Painter's linear
      model with premultiplied alpha, the Normal coverage solve, the
      Multiply/Divide rewrite, and conversion to Normal; Python ctypes wrapper.
- [x] Blend map: replace `preserve_all_layers` with the Blend modes setting,
      convert SoftLight/Saturation/Color, map SignedAddition to LinearLight,
      and remove `compensation.py`.
- [x] Export: composite backdrops from the exported assets and rewrite
      color and data channel layers (the normal channel keeps today's export).
- [ ] Export: verify the composite against Painter's channel render and name
      layers that could not be reproduced.
- [ ] Bridge: read-only Photoshop pass that renders the backdrop below each
      insertion point; rewrite inserted layers against it.
- [ ] Settings: Blend modes row beside Size and Render at, with the export
      dialog override.
- [ ] Photoshop to Painter: stop importing Hue and Luminosity as Tint and
      Value.
- [ ] Host-test with the ramp probe and a production project.
