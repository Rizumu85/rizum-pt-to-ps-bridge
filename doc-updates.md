# Doc Updates: Channel Export Findings

Apply these to `analysis.md`, `design.md`, and `plan.md`.

---

## `analysis.md`

### §2 JS API fallback — append after the existing `alg.mapexport.save` entry

```
- `alg.mapexport.save` MapInfo type has no UDIM/tile parameter. Fields are
  padding, dilation, dithering, resolution, bitDepth, keepAlpha. Per-layer
  PNGs always render at full texture-set resolution covering all UV tiles.
  For UDIM projects that need per-tile per-layer assets, the Python
  solo-export fallback (§4) is the only known path.
- Valid user-channel map names for `alg.mapexport.save([uid, channel])`:
  `user0`–`user7` (lowercase, no space), `user 0`–`user 7` (lowercase with
  space), or the custom user label such as `SCol`. All three are documented
  as valid in the JS API reference.
- `channelIdentifiers(stackPath)` returns resolved user channel identifiers
  (custom labels) when a stackPath is provided. `documentStructure()`
  `.materials[].stacks[].channels` returns engine-resolved lowercase
  identifiers. The old v1.1.8 plugin used these exact strings directly and
  they are the most reliable source.
```

### §4 Gaps & decisions — append

```
- **UDIM per-layer export gap**: `alg.mapexport.save` cannot target a
  single UV tile. Python `export_project_textures` supports `uvTiles`
  filters but exports full composited channel output, not single-layer
  contributions. The Python solo-export fallback (temporary visibility
  isolation via `Node.set_visible()` + `ScopedModification`) closes this
  gap. Host validation is required for performance (thumbnail regeneration
  risk) and correctness (visibility-only mutations inside
  ScopedModification).
- **User channel export**: the current multi-candidate fallback in
  `_export_asset_png` is correct. The preferred channel identifier source
  is `documentStructure().stacks[].channels` (exact engine strings), with
  `channelIdentifiers(stackPath)` as fallback. Derived candidates
  (`user0`, `user 0`, custom label) should only be tried when the primary
  source is unavailable or produces transparent output.
- **Python layerstack visibility API**: `Node.set_visible(bool)` exists on
  every node (`navigation.md:202`). `Node.is_visible()` is the getter.
  `ScopedModification` (`edition.md:173`) groups mutations into a single
  undo entry. No built-in solo or layer-isolation export API exists.
```

### §5 Open questions — add

```
- Host-validate solo-export performance: does hiding many layers trigger
  thumbnail-regeneration stalls similar to the deprecated inbox/apply path?
- Confirm `ScopedModification` accepts visibility-only mutations without
  requiring full layer-stack recompute on exit.
- Determine whether solo-export wall-clock time for a representative UDIM
  project (4+ UV tiles, 20+ layers) is practical for interactive use or
  should be reserved for batch/overnight exports.
```

---

## `design.md`

### §3.1 UDIM handling — append after the filename pattern section

```
Per-layer PNG assets for UDIM projects share the same limitation as
`alg.mapexport.save`: no per-tile filtering. For UDIM projects where
Photoshop needs per-tile per-layer assets, the Python solo-export
fallback (`sp_plugin/rizum_sp_to_ps/solo_export.py`) is the designated
path. This path is gated behind `texture_set.has_uv_tiles()` so non-UDIM
projects keep the fast, non-mutating JS bridge.
```

### §3.4 Padding & dilation — note UDIM interaction

After the bit-depth sentence, add:

```
For UDIM solo-export, padding and dilation are passed through
`exportParameters` in the `export_project_textures` config rather than
the `MapInfo` object used by `alg.mapexport.save`.
```

### §8 Remaining validation questions — add

```
- Host-measure solo-export latency for a representative UDIM project to
  decide whether it should be opt-in or automatic.
- Verify that `ScopedModification` wrapping visibility-only mutations does
  not trigger a full project recompute or dirty the save state.
```

---

## `plan.md`

### Direction 1 — add unchecked items after the existing per-layer PNG entry

```
- [ ] Add `bridge.export_layer_png_raw()` to pass exact engine channel
      strings without identifier mapping.
- [ ] Implement Python solo-export fallback module
      (`sp_plugin/rizum_sp_to_ps/solo_export.py`) for UDIM per-tile
      per-layer PNG export. Gate behind `has_uv_tiles()`.
- [ ] Host-test solo-export: measure latency, confirm visibility restore
      is reliable, check for thumbnail/refresh stalls.
- [ ] Host-test user-channel export with `documentStructure()` channel
      strings as the primary identifier on a project that has custom
      user channel labels (SCol, TNrm, SDF).
```

### Direction 1 — update existing unchecked item

The existing item:

```
- [ ] Host-test Painter export on representative projects: non-UDIM,
      multi-UDIM, grouped layers, masks, anchor references, and at least
      one unsupported blend/effect that must bake.
```

Add note: *"Multi-UDIM per-layer PNG fidelity depends on solo-export
fallback. Validate before claiming full UDIM support."*
