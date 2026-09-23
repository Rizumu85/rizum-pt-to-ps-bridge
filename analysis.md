# API Analysis

## Current Constraints

This document records API findings and host constraints. User-facing behavior
belongs in `design.md`; open work belongs in `plan.md`. The development log of
earlier corrections lives in `docs/archive/analysis-history.md`.

Host findings that still constrain the implementation:

- **No background work in Painter.** Even a 1-second `QTimer` polling
  `project.is_open()` correlated with brush-time freezes and crashes. Project
  state is checked only on user actions; the only timer is the bounded
  Photoshop-job receipt poll while a job the user started is running.
- **Per-layer export.** The Python export API only exports whole channels.
  Layer and mask pixels come from Painter 12.1's native stack-node texture
  export (`stack_node_export.py`), which also renders per-UV-tile payloads.
  `alg.mapexport.save([uid, "mask"])` resolves to `blendingmask` since
  SP 12.1.0 and must not be used for masks.
- **Effects are not exportable nodes.** `alg.mapexport.save([effectUid, ...])`
  fails; content and mask effects are provenance baked through their parent
  export. Editable Photoshop clipping reconstruction is abandoned.
- **Automatic Painter resource import is unsafe.** Importing 4K PNGs in the
  background caused thumbnail stalls, viewport slowdown, and crashes. Painter
  imports resources only when the user presses Apply in the desktop mapper.
- **Photoshop automation from Painter uses ExtendScript.** UXP panels are lazy
  and cannot receive a reliable external launch event, so Painter launches
  Photoshop with a JSX file and waits for a published receipt.
- **PSD reading.** The mapper reads PSD/PSB files with ag-psd (MIT) using
  `useRawData`, which decodes one layer at a time. It supports 8/16/32-bit
  channels including ZIP-with-prediction and PSB. Measured on production files:
  a 25-layer 4K PSD connects in about 1.7 s and a 522-layer 6000 px file in
  about 0.9 s. 32-bit layer data is linear and is encoded to sRGB.
- **Many PSDs have no persistent layer ids.** None of the user's production
  PSDs contained `lyid`. Painter-to-Photoshop inserts therefore address a
  target by layer id when present, otherwise by sibling index path (top first,
  matching the ExtendScript DOM) verified against the layer name.
- **Desktop mapper stdio.** GPUiX serves its automation protocol whenever stdin
  is a pipe, so the Painter link uses marked stdout lines and single-line JSON
  replies on the shared stream (see `desktop/README.md`).

## 0. Local API documentation coverage

| Area | Included local source | Coverage status |
|---|---|---|
| Substance Painter Python API | `pt-python-doc-md/substance_painter/` | Covered for traversal, export, resources, UI, events, layer-stack mutation, color management, and JS bridge |
| Legacy Painter JS API | `javascript-doc/` | Covered for the required map-export fallbacks: `alg.mapexport.save`, `alg.mapexport.exportPath`, and `alg.mapexport.channelIdentifiers` |
| Host-recorded Action Manager descriptors | Not included as ready-to-use project files | Must be recorded or validated in Photoshop for layer-mask pixel transfer and the RGB blend-gamma setting |

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
for per-layer and per-mask export. This is one of the small map-export JS
fallbacks in the SP side of the plugin. Logged in §4.2.

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

Historical automatic sync-back used `import_project_resource`. The original
PNG file can be deleted after import because data is copied into the `.spp`,
but host validation showed this path is too heavy for the current Phase 1
workflow. It is deprecated in favor of manual Photoshop PNG export and manual
Painter import.

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
  `tile_indices`, `channel_type`, `cache_key` — enough to detect that a
  stack/channel/tile changed, **not** which SP layer changed)
- `LayerStacksModelDataChanged` can signal that the layer-stack model changed,
  but the docs do not expose a per-layer `last_modified` timestamp. Conflict
  detection must therefore use coarse stack/channel cache keys or re-exported
  hashes, not a nonexistent per-layer timestamp.
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

## 4. Gaps & decisions — populated

### 4.1 Confirmed gaps

| Gap | Resolution |
|---|---|
| SP Python cannot export a single layer/mask to PNG | Painter 12.1 native stack-node texture export (`stack_node_export.py`) |
| SP Python cannot read project-level export path | Use `alg.mapexport.exportPath()` via `sp.js.evaluate` (see §2.1) |
| SP Python has no per-layer `last_modified` timestamp | Use channel/tile cache-key comparison or re-exported hashes for conservative conflict warnings |

### 4.2 JS fallback scope (SP side)

Exactly three JS calls are wrapped by `bridge.py`:

- `alg.mapexport.save(path, filepath, opts)` — per-layer PNG export
- `alg.mapexport.exportPath()` — project texture export path
- `alg.mapexport.channelIdentifiers(stackPath)` — stack-level used channel
  identifiers, including resolved user-channel labels where the host reports
  them

Nothing else. All traversal, blend modes, effects, masks, layer-stack
mutation, UI, events, and logging are Python-native.

---

## 5. Open questions

- **"Blend RGB Colors Using Gamma 1.0" settability** through an Action
  Manager descriptor — see §6.3. Big potential payoff; keep it off until a
  build can set it without a host modal error.
- **Current Painter normal-map orientation getter**: `NormalMapFormat` is
  documented for project creation settings, but no direct getter for the
  currently opened project was found in the local `project.md`. Store the
  value when known, infer from existing normal sources if possible, or expose
  a user setting.

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

If this setting is writable through an Action Manager descriptor, method B collapses from
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

If this setting is **not** writable from a script:

- Fall back to empirical per-mode compensation LUT calibrated in M3
- Accept that Overlay/SoftLight/HardLight family will have residual drift

### 6.3.1 Adobe community blend-mode clarification

Adobe staff clarified in a Substance 3D Painter community thread that Painter
blend modes should mostly behave like Photoshop blend modes, but Painter uses
different color-space management and can therefore show differences. The same
reply also calls out two structural details that matter for this bridge:

- Painter layers have per-channel blending, so BaseColor, Normal, Roughness,
  and other channels must read and export the blend mode for the specific
  channel being built.
- A Painter group also has its own blending mode, and the group result can be
  different from applying a blend mode only on the contained layer.

This supports the current M3 plan rather than replacing it. We still need the
Photoshop gamma-1.0 validation because the color-space difference is the likely
source of BaseColor drift. We also need group construction to preserve group
blend modes instead of flattening every group to Pass Through.

### 6.4 Sync-back color space handling

When a Photoshop layer PNG is imported into SP, it is sRGB-encoded (PS document is
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
    # match the project's normal map format. The local project docs expose
    # NormalMapFormat at project creation time, but no direct getter was found;
    # store it in our export manifest or ask the user if it cannot be inferred.
    fmt = manifest["normal_map_format"]
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

### 8.2 PS-side ExtendScript recipes

`footer.jsx` contains action-descriptor sequences the current JSX scripts
reuse for placing PNGs and building masks:

| ExtendScript function | What it does |
|---|---|
| `open_png(File)` | `Plc ` (placeEvent) action: places a PNG at origin, no free-transform |
| `layerToMask()` | Turns the top layer (pixel content) into a layer mask of the layer below. Sequence: select all pixels → copy → delete layer → make new reveal-all user mask on target → select mask channel → paste → deselect |
| `applyLayerMask()` | `GrpL` action — commits the mask into the layer's pixels |
| `fillSolidColour(R,G,B)` | Creates a `contentLayer`/`solidColorLayer` fill layer with given RGB |
| `Overlay_Normal()` | Hack: sets blend=linearLight @ 50% fill + linearBurn fill-effect layer at (255,255,128) to fake SP's NormalMapCombine |
| `del_bg()` / `rasterize_All()` / `send_backward()` / `center_layer()` / `new_layer()` | Small ExtendScript helpers |

### 8.3 Settings UI discrepancies vs. README

- `ConfigurePanel.qml:156` declares `maxValue: 256` for the dilation
  slider. The README claims 0–10. Neither is right for v2 (we use 0–64
  per `design.md §3.4`), but worth noting: the v1.1.8 **behavior** was
  0–256, only the README said 0–10.
- The "Launch Photoshop after export" feature stores a path to
  `photoshop.exe` and calls `alg.subprocess.startDetached([photoshopPath,
  photoshopScript.jsx])`. That is why old exports can enter Photoshop without a
  Photoshop-side button click. This was an ExtendScript execution path, not a
  Photoshop plugin invocation.

### 8.4 Documented bugs to avoid regressing

- Old plugin's blend-mode `switch` drops **`Darken`, `Lighten`, `Inverse
  divide`, `Inverse Subtract`, `Tint`, `Value`, `Signed addition`** as
  `blendingMode = ""` — i.e. silently omits the entire `blendMode` set
  line, leaving PS at its default `NORMAL`. v2 handles all of these per
  the mapping table in §3.6.
- Old plugin mutates `app.preferences.rulerUnits`, `typeUnits`,
  `displayDialogs` globally. The current JSX scripts save and restore
  `displayDialogs` around their work.

---

## 9. M1 request-preview contract

The first M1 implementation slice is intentionally read-only. It traverses the
open Painter project and emits request-preview JSON with the same shape that
later PNG-producing requests will use, but it does **not** call
`alg.mapexport.save` yet.

Minimum top-level fields for each preview request:

```json
{
  "schema_version": 1,
  "request_type": "preview",
  "project": {
    "name": "ProjectName",
    "path": "C:/path/project.spp",
    "uuid": "..."
  },
  "texture_set": "Body",
  "stack": "",
  "channel": "BaseColor",
  "channel_format": "sRGB8",
  "bit_depth": 8,
  "is_color": true,
  "udim": 1001,
  "uv_tile": {
    "u": 0,
    "v": 0,
    "name": "1001",
    "resolution": {"width": 2048, "height": 2048}
  },
  "normal_map_format": null,
  "baseline_cache_key": null,
  "layers": []
}
```

Layer/effect records include `uid`, `uid_hex`, `name`, `kind`, `visible`,
`has_blending`, `blend_mode`, `opacity`, `has_mask`, `mask_enabled`,
`mask_background`, `children`, `content_effects`, and `mask_effects` where
applicable. `normal_map_format` and `baseline_cache_key` may be null in the
preview slice because the local API docs did not expose a direct normal-format
getter or a current cache-key query outside events.

### 9.1 M1 bake decision fields

Each layer/effect record also carries pure metadata decisions:

| Field | Meaning |
|---|---|
| `bake_policy` | `keep_editable`, `bake`, `hidden`, or `no_blending` |
| `sync_direction` | `both`, `sp_to_ps_only`, or `none` |
| `ps_blend_mode` | Photoshop blend mode for the relevant channel/mask, if any |
| `warnings` | Human-readable limitations, e.g. approximate mapping or unsupported blend mode |

Default "Bake unsupported modes" behavior:

- PS-representable modes stay `keep_editable` and `sync_direction: "both"`.
- `Disable` becomes `hidden` and `sync_direction: "none"`.
- `Tint`, `Value`, `SignedAddition`, `InverseDivide`, `InverseSubtract`,
  `NormalMapCombine`, `NormalMapDetail`, and `NormalMapInverseDetail` become
  `bake` and `sync_direction: "sp_to_ps_only"`.
- `Replace` is treated as unsupported for editable compositing in default
  mode and is baked, matching `design.md §4.1`.

Preserve-all-layers mode:

- Approximate modes (`Tint`, `Value`, `SignedAddition`, `InverseDivide`,
  `InverseSubtract`, `Replace`) are kept editable with warnings.
- Normal-map blend modes remain baked because Photoshop has no equivalent.

### 9.2 M1 build bundle contract

After preview traversal is stable, Painter writes one bundle per
texture-set/stack/channel/UDIM request:

```text
<bundle>/
  build_request.json
  png/
    uid_<uid>.png
    uid_<uid>_mask.png
    baked_<uid>.png
```

`build_request.json` is the preview request promoted to
`request_type: "build"` with these additional fields:

- `build_request_file`: absolute path to the JSON file.
- `asset_dir`: absolute path to the `png/` directory.
- `psd_file`: absolute output PSD path for M2.
- `export_settings`: resolved padding, dilation, bit depth, keep-alpha, and
  per-UDIM resolution values passed to `alg.mapexport.save`.
- Per-node `asset` entries for editable or baked pixel payloads.
- Per-node `mask_asset` entries when a layer has an enabled mask.

Painter-side PNG writing is implemented behind the JS bridge wrapper and can be
disabled with `export_pngs=False` for local/static validation. When enabled in
Painter, PNG payloads are written with `alg.mapexport.save`; target discovery
may also use `alg.mapexport.channelIdentifiers` to hide unused stack channels.

`build_request.json` keeps the Python-facing channel name (for example
`BaseColor`) and also stores `channel_identifier` (for example `basecolor`) for
the legacy JS `alg.mapexport.save` call. The JS docs define export channels as
channel identifiers, not Python enum names.

## 10. Desktop runtime direction

The desktop bridge is now a GPUiX application using Bun, strict TypeScript,
React 19, and an exact-pinned `@gpuix/react`. GPUiX supplies the GPUI native
renderer; direct GPUI, Electron, Tauri, WinUI, and webview implementations are
not parallel fallbacks.

`mockups/pt-bridge-ui-v4.html`, the vendored `rizum_ui` design decisions, and
the shared icon snapshot remain the product's visual authority. The Rizum Glass
repository is used only for its GPUiX migration discipline: freeze the approved
reference, record visible states and motion in a reference contract, keep all
text colors explicit, and isolate frame-bound renderer queries from domain
state and transport work.

### 10.1 Explicit desktop transfer contracts

Photoshop selected-layer export now writes `photoshop_selection.json` beside
its PNG files. The manifest records the source document, stable Photoshop layer
IDs, blend metadata, and relative layer/mask PNG paths. The desktop app reads
that manifest together with either the PSD's persistent `.rizum.json` sidecar
or an explicit Painter `build_request.json` snapshot.

Apply writes `desktop_transfer.json` atomically. Each transfer contains the
source asset reference, destination Painter UID/path, and an explicit `inside`
or `after` insertion relation. This is a user-confirmed file contract, not a
revival of the deprecated `_pt_sync_inbox`, daemon, or background polling path.
