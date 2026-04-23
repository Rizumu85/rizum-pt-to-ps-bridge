# API Analysis

**Status**:
- §1 SP Python API — **done**
- §2 SP JS API fallback — **done**
- §3 UXP Photoshop API — skeleton, not yet populated
- §4 Gaps & decisions — partially filled from §1/§2; finalize after §3
- §5 Open questions — alive

Populating this doc **must** happen before `plan.md` milestones start.
Every design claim in `design.md §5–6` needs a line item here that points
to a real API call — otherwise the design claim is unverified.

## Summary of findings so far (SP side)

- Every capability in `design.md §5–6` that is SP-side has a Python API
  mapping, **except per-layer PNG export** — that requires one JS fallback
  (`alg.mapexport.save`) via `substance_painter.js.evaluate`.
- `design.md §4` (color fidelity bake vs pre-compensation), `§5` (layer
  structure mapping), `§6` (sync-back inbox with embedded resources), `§7`
  (metadata schema) are all feasible on the SP side as designed.
- Paint layer strokes aren't Python-writable. Sync-back to a paint layer
  must be implemented as "insert fill effect at top of content stack with
  new PNG as source; hide old effects as backup" — same hidden-backup
  pattern we already planned for masks in `design.md §6.3`. **Design is
  consistent; no revision needed.**
- No SP-side capability surfaced that forces a `design.md` revision.

---

## 1. SP Python API

Source: `pt-python-doc-md/substance_painter/`. All API calls below use the
abbreviated module aliases: `sp = substance_painter`, `ls = sp.layerstack`,
`ts = sp.textureset`.

### 1.1 Document / project structure traversal — ✅ fully covered

| Need | API |
|---|---|
| List texture sets | `ts.all_texture_sets() → List[TextureSet]` |
| Active stack | `ts.get_active_stack() → Stack` |
| Set active stack | `ts.set_active_stack(stack)` — required before some export operations |
| All stacks of a texture set | `TextureSet.all_stacks() → List[Stack]` |
| Layered-material check | `TextureSet.is_layered_material() → bool` |
| All channels of a stack | `Stack.all_channels() → Dict[ChannelType, Channel]` |
| Channel format / bit depth / is_color | `Channel.format()`, `Channel.bit_depth()`, `Channel.is_color()` |
| Walk layer tree — root | `ls.get_root_layer_nodes(stack) → List[LayerNode subtype]` |
| Walk layer tree — descend | `GroupLayerNode.sub_layers() → List[LayerNode]` |
| Node type | `Node.get_type() → NodeType` (PaintLayer, FillLayer, GroupLayer, InstanceLayer, PaintEffect, FillEffect, GeneratorEffect, FilterEffect, LevelsEffect, CompareMaskEffect, ColorSelectionEffect, AnchorPointEffect) |
| Node uid / name / visible | `Node.uid()`, `.get_name()`, `.is_visible()`, `.set_visible(bool)` |
| Walk content (sub-effect) stack | `LayerNode.content_effects() → List[EffectNode]` |
| Walk mask (sub-effect) stack | `LayerNode.mask_effects() → List[EffectNode]` |
| Parent / siblings | `Node.get_parent()`, `.get_next_sibling()`, `.get_previous_sibling()` |
| Texture set of a node | `Node.get_texture_set() → TextureSet` |

Instanced-layer handling: `InstanceLayerNode` is a separate type; treat as a
paint layer for export purposes (bake final content, export as one raster).
Deep recursion not needed — instance content is rendered at the instance site.

### 1.2 Layer blend mode + opacity — ✅ fully covered

- `Node.has_blending() → bool` — not all nodes support blending (Levels doesn't)
- `Node.get_blending_mode(channel: ChannelType | None) → BlendingMode`
- `Node.set_blending_mode(mode, channel)` — `channel=None` for nodes inside a mask stack (monochannel)
- `Node.get_opacity(channel) → float` (0.0–1.0)
- `Node.set_opacity(float, channel)`
- `Node.is_in_mask_stack() → bool` — determines whether `channel` must be `None`

**BlendingMode enum** (exactly matches what `design.md §4` assumes):
`Normal, PassThrough, Disable, Replace, Multiply, Divide, InverseDivide, Darken, Lighten, LinearDodge, Subtract, InverseSubtract, Difference, Exclusion, SignedAddition, Overlay, Screen, LinearBurn, ColorBurn, ColorDodge, SoftLight, HardLight, VividLight, LinearLight, PinLight, Tint, Saturation, Color, Value, NormalMapCombine, NormalMapDetail, NormalMapInverseDetail`.

**Per-channel blend modes**: every non-mask node has a possibly-different
blend mode per channel. Export must iterate all active channels per layer,
which also means one PSD per channel (already implied by `design.md §3`).

### 1.3 Effects (fill / paint / filter / generator / levels / anchor) — ✅ covered

Effects surface via `content_effects()` / `mask_effects()`. Type check with
`isinstance(node, ls.FillEffectNode)` etc. All effect node types:

| Node type | Purpose for export |
|---|---|
| `FillEffectNode` | Exposable as its own PS layer (has source — bitmap/material/color/anchor) |
| `PaintEffectNode` | Exposable as its own PS layer (strokes rendered to bitmap) |
| `GeneratorEffectNode` | Bakes to raster (procedural, no PS equivalent) |
| `FilterEffectNode` | Bakes its output stack into a single PS raster layer |
| `LevelsEffectNode` | Bakes (PS Levels differs from SP Levels; safer to flatten) |
| `CompareMaskEffectNode` | Mask-only; bakes |
| `ColorSelectionEffectNode` | Mask-only; bakes |
| `AnchorPointEffectNode` | Bakes to static raster (per `design.md §5.4`) |

**FillEffect source introspection** (`source/` module):
- `FillEffectNode.source_mode → SourceMode` (`Material`, `Split`, or `None` for mask)
- `FillEffectNode.get_source(channel) → SourceBitmap | SourceUniformColor | SourceSubstance | SourceReference | SourceFont | SourceVectorial`
- `SourceReference` wraps an anchor point ref — that's how we detect "this fill is a reference to an anchor"

**Anchor point semantics**:
- `AnchorPointEffectNode` is a marker node placed inside a layer's content or
  mask stack. It captures the stack state at that position.
- Another node can *reference* an anchor via `set_source(channel, anchor_node)`
  — the `AnchorPointEffectNode` instance is passed in as the source param.
- No direct "resolve to bitmap" API. To bake, we need the JS-side
  `alg.mapexport.save([anchor_uid, channel], ...)` — see §2.

### 1.4 Mask structure — ✅ covered

- `LayerNode.has_mask() → bool`
- `LayerNode.add_mask(MaskBackground.Black | .White)`
- `LayerNode.remove_mask()`
- `LayerNode.get_mask_background() → MaskBackground`
- `LayerNode.is_mask_enabled() / .enable_mask(bool)`
- Mask sub-effect stack: `LayerNode.mask_effects()` (same interface as content)
- `is_in_mask_stack()` on each effect tells us which stack it's in — needed
  because mask-stack effects are monochannel (blend mode takes `channel=None`)
- **Hidden-backup pattern** (`design.md §6.3`): iterate the current mask
  effects, call `effect.set_visible(False)` on each; then
  `ls.insert_fill(ls.InsertPosition.inside_node(layer, ls.NodeStack.Mask))`
  at the top, set its source to the synced PNG's resource ID.

### 1.5 UDIM / UV tile iteration — ✅ covered

- `TextureSet.has_uv_tiles() → bool`
- `TextureSet.all_uv_tiles() → List[UVTile]` (ordered by U, then V)
- `UVTile.u`, `UVTile.v` — **no `UVTile.udim` attribute**; we compute
  `udim = 1001 + u + 10*v` ourselves
- `UVTile.get_resolution() → Resolution` (may differ from texture set)
- Export JSON config uses `$udim` token in `fileName` pattern → SP fills in
  the number automatically. Also supports a UV-tile filter:
  `"filter": {"uvTiles": [[u, v], ...]}` — lets us export one tile at a time.

Project workflow: `ProjectWorkflow.UVTile` vs `TextureSetPerUVTile`. The
former is the modern workflow (one TS holding all tiles). Plugin must
support both but we can prioritize `UVTile`.

### 1.6 Per-layer/per-effect export to PNG — ⚠ gap, JS fallback required

**Python `sp.export` only exports full channels** via
`export_project_textures(json_config)`. The JSON config's `exportList` filters
by texture set / stack / uvTile / output-map — there is **no filter that
isolates a single layer or effect node**. No "snapshot at this layer uid"
equivalent in Python.

**The v1.1.8 plugin relied on JS `alg.mapexport.save([uid, channel], path, config)`**
which *does* take a layer uid to isolate the contribution. Confirmed present
in JS via `javascript-doc/alg.mapexport.html`:

```js
alg.mapexport.save([24, "mask"], "c:/file.png")              // uid
alg.mapexport.save(["M1", "Group 1", "Layer 1", "mask"], ...) // path
alg.mapexport.save(["M1", "base color"], "c:/file.jpg",
                    {padding: "Transparent", dilation: 0,
                     resolution: [256, 512]})
```

**Decision**: keep using `alg.mapexport.save` via `substance_painter.js.evaluate`
for per-layer + per-effect + per-mask export. This is the only JS fallback in
the SP side of the plugin. Logged in §4.2.

Still useful Python APIs:
- `sp.export.list_project_textures(config)` — dry run / preview
- `sp.export.PredefinedExportPreset.list_output_maps(stack)` — get channel list
- `sp.export.get_default_export_path() → str` — default save path
- Full JSON config doc fully covers padding/dilation/bit depth/resolution

### 1.7 Resource import (embedded) — ✅ covered, with nuance

| Function | Persistence |
|---|---|
| `sp.resource.import_project_resource(path, Usage.TEXTURE)` | Embedded in `.spp`, survives restart |
| `sp.resource.import_session_resource(path, Usage.TEXTURE)` | In memory only, lost on restart |

Return is a `Resource` object with `.identifier() → ResourceID` which is
what fill layers / fill effects accept as their source argument.

**Sync-back uses `import_project_resource`**. The original PNG file can be
deleted after import — data is copied into the `.spp`.

Assigning to a paint layer:
- **Paint layers don't accept a bitmap source directly** — strokes aren't
  Python-accessible (`paint.md` explicitly: "Strokes are not accessible from
  the Python API").
- Strategy: insert a `FillEffectNode` at the top of the paint layer's
  content stack with the imported PNG as `set_source(channel, resource_id)`.
  Old paint strokes remain below as hidden-backup (`set_visible(False)` via
  §1.4 pattern).

Assigning to a fill layer:
- `FillLayerNode.set_source(channel, ResourceID)` directly — simpler.

Assigning to a mask:
- Mask stack takes fill effects (`ls.insert_fill(position)` with
  `NodeStack.Mask` position). Source via `set_source(None, resource_id)` —
  mask fills are monochannel.

### 1.8 Layer-stack mutation — ✅ fully covered

- `ls.insert_paint(InsertPosition) → PaintLayerNode | PaintEffectNode`
- `ls.insert_fill(InsertPosition) → FillLayerNode | FillEffectNode`
- `ls.insert_group(InsertPosition) → GroupLayerNode`
- `ls.insert_anchor_point_effect(position, name) → AnchorPointEffectNode`
- `ls.insert_filter_effect(position, filter_resource_id)`
- `ls.delete_node(node)`
- `ls.InsertPosition.above_node / below_node / inside_node(node, NodeStack) / from_textureset_stack(stack)`
- `ls.NodeStack.{Substack, Content, Mask}` — picks which stack to insert into
- `ls.ScopedModification("name")` — context manager that batches edits into
  one undo entry; also batches expensive recomputation. **Use this around
  every sync-apply operation.**

Insertion rule tables in `edition.md` confirm: fill effect into content or
mask stack is legal; paint effect into content or mask is legal; anchor into
content or mask is legal.

### 1.9 UI (PySide6) — ✅ fully covered

- `sp.ui.get_main_window() → QMainWindow` (parents our dialogs)
- `sp.ui.add_dock_widget(widget, ui_modes=UIMode.Edition) → QDockWidget` —
  register the Rizum panel
- `sp.ui.add_action(ApplicationMenu.File, qaction)` — menu entry
- `sp.ui.add_plugins_toolbar_widget(widget)` — toolbar entry
- Use standard PySide6 dialog widgets (QDialog, QCheckBox, QComboBox,
  QProgressBar). All Qt modules shipped with SP's Python.

### 1.10 Events / file watching — ✅ covered

- `sp.event.DISPATCHER.connect(EventClass, callback)` — weak ref
- `sp.event.DISPATCHER.connect_strong(EventClass, callback)` — strong ref,
  use for our sync-inbox watcher that must outlive function scope
- Events we need: `ProjectOpened`, `ProjectEditionEntered`,
  `ProjectAboutToClose`, `ProjectClosed`, `ExportTexturesEnded`,
  `TextureStateEvent` (fires on texture changes; has
  `tile_indices`, `channel_type`, `cache_key` — enough to detect per-layer
  changes for dirty tracking on the SP side)
- **QFileSystemWatcher** (Qt) is usable directly since PySide6 is available —
  that's how we watch `_pt_sync_inbox/` for new manifests

### 1.11 Logging & errors — ✅ covered

- `sp.logging.info(str)`, `.warning(str)`, `.error(str)` — user-facing
- `sp.logging.log(severity, channel, message)` — custom channel per plugin;
  we'll use channel `"Rizum"`
- `sp.exception.*` — `ProjectError`, `ServiceNotFoundError`,
  `ResourceNotFoundError`, `EditionContextException`, etc.

---

## 2. SP JS API (fallback bridge)

Invoked via `sp.js.evaluate(js_source_str) → str` (JSON-serialised return).
Documented in `pt-python-doc-md/substance_painter/js.md`.

### 2.1 Capabilities present in JS but missing in Python

Two:

**`alg.mapexport.save([path_or_uid…], filepath, config?)`** — per-layer export
- Saves the rendered output of a single layer / effect / mask to disk
- Path can be `[uid]`, `[uid, channel]`, `[texture_set, channel]`,
  `[texture_set, stack, channel]`, `[texture_set, "GroupName", "LayerName", "mask"]`
- Config options: `padding` (`"Infinite" | "Transparent" | …`), `dilation`
  (int), `resolution` (`[w, h]`), `bitDepth`, `keepAlpha`, `dithering`
- This is how the v1.1.8 plugin gets per-layer PNGs
- **We'll wrap it in `bridge.py` as `export_layer_png(uid, channel, config, out_path)`**

**`alg.mapexport.exportPath()`** — project-level export path (dynamic)
- Returns the current project's texture export directory (the path the user
  sees and can change in Painter's Export Textures dialog)
- Updates whenever the user changes the project's export path — our plugin
  must read it fresh on every export, not cache it
- The Python-side `sp.export.get_default_export_path()` returns the
  **application** default, which is NOT the project-specific path — confirmed
  in `export.md`. So we go through JS.

### 2.2 JS invocation bridge

```python
import substance_painter.js
import json

def export_layer_png(uid: int, channel: str, out_path: str,
                     padding="Infinite", dilation=0,
                     resolution=None, bit_depth=8) -> None:
    opts = {"padding": padding, "dilation": dilation,
            "bitDepth": bit_depth, "keepAlpha": False}
    if resolution:
        opts["resolution"] = list(resolution)
    js = (f'alg.mapexport.save([{uid}, "{channel}"], '
          f'{json.dumps(out_path)}, {json.dumps(opts)})')
    sp.js.evaluate(js)   # returns "" on success, raises RuntimeError on failure
```

Side effects / concerns:
- `sp.js.evaluate` returns a **JSON-formatted string** — successful save
  returns `""` / `null`. Parse accordingly.
- Errors surface as Python `RuntimeError` with JS stack trace as message
- Path escaping: use `json.dumps()` on every path to handle backslashes and
  quotes safely
- JS engine is single-threaded and blocking — each `evaluate` call yields
  synchronously

### 2.3 Also needed from JS (blend-mode + document structure)

`design.md` lets us get blend modes from Python now (`Node.get_blending_mode`),
so we **don't** need `alg.mapexport.layerBlendingModes`. Document structure
traversal is fully Python. Only `alg.mapexport.save` is a JS-only dependency.

---

---

## 2. SP JS API (fallback — only if Python is missing something)

Source: `pt-python-doc-md/substance_painter/js.md` + `javascript-doc/`.

### 2.1 Capabilities confirmed present in JS but missing in Python
_Populate after §1 is done._

### 2.2 JS invocation bridge
- [ ] How to call `alg.*` from Python (`substance_painter.js.evaluate`?)
- [ ] Return-value marshalling
- [ ] Error propagation

---

## 3. UXP Photoshop API

Source: `uxp-photoshop-main/reference-ps.js`, `uxp-photoshop-main/src/`.

### 3.1 PSD creation & save
- [ ] `app.documents.add(...)` signature
- [ ] `doc.saveAs` / `doc.save` for PSD
- [ ] Color mode, bit depth, ICC profile control
- [ ] Open existing PSD

### 3.2 Layer creation
- [ ] Raster (`ArtLayer`) from PNG file
- [ ] Layer group (`LayerSet`)
- [ ] Clipping mask toggle (`grouped` / `clipping mask`)
- [ ] Layer ordering / move-to-end / move-to-beginning
- [ ] Set opacity, visibility

### 3.3 Blend modes
- [ ] `BlendMode` enum values actually supported in UXP (may differ from ExtendScript)
- [ ] PASSTHROUGH for groups
- [ ] Gap list: which SP modes have no UXP mapping

### 3.4 Layer masks
- [ ] Add layer mask from PNG (grayscale)
- [ ] Detect whether layer has a mask
- [ ] `Apply Layer Mask` detection (pre-sync-back diagnostic)

### 3.5 Metadata (XMP / per-layer info)
- [ ] XMP packet read/write on document
- [ ] Per-layer custom metadata: supported method in UXP
- [ ] Sidecar-JSON fallback policy

### 3.6 Panel UI
_`uxp-photoshop-main/reference-spectrum.js`, `reference-html.js`, `reference-css.js`._

- [ ] Panel registration via manifest
- [ ] Spectrum Web Components used: `sp-button`, `sp-checkbox`, etc.
- [ ] Event model inside modal execution

### 3.7 File I/O + local FS
- [ ] UXP FS API: `require('fs')` or `uxp.storage.localFileSystem`
- [ ] Write PNG + JSON to a path outside the plugin sandbox
- [ ] Hash computation (sha1) availability

### 3.8 Modal execution scope
- [ ] `executeAsModal` wrapper for all doc-mutating calls
- [ ] Long-running export: batching + progress

### 3.9 Document / layer change detection
_For sync-back "last changed" tracking._

- [ ] Event or poll-hash strategy
- [ ] Timestamp / dirty flag per layer

---

## 4. Gaps & decisions

_Fill once §1–3 are populated._

### 4.1 Capabilities missing from chosen API stack
### 4.2 JS fallback scope (SP side)
### 4.3 Design-doc revisions required (if any)

---

## 5. Open questions to resolve during reading

- Does SP Python expose enough of the effect stack for a sub-effect to be
  exported as an isolated PNG? If not, sub-effect clipping-group mapping
  (`design.md §5.2`) may need to fall back to JS or be reduced to
  flatten-per-layer.
- Does UXP support writing per-layer XMP metadata reliably across PS 23,
  24, 25, 26? If not, sidecar JSON becomes the only source of truth.
- What is the exact gamma behavior of PS blend modes in UXP (vs
  ExtendScript legacy)? Needed to calibrate `compensation.py`.
- UXP panel + modal execution: can the sync-back panel show a diff
  dialog while a modal export is running? If not, split into two
  separate user actions.
