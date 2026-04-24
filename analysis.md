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

## 3. UXP Photoshop API

Source: `uxp-photoshop-main/src/pages/ps_reference/` + `uxp-api/reference-js/`
+ `guides/uxp_guide/`.

Entry point: `const { app, action, core, constants } = require('photoshop');`

### 3.1 Minimum Photoshop version

Manifest v5 requires **Photoshop ≥ 23.3** (UXP ≥ 6.0). All methods we rely on
are available at 23.3. Set `manifest.host.minVersion = "23.3.0"`.

This revises `design.md §2` which said "PS ≥ 23"; update to 23.3.

### 3.2 PSD creation & save — ✅ covered

| Need | API |
|---|---|
| New doc | `await app.createDocument({width, height, resolution, mode: "RGBColorMode", fill: "transparent"})` |
| Open existing | `await app.open(fileEntry)` — takes UXP File entry |
| Save PSD | `await doc.saveAs.psd(fileEntry, {embedColorProfile: true}, asCopy=false)` |
| Save current | `await doc.save()` |
| Close | `await doc.close(SaveOptions.DONOTSAVECHANGES)` |

Color mode: `"RGBColorMode"` (default), bit depth via `doc.bitsPerChannel`.

### 3.3 Layer creation & arrangement — ✅ covered via high-level DOM

| Need | API |
|---|---|
| New raster layer | `await doc.createPixelLayer({name, opacity, blendMode, fillNeutral})` |
| New group | `await doc.createLayerGroup({name, opacity, blendMode, fromLayers})` |
| Group existing | `await doc.groupLayers([layer1, layer2])` |
| Duplicate / move across doc | `await layer.duplicate(targetDoc)` |
| Reorder | `layer.move(relativeLayer, ElementPlacement.PLACEBEFORE\|PLACEAFTER\|PLACEINSIDE\|PLACEATBEGINNING\|PLACEATEND)` |
| Delete | `layer.delete()` |
| Visibility | `layer.visible = bool` |
| Opacity / fill | `layer.opacity = 0–100`, `layer.fillOpacity = 0–100` (ints) |
| Name | `layer.name = str` |
| Lock | `layer.allLocked = bool`, `.pixelsLocked`, `.positionLocked`, `.transparentPixelsLocked` |
| **Clipping mask** (design.md §5.2) | `layer.isClippingMask = true` — clips to layer below |
| Rasterize | `await layer.rasterize(RasterizeType)` / `await doc.rasterizeAllLayers()` |

### 3.4 Placing a PNG as raster content — ⚠ no high-level API

UXP Layer has no direct "load PNG into this raster layer" call. Two routes:

**Path A (proven from v1.1.8):**
```javascript
const pngDoc = await app.open(pngEntry);
const ours = pngDoc.layers[0];
await ours.duplicate(targetDoc);               // copies layer into our PSD
await pngDoc.closeWithoutSaving();
```

**Path B (surgical, via `batchPlay`):** the `placeEvent` action descriptor,
followed by `rasterize()`. More complex, same end state.

**Decision**: Path A. Matches what the old plugin did in JSX, survives new
UXP quirks, doesn't require reverse-engineering action descriptors.

### 3.5 Layer mask add/set — ⚠ `batchPlay` only

No high-level method. Add reveal-all mask, then fill it from a grayscale PNG
via the same open-and-duplicate trick targeting the mask channel:

```javascript
// Add reveal-all mask to active layer
await action.batchPlay([{
  _obj: "make", new: {_class: "channel"},
  at: {_ref: "channel", _enum: "channel", _value: "mask"},
  using: {_enum: "userMaskEnabled", _value: "revealAll"}
}], {});
// Select the mask channel, then paste the grayscale PNG's pixels into it.
```

Inbound flow uses `batchPlay` with `set` + `to: {_obj: "file", _path: maskPng}`
via the `placeEvent` action, or opens the mask PNG as a new doc and copies
its pixel channel into the mask channel of the target layer. **Details will
be finalized at M2 impl time by recording the sequence via PS's "Record Action
Commands" developer menu** (per `batchplay.md` workflow).

Mask presence detection: `doc.layers[i]` has no direct `hasLayerMask`
property. Use `batchPlay` `get` on `{_ref: "property", _property: "hasUserMask"}`
or check bounds differences — implementation detail for M2.

### 3.6 Blend modes — ✅ covered, better than v1.1.8

UXP `constants.BlendMode` members (relevant for our map):
`NORMAL, MULTIPLY, SCREEN, OVERLAY, DARKEN, LIGHTEN, COLORBURN,
COLORDODGE, LINEARBURN, LINEARDODGE, LINEARLIGHT, VIVIDLIGHT, PINLIGHT,
HARDLIGHT, SOFTLIGHT, DIFFERENCE, EXCLUSION, SUBTRACT, DIVIDE, HUE,
SATURATION, COLOR, LUMINOSITY, PASSTHROUGH, DISSOLVE, DARKERCOLOR,
LIGHTERCOLOR, HARDMIX`.

**Full SP → PS mapping** (supersedes the v1.1.8 table):

| SP BlendingMode | UXP BlendMode | Bake policy |
|---|---|---|
| Normal, Replace | NORMAL | keep |
| PassThrough (group only) | PASSTHROUGH | keep |
| Disable | — (set `visible=false`) | keep |
| Multiply | MULTIPLY | keep |
| Screen | SCREEN | keep |
| Overlay | OVERLAY | keep |
| Darken | DARKEN | keep |
| Lighten | LIGHTEN | keep |
| LinearDodge | LINEARDODGE | keep |
| LinearBurn | LINEARBURN | keep |
| ColorBurn | COLORBURN | keep |
| ColorDodge | COLORDODGE | keep |
| SoftLight | SOFTLIGHT | keep |
| HardLight | HARDLIGHT | keep |
| VividLight | VIVIDLIGHT | keep |
| LinearLight | LINEARLIGHT | keep |
| PinLight | PINLIGHT | keep |
| Difference | DIFFERENCE | keep |
| Exclusion | EXCLUSION | keep |
| Subtract | SUBTRACT | keep |
| Divide | DIVIDE | keep |
| Saturation | SATURATION | keep |
| Color | COLOR | keep |
| **Tint** | HUE (approx) | **bake in default; `[!]` in preserve-mode** |
| **Value** | LUMINOSITY (approx) | **bake in default; `[!]` in preserve-mode** |
| InverseDivide, InverseSubtract, SignedAddition | — | **always bake** |
| NormalMapCombine, NormalMapDetail, NormalMapInverseDetail | — | **always bake** |

**Improvements over v1.1.8 JSX plugin**:
- `Darken`, `Lighten` now mapped (old plugin dropped them)
- `LinearLight` now mapped (old plugin dropped it)
- `Tint` → `HUE`, `Value` → `LUMINOSITY` have approximate mappings in
  "Preserve all layers" mode instead of silent drop

### 3.7 Panel UI — ✅ covered

Manifest v5 entrypoint:
```json
{
  "entrypoints": [{
    "type": "panel",
    "id": "rizumBridge",
    "label": {"default": "Rizum PT Bridge"},
    "minimumSize": {"width": 260, "height": 300},
    "icons": [...]
  }]
}
```

Root is `index.html` (declared via `"main": "index.html"`). Standard DOM +
Spectrum Web Components (`<sp-button>`, `<sp-checkbox>`, `<sp-menu>`,
`<sp-action-button>`, etc.) for controls. CSS via Spectrum CSS.

No modal blocking for the panel itself. Long operations wrap in
`executeAsModal`.

### 3.8 File I/O — ✅ covered

`manifest.requiredPermissions.localFileSystem = "fullAccess"` gives us
arbitrary read/write. Two interfaces:

**Modern (token-based, UXP native):**
```javascript
const fs = require('uxp').storage.localFileSystem;
const entry = await fs.getEntryWithUrl("file:" + absolutePath);   // needs fullAccess
await entry.write(data);
// or getFileForOpening() / getFileForSaving() for user pickers
```

**Node-style fs** (convenience shim in UXP):
```javascript
const fs = require('fs');
await fs.writeFile(path, buffer);
const data = await fs.readFile(path);
const list = await fs.readdir(dir);
```

Use Node-style `fs` for the sync manifest + PNG I/O — simpler for our
read-manifest / write-manifest flow. `getFileForOpening()` picker for the
"pick a build_request.json" action on initial SP→PS build.

SHA1/hash: use Web Crypto `crypto.subtle.digest('SHA-1', buffer)`.

### 3.9 Modal execution scope — ✅ covered

All document-mutating calls must be inside:
```javascript
await require('photoshop').core.executeAsModal(async (ctx) => {
  // all the createLayer / setBlendMode / batchPlay calls
}, {commandName: "Rizum: Build PSD"});
```

`ctx.isCancelled` / `ctx.onCancel` for user-cancel handling. Wrap each
per-UDIM-tile build in its own modal scope so cancelling mid-export stops
cleanly between tiles.

History suspension: `doc.suspendHistory(cb)` OR `ctx.hostControl.suspendHistory({documentID})`
inside modal scope — collapses all our mutations into one undoable step.

### 3.10 Metadata — ⚠ revised: layer-name suffix + sidecar JSON

UXP exposes `require('uxp').xmp` for **document-level** XMP. Per-layer XMP
is not exposed in the high-level API. `batchPlay` can poke layer metadata
but it's fragile across PS versions.

**Revised schema** (replaces `design.md §7`):

- Every plugin-created PS layer gets a suffix `‡<sp_uid>` appended to its
  name (`DiffuseBase ‡a3f7`). The double-dagger (U+2021) is a single char
  chosen because it's not on any keyboard, so user-typed names won't
  collide. Users can rename the prefix freely as long as they keep the
  trailing `‡<uid>` — the regex `‡[0-9a-f]+$` is the lookup key.
- The PSD also gets a sidecar JSON: `<psdname>.rizum.json` next to the
  PSD file, containing:
  ```json
  {
    "rizum_version": "2.0.0",
    "sp_project_path": "C:/.../project.spp",
    "sp_project_uuid": "<from sp.project.get_uuid()>",
    "baseline_timestamp": "ISO-8601",
    "udim": 1001,
    "layers": [
      {"sp_uid": "a3f7", "sp_kind": "layer", "sync_direction": "both",
       "ps_name": "DiffuseBase ‡a3f7"},
      {"sp_uid": "b912", "sp_kind": "baked_effect",
       "sync_direction": "sp_to_ps_only",
       "ps_name": "[baked] Tint_Layer ‡b912"}
    ]
  }
  ```
- On sync-back, UXP parses the suffix from each layer's name as primary
  key; sidecar JSON is cross-reference to detect renames/duplicates.

**Design revision required**: update `design.md §7`.

### 3.11 Document / layer change detection — ⚠ compute on demand

UXP has `action.addNotificationListener(events, cb)` — event IDs include
`"select"`, `"make"`, `"delete"`, `"set"`, etc. But per-layer pixel-dirty
tracking is not a first-class event. Strategy:

- Don't try to track dirty state continuously
- When user clicks "Push to Painter", UXP iterates all `‡<sp_uid>`-tagged
  layers, exports each to PNG into a temp folder, SHA1s the PNG, compares
  against the baseline-export hash stored in sidecar JSON
- Unchanged layers get pre-unchecked in the push panel; changed ones are
  pre-checked
- User confirms and pushes

This avoids depending on the unreliable event stream, at the cost of a
one-off "scan" step (a few seconds for a typical PSD).

---

## 4. Gaps & decisions — populated

### 4.1 Confirmed gaps

| Gap | Resolution |
|---|---|
| SP Python cannot export a single layer/effect/mask to PNG | Use `alg.mapexport.save` via `sp.js.evaluate` (see §2.1) |
| SP Python cannot read project-level export path | Use `alg.mapexport.exportPath()` via `sp.js.evaluate` (see §2.1) |
| SP Python paint layers don't accept a bitmap source directly (strokes not exposed) | Insert a top `FillEffectNode` with PNG as source; hide existing content stack as backup (§1.7) |
| UXP has no high-level "load PNG into layer" | `app.open(pngEntry)` + `duplicate(targetDoc)` (§3.4) |
| UXP has no high-level layer-mask manipulation | `batchPlay` with `make new channel mask` + open+copy for mask content (§3.5) |
| UXP has no reliable per-layer XMP metadata | Layer-name suffix `‡<sp_uid>` + sidecar JSON (§3.10) |
| UXP has no per-layer dirty event | Hash-on-demand when user clicks Push (§3.11) |

### 4.2 JS fallback scope (SP side)

Exactly two JS calls are wrapped by `bridge.py`:

- `alg.mapexport.save(path, filepath, opts)` — per-layer PNG export
- `alg.mapexport.exportPath()` — project texture export path

Nothing else. All traversal, blend modes, effects, masks, layer-stack
mutation, UI, events, and logging are Python-native.

### 4.3 Design-doc revisions required

Applied at the end of this block:

1. **`design.md §2`**: change "PS ≥ 23" to "PS ≥ 23.3" (manifest v5
   requirement)
2. **`design.md §7`** (metadata schema): replace with layer-name-suffix
   `‡<sp_uid>` + sidecar JSON model (see §3.10 here)

No other design revisions forced. `design.md §4–§6` all remain valid given
UXP + batchPlay coverage.

---

## 5. Open questions to resolve during implementation

(Resolved ones deleted. Remaining:)

- **batchPlay for mask insert + content fill**: the exact action
  descriptor sequence will be worked out at M2 using Photoshop's "Record
  Action Commands" developer mode. Low risk — well-documented path — but
  not pre-verified here.
- **UXP `getEntryWithUrl("file:...")` with `fullAccess`**: documented but
  not hands-on verified. Node-style `fs` is a safer fallback; if the
  token-based approach has quirks, `fs.readFile`/`writeFile` covers us.
- **Panel UI behavior while `executeAsModal` is running**: per docs the
  panel stays responsive (events queue up). If we hit a blocking issue,
  split the long export into smaller modal scopes per UDIM tile.
- **PSD "Blend RGB Colors Using Gamma 1.0" settability via UXP** — see
  §6.3 below. Big potential payoff, verification needed at M3 start.

---

## 6. Color management deep dive (SP side)

Source: `pt-python-doc-md/substance_painter/colormanagement.md` +
`source/bitmap.md`.

### 6.1 Color space model in SP

| Space | When used | Enum |
|---|---|---|
| sRGB | Color-managed channels on output (BaseColor, Emissive, Diffuse, Specular, CoatColor, ScatterColor, SheenColor) | `GenericColorSpace.sRGB` |
| Working (Linear sRGB in legacy) | **Layer blending happens here** | `GenericColorSpace.Working` |
| Raw | Data channels (Roughness, Metallic, Height, Displacement, AO, Opacity, Glossiness, Anisotropy, IoR, Specularlevel, user channels) | `GenericColorSpace.Raw` / `DataColorSpace.Data` |
| Normal | Normal channel, depends on project OpenGL/DirectX | `NormalColorSpace.NormalXYZRight` / `...Left` |

When `alg.mapexport.save` writes a PNG:
- Color-managed channel → PNG is **sRGB-encoded** (gamma ~2.2)
- Data channel → PNG is **raw** (no conversion)
- Normal channel → PNG is raw in the project's normal orientation

### 6.2 The fundamental SP↔PS blend mismatch

- **SP**: layers composite in *Working* (linear sRGB) space. Tonemap + sRGB
  encode happens once at the end for display/export.
- **PS**: by default, blends in *sRGB gamma-encoded* space. `Multiply` of
  two sRGB values is not the same visual result as `Multiply` of their
  linear-space equivalents.

This is why `design.md §4 method B` (per-layer pre-compensation) is hard
in general — there's no scalar correction that makes an sRGB-space
multiply yield a linear-space multiply's result for arbitrary input.

### 6.3 Key finding: PS's "Blend RGB Colors Using Gamma 1.0" toggle

Photoshop supports document-level **"Blend RGB Colors Using Gamma 1.0"**
(Edit → Color Settings → More Options → Custom). When enabled for a
document:

- PS decodes sRGB → linear → blends → re-encodes
- This is **exactly what SP does**
- Result: Multiply/Screen/LinearDodge/LinearBurn/Darken/Lighten/ColorBurn/
  ColorDodge/Difference/Exclusion all produce SP-matching output **with
  zero per-layer pre-compensation**

If this setting is writable via UXP `batchPlay`, method B collapses from
"approximate per-mode compensation LUT" to "one document-level toggle at
PSD creation time". The action command is something along the lines of:

```javascript
// Not yet verified — M3 implementation will validate
{ _obj: "set",
  _target: [{_ref: "property", _property: "colorSettings"},
            {_ref: "document", _enum: "ordinal"}],
  to: { _obj: "colorSettings", rgbColorBlendGamma: 1.0 } }
```

**Action for M3**: verify this via "Record Action Commands" on a document
where we toggle the setting manually. If it works:

- Default export mode ("Bake unsupported modes") sets `rgbColorBlendGamma = 1.0`
  on every PSD; no per-layer math needed for representable blend modes
- "Preserve all layers" mode does the same; SP-only modes (Tint, Value,
  SignedAddition, etc.) still map to closest PS equivalent with `[!]`
  prefix

If this setting is **not** writable via UXP:

- Fall back to empirical per-mode compensation LUT calibrated in M3
- Accept that Overlay/SoftLight/HardLight family will have residual drift

### 6.4 Sync-back color space handling

When UXP pushes a PNG back to SP, the PNG is sRGB-encoded (PS document is
sRGB). SP's `import_project_resource(path, Usage.TEXTURE)` defaults the
imported `SourceBitmap` color space based on context:

- BaseColor (and other color-managed channels) → sRGB, correct by default
- Roughness/Metallic/Height/etc. (data channels) → **need manual override**

After `set_source(channel, resource_id)` returns a `SourceBitmap`:

```python
source_bitmap = node.set_source(channel, resource_id)
if is_data_channel(channel):
    source_bitmap.set_color_space(sp.colormanagement.GenericColorSpace.Raw)
elif channel == ChannelType.Normal:
    # match the project's normal map format
    fmt = sp.project.NormalMapFormat.OpenGL  # or query from project
    cs = (sp.colormanagement.NormalColorSpace.NormalXYZRight
          if fmt == sp.project.NormalMapFormat.OpenGL
          else sp.colormanagement.NormalColorSpace.NormalXYZLeft)
    source_bitmap.set_color_space(cs)
```

`sync_inbox.py` must know the channel for each incoming PNG (already in the
manifest) and apply the appropriate color-space override.

### 6.5 OCIO / ACE projects

Projects with `OCIO` or `PAINTER_ACE_CONFIG` env vars set use custom
color management. `Working` means whatever the config defines — not
guaranteed to be Linear sRGB.

**Phase 1 scope**: assume Legacy color management (Linear sRGB working
space). Document this assumption and emit a warning at export time if the
project uses OCIO/ACE. Full OCIO support can come in Phase 2.

---

## 7. Effect-type bake-or-keep matrix

For completeness. Each `NodeType` seen in `content_effects()` or
`mask_effects()` decides a handler:

| NodeType | In content stack | In mask stack | Handler |
|---|---|---|---|
| `FillEffect` | PS raster layer (clipping group) | Flattened into mask | Use `get_source()` to classify; if source is bitmap, export direct; if procedural/anchor, bake via `alg.mapexport.save(uid, channel)` |
| `PaintEffect` | PS raster layer (clipping group) | Flattened into mask | Bake (strokes not Python-readable anyway) |
| `FilterEffect` | Bake everything up to this effect | Bake into mask | Always bake |
| `GeneratorEffect` | Bake | Bake | Always bake |
| `LevelsEffect` | Bake | Bake | PS Levels differs from SP Levels |
| `CompareMaskEffect` | (invalid per `edition.md` table) | Bake | Mask only |
| `ColorSelectionEffect` | (invalid) | Bake | Mask only |
| `AnchorPointEffect` | Bake in place | Bake in place | Per `design.md §5.4` |

"Bake" means: call `alg.mapexport.save([effect_uid, channel], ...)` to get
the effective contribution up to and including that effect, then emit a
single PS raster layer with that PNG.

"Instance layer" (`InstanceLayerNode`) is a top-level type — treat as a
paint layer, bake its fully-resolved content to one raster.

No further per-effect introspection needed at the `design.md` level; the
exporter only needs the type enum + uid to dispatch.

---

## 8. Old plugin findings (v1.1.8) — reusable patterns

Source: `ps-export_Rizum v1.1.8/ps-export-Rizum/`. The old plugin is
JS/QML on the SP side and ExtendScript (.jsx) on the PS side. Several
patterns translate cleanly to our new architecture.

### 8.1 SP-side patterns worth porting

From `photoshop.js` and `main.qml`:

| Pattern | v1.1.8 source | Where it lives in v2 |
|---|---|---|
| Settings persisted in SP preferences (last checked material/stack/channel list, dilation, bit depth, padding, launch-PS) | `alg.settings.setValue(...)` | `sp_plugin/rizum_sp_to_ps/settings.py` using `QSettings` or project metadata (`sp.project.Metadata("Rizum")`) |
| Material/stack/channel tree picker with "All"/"None" buttons + hierarchical check propagation | `ExportDialog.qml` | `ui.py` — PySide6 `QTreeWidget` with tri-state checkboxes |
| Recursive layer-tree traversal (DFS) with per-leaf PNG export and per-folder group creation | `layersDFS()` in `photoshop.js` | `exporter.py` — use `GroupLayerNode.sub_layers()` + type switch |
| Export path = `alg.mapexport.exportPath() + "/" + projectName + "_photoshop_export/"` | `photoshop.js:54` | Same, via JS bridge (§2.1). Preserved for compatibility with existing user workflows. |
| Default normal-channel background = RGB(128, 128, 255) fill layer at the bottom | `photoshop.js:189-192` | `exporter.py` — emit a `fill` entry in `build_request.json` for the `normal` channel |
| Bottom "snapshot" layer (full flattened channel export, hidden, at top of PSD) as visual reference | `photoshop.js:194-197` | Optional debug feature in v2; off by default. Useful for verifying the live stack matches the ground-truth composite |
| Folder visibility set **after** children are added (gotcha: PS overrides to `true` otherwise) | `photoshop.js:242` comment | Note in `ps_plugin/src/build-psd.js` — set `group.visible` at the end of group processing, not at creation |
| Rasterize-all at end of PSD build | `photoshop.js:185` | `ps_plugin/src/build-psd.js` — optional; off by default in v2 since we want editable layers |
| Bit-depth dropdown: "TextureSet value" (−1) / "8 bits" / "16 bits" | `ConfigurePanel.qml:193-197` | `ui.py` — same three options. Value −1 means "use `Channel.bit_depth()`" |

### 8.2 PS-side ExtendScript recipes → UXP `batchPlay` port targets

`footer.jsx` contains pre-built action-descriptor sequences that solve
exactly the problems UXP's high-level API leaves open. Port these
directly to `action.batchPlay` format:

| ExtendScript function | What it does | UXP port |
|---|---|---|
| `open_png(File)` | `Plc ` (placeEvent) action: places a PNG at origin, no free-transform | `batchPlay [{_obj: "placeEvent", null: {_path, _kind: "local"}, freeTransformCenterState: {_enum: "quadCenterState", _value: "QCSAverage"}, offset: {...zero...}}]` then `layer.rasterize()` |
| `layerToMask()` | Turns the top layer (pixel content) into a layer mask of the layer below. Sequence: select all pixels → copy → delete layer → make new reveal-all user mask on target → select mask channel → paste → deselect | Direct port. 7 action descriptors, same ordering. Exact JS in old source can be translated mechanically. |
| `applyLayerMask()` | `GrpL` action — commits the mask into the layer's pixels | `batchPlay [{_obj: "GrpL", null: {_ref: "layer", _enum: "ordinal", _value: "targetEnum"}}]`. Used only if user wants to bake masks. |
| `fillSolidColour(R,G,B)` | Creates a `contentLayer`/`solidColorLayer` fill layer with given RGB | For the normal-channel background fill (`RGB 128,128,255`). Direct batchPlay port of the same descriptor tree. |
| `Overlay_Normal()` | Hack: sets blend=linearLight @ 50% fill + linearBurn fill-effect layer at (255,255,128) to fake SP's NormalMapCombine | **Drop** — v2 bakes normal-map modes per `design.md §4`. Keep as reference if anyone wants to resurrect |
| `del_bg()` / `rasterize_All()` / `send_backward()` / `center_layer()` / `new_layer()` | Small ExtendScript helpers | `del_bg` → `layer.delete()`; `rasterize_All` → `doc.rasterizeAllLayers()`; `send_backward` → `layer.move(other, ElementPlacement.PLACEAFTER)`; others not needed |

### 8.3 Settings UI discrepancies vs. README

- `ConfigurePanel.qml:156` declares `maxValue: 256` for the dilation
  slider. The README claims 0–10. Neither is right for v2 (we use 0–64
  per `design.md §3.4`), but worth noting: the v1.1.8 **behavior** was
  0–256, only the README said 0–10.
- The "Launch Photoshop after export" feature stores a path to
  `photoshop.exe`. v2 drops this — plugin runs inside PS already; the
  UXP panel's "Build from Painter" button replaces that launch step.

### 8.4 Documented bugs to avoid regressing

- Old plugin's blend-mode `switch` drops **`Darken`, `Lighten`, `Inverse
  divide`, `Inverse Subtract`, `Tint`, `Value`, `Signed addition`** as
  `blendingMode = ""` — i.e. silently omits the entire `blendMode` set
  line, leaving PS at its default `NORMAL`. v2 handles all of these per
  the mapping table in §3.6.
- Old plugin mutates `app.preferences.rulerUnits`, `typeUnits`,
  `displayDialogs` globally. In UXP this is moot — `executeAsModal`
  provides isolation.
