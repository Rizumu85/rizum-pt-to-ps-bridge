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
| Substance Painter Python API | `reference-docs/pt-python-doc-md/substance_painter/` | Covered for traversal, export, resources, UI, events, layer-stack mutation, color management, and JS bridge |
| Legacy Painter JS API | `reference-docs/pt-javascript-doc-html/` | Covered for the `alg.mapexport` queries the plugin uses (§2) |

---

## 1. SP Python API

Source: `reference-docs/pt-python-doc-md/substance_painter/`. All API calls below use the
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
`isinstance(node, ls.FillEffectNode)` etc. No effect is exported as its own
Photoshop layer: every one is baked through its parent layer's or mask's
export (Current Constraints). All effect node types:

| Node type | What it holds |
|---|---|
| `FillEffectNode` | A source: bitmap, material, color or anchor reference |
| `PaintEffectNode` | Strokes |
| `GeneratorEffectNode` | A procedural generator (no PS equivalent) |
| `FilterEffectNode` | A filter over the stack below it |
| `LevelsEffectNode` | Levels (PS Levels differs from SP Levels) |
| `CompareMaskEffectNode` | Mask-only |
| `ColorSelectionEffectNode` | Mask-only |
| `AnchorPointEffectNode` | An anchor point (`design.md §5.4`) |

**FillEffect source introspection** (`source/` module):
- `FillEffectNode.source_mode → SourceMode` (`Material`, `Split`, or `None` for mask)
- `FillEffectNode.get_source(channel) → SourceBitmap | SourceUniformColor | SourceSubstance | SourceReference | SourceFont | SourceVectorial`
- `SourceReference` wraps an anchor point ref — that's how we detect "this fill is a reference to an anchor"

**Anchor point semantics**:
- `AnchorPointEffectNode` is a marker node placed inside a layer's content or
  mask stack. It captures the stack state at that position.
- Another node can *reference* an anchor via `set_source(channel, anchor_node)`
  — the `AnchorPointEffectNode` instance is passed in as the source param.
- No direct "resolve to bitmap" API: an anchor reference reaches Photoshop
  baked into the export of the layer that uses it.

### 1.4 Mask structure — ✅ covered

- `LayerNode.has_mask() → bool`
- `LayerNode.add_mask(MaskBackground.Black | .White)`
- `LayerNode.remove_mask()`
- `LayerNode.get_mask_background() → MaskBackground`
- `LayerNode.is_mask_enabled() / .enable_mask(bool)`
- Mask sub-effect stack: `LayerNode.mask_effects()` (same interface as content)
- `is_in_mask_stack()` on each effect tells us which stack it's in — needed
  because mask-stack effects are monochannel (blend mode takes `channel=None`)

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

### 1.6 Per-layer export to PNG — ✅ covered by the stack-node export

**Python `sp.export` only exports full channels** via
`export_project_textures(json_config)`. The JSON config's `exportList` filters
by texture set / stack / uvTile / output-map — there is **no filter that
isolates a single layer or effect node**.

Layer and mask pixels therefore come from Painter 12.1's native stack-node
texture export (`stack_node_export.py`), one layer or mask at a time and per
UV tile. The legacy JS `alg.mapexport.save([uid, channel])` that the v1.1.8
plugin used is no longer called (Current Constraints).

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

Apply imports each mapped Photoshop layer with `import_project_resource`
(`desktop_transfer.py`); the data is copied into the `.spp`. Importing in the
background was too heavy (Current Constraints), so nothing is imported before
the user presses Apply.

**Paint layers don't accept a bitmap source** — strokes aren't
Python-accessible (`paint.md`: "Strokes are not accessible from the Python
API"), so a Photoshop layer arrives as a new fill layer.

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
  one undo entry; also batches expensive recomputation. Apply runs inside
  one.

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
- `sp.event.DISPATCHER.connect_strong(EventClass, callback)` — strong ref
- The plugin connects to none of them (Current Constraints: no background
  work). Available: `ProjectOpened`, `ProjectEditionEntered`,
  `ProjectAboutToClose`, `ProjectClosed`, `ExportTexturesEnded`,
  `TextureStateEvent` (fires on texture changes; has
  `tile_indices`, `channel_type`, `cache_key` — enough to detect that a
  stack/channel/tile changed, **not** which SP layer changed)
- `LayerStacksModelDataChanged` can signal that the layer-stack model changed,
  but the docs do not expose a per-layer `last_modified` timestamp. Conflict
  detection must therefore use coarse stack/channel cache keys or re-exported
  hashes, not a nonexistent per-layer timestamp.

### 1.11 Logging & errors — ✅ covered

- `sp.logging.info(str)`, `.warning(str)`, `.error(str)` — user-facing
- `sp.logging.log(severity, channel, message)` — custom channel per plugin;
  we'll use channel `"Rizum"`
- `sp.exception.*` — `ProjectError`, `ServiceNotFoundError`,
  `ResourceNotFoundError`, `EditionContextException`, etc.

---

## 2. SP JS API (fallback bridge)

Invoked via `sp.js.evaluate(js_source_str) → str` (JSON-serialised return).
Documented in `reference-docs/pt-python-doc-md/substance_painter/js.md`.
`bridge.py` wraps four read-only queries, all under `alg.mapexport`; nothing
is exported through JS.

| Call | Why it goes through JS |
|---|---|
| `exportPath()` | The project's texture export directory, the one the user sees and can change in Painter's Export Textures dialog. `sp.export.get_default_export_path()` returns the **application** default instead (`export.md`). Read fresh on every export, never cached. |
| `getProjectExportPreset()` | Python can list export presets but cannot read the one stored on the project. |
| `channelIdentifiers(stackPath)` | Stack-level used channel identifiers, including resolved user-channel labels where the host reports them. |
| `documentStructure()` | `materials[].stacks[].channels`, a second source for the same identifiers. |

Side effects / concerns:
- `sp.js.evaluate` returns a **JSON-formatted string**; parse accordingly.
- Errors surface as Python `RuntimeError` with JS stack trace as message
- Path escaping: use `json.dumps()` on every path to handle backslashes and
  quotes safely
- JS engine is single-threaded and blocking — each `evaluate` call yields
  synchronously

---

## 4. Gaps & decisions — populated

### 4.1 Confirmed gaps

| Gap | Resolution |
|---|---|
| SP Python cannot export a single layer/mask to PNG | Painter 12.1 native stack-node texture export (`stack_node_export.py`) |
| SP Python cannot read project-level export path | Use `alg.mapexport.exportPath()` via `sp.js.evaluate` (see §2) |
| SP Python has no per-layer `last_modified` timestamp | Use channel/tile cache-key comparison or re-exported hashes for conservative conflict warnings |

### 4.2 JS fallback scope (SP side)

The four `alg.mapexport` queries in §2, and nothing else. All traversal,
blend modes, effects, masks, layer-stack mutation, UI, events, and logging
are Python-native.

---

## 5. Open questions

- **Current Painter normal-map orientation getter**: `NormalMapFormat` is
  documented for project creation settings, but no direct getter for the
  currently opened project was found in the local `project.md`. Store the
  value when known, infer from existing normal sources if possible, or expose
  a user setting.

---

## 6. Color management deep dive (SP side)

Source: `reference-docs/pt-python-doc-md/substance_painter/colormanagement.md` +
`source/bitmap.md`.

### 6.1 Color space model in SP

| Space | When used | Enum |
|---|---|---|
| sRGB | Color-managed channels on output (BaseColor, Emissive, Diffuse, Specular, CoatColor, ScatterColor, SheenColor) | `GenericColorSpace.sRGB` |
| Working (Linear sRGB in legacy) | **Layer blending happens here** | `GenericColorSpace.Working` |
| Raw | Data channels (Roughness, Metallic, Height, Displacement, AO, Opacity, Glossiness, Anisotropy, IoR, Specularlevel, user channels) | `GenericColorSpace.Raw` / `DataColorSpace.Data` |
| Normal | Normal channel, depends on project OpenGL/DirectX | `NormalColorSpace.NormalXYZRight` / `...Left` |

An exported layer PNG is:
- Color-managed channel → **sRGB-encoded** (gamma ~2.2)
- Data channel → **raw** (no conversion)
- Normal channel → raw in the project's normal orientation

### 6.2 Measured blend behavior (2026-09-30)

Painter's documentation states that all blend modes run in linear space. This
was measured directly, which also pins down each formula. Method:

- A temporary Painter instance built a plane project whose base fill is a
  horizontal 0..255 ramp and whose top fill is a vertical ramp, so one texture
  covers every (backdrop, layer) pair. A second pair of hue/value sweeps
  covered the HSV modes. Every Painter mode was exported at 100% and 50%
  opacity as a 16-bit BaseColor PNG.
- Photoshop 26.1 rebuilt the same two layers in scratch documents through
  COM, for every Photoshop mode and both opacities, in three variants: a
  default sRGB document, a 16-bit linear (gamma 1.0) document, and a default
  sRGB document with "Blend RGB Colors Using Gamma 1.0" switched on by hand
  and restored afterwards.

Results (maximum error in 8-bit levels against Painter):

| Mode | sRGB PSD | Linear 16-bit PSD | sRGB + gamma 1.0 setting |
|---|---|---|---|
| Normal 50% | 60 | 1.1 | 1.1 |
| Multiply 100% / 50% | 8 / 60 | 0.9 / 1.1 | 8 / 2.5 |
| Screen 100% | 27 | 0.9 | 27 |
| Overlay 100% / 50% | 118 / 38 | 0.9 / 1.0 | 118 / 51 |
| ColorDodge 100% / 50% | 202 / 96 | 1.0 / 1.0 | 202 / 151 |
| Other RGB modes 100% | 65 to 244 | 0.9 (4.4 on isolated divide-by-zero pixels) | same as sRGB |
| SoftLight 100% | 37 | 38 | 37 |

The ~1 level floor comes from the 8-bit test inputs. Conclusions:

- **Every Painter RGB mode is its standard formula applied to linear values**,
  mixed with the backdrop by coverage in linear space:
  `out = enc((1 - a) * lin(B) + a * f(lin(B), lin(C)))`, clamped to 0..1.
  Overlay is backdrop-keyed and HardLight layer-keyed, exactly as in
  Photoshop. SignedAddition is `b + 2c - 1`, identical to LinearLight.
  InverseDivide is `c / b`, InverseSubtract `c - b`.
- **SoftLight** is `b + (2c - 1)(sqrt(b) - b)` for `c > 0.5` and
  `b - (1 - 2c) b (1 - b)` otherwise; Photoshop's SoftLight is a different
  curve, so no document setting makes them agree.
- **Tint, Saturation, Color, Value** replace HSV components of the linear
  backdrop with the layer's (hue; saturation; hue and saturation; value) and
  then **double the value**, clamped. The doubling is reproducible across
  every sample (ratio 2.000); Photoshop's Hue/Saturation/Color/Luminosity use a
  luminosity model and cannot match.
- **"Blend RGB Colors Using Gamma 1.0" only linearizes the coverage mix.**
  Blend formulas still run on sRGB values, so it fixes Normal, Darken and
  Lighten edges and nothing else, and makes some partially covered modes
  worse. It is application-wide and not stored in the PSD.
- **A linear-profile PSD matches**, but Photoshop 26.1 still shows the old
  user complaints: a typed hex `808080` is stored as linear 128 (displayed as
  sRGB ~188), and Save As TGA writes the linear values with no profile, so
  engines read them dark. CSP reads PSDs only up to 8-bit.

Data channels are raw in both apps, so only the formula differences (SoftLight,
HSV, Inverse modes, normal-map modes) apply to them.

### 6.3 Pixel rewrite for sRGB PSDs

With the backdrop known, a layer can be given pixels that reproduce Painter
under Photoshop's sRGB blending (`design.md §4`). Notation: `B` backdrop,
`T` Painter's result, both sRGB; `a` Painter coverage (pixel alpha x mask x
opacity); `C` layer color; `lin` / `enc` the sRGB transfer functions.

- **Normal** (and Darken/Lighten where the layer wins): Photoshop gives
  `(1 - A) B + A F`. Solve for the smallest `A >= a` that keeps
  `F = B + (T - B) / A` inside 0..1 on every channel. Keeping `A = a` and
  clamping `F` leaves errors up to 60 levels on 9-16% of soft-edge pairs
  (dark backdrop under a light layer); raising `A` is exact and needs at most
  about 3.5x the original coverage.
- **Multiply** is gamma-invariant for a pure power curve, so the backdrop
  drops out: `C' = 1 - (1 - enc(1 - a + a lin(C))) / a` at the original
  coverage. Residual error is at most ~8 levels, from the linear toe of the
  sRGB curve. **Divide** follows the same pattern.
- **Every other mode** has no backdrop-independent rewrite (Normal's best
  backdrop-independent fit still misses by 24-35 levels), so Match Painter
  look writes `T` as a Normal layer over the known backdrop.
- **Backdrop alpha**: the bottom of a stack and isolated groups start
  transparent, so the compositor tracks premultiplied alpha in both spaces.
  Over a partly transparent backdrop (0 < alpha < 1) Photoshop's result
  alpha fixes the layer's coverage, so the color solve has no freedom left
  and can clip. It is exact wherever what lies below a layer is opaque; in
  texture PSDs a partly transparent composite occurs only around the bottom
  layers' soft edges, outside an opaque base.
- **Groups and masks** (measured the same way, all within ~1 level):
  - A Normal-mode group is isolated: its children composite against a
    transparent backdrop, so a Multiply or Screen child there shows its own
    color, and the group result then composites by coverage. Photoshop Normal
    groups behave the same way, only in sRGB.
  - A Pass Through group lets children blend with what is below it; its
    opacity mixes the group result with that backdrop.
  - A group's own blend mode (e.g. Multiply) applies to its composite.
  - Masks are raw coverage values, multiplied with opacity like any coverage.
  - An empty stack is transparent: a Multiply layer over nothing shows its own
    color. The export flattens what stays transparent over the channel's
    default color (BaseColor: sRGB 231).

Painter's bundled Python has no numpy, so the compositor and rewrite belong in
the native library that already hosts edge smoothing (`native/`).

### 6.4 Color space of an imported PNG

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
    # store it with the export or ask the user if it cannot be inferred.
    fmt = manifest["normal_map_format"]
    cs = (sp.colormanagement.NormalColorSpace.NormalXYZRight
          if fmt == sp.project.NormalMapFormat.OpenGL
          else sp.colormanagement.NormalColorSpace.NormalXYZLeft)
    source_bitmap.set_color_space(cs)
```

The transfer manifest names the target channel, so the importer knows which
case applies.

### 6.5 OCIO / ACE projects

Projects with `OCIO` or `PAINTER_ACE_CONFIG` env vars set use custom
color management. `Working` means whatever the config defines — not
guaranteed to be Linear sRGB.

**Phase 1 scope**: assume Legacy color management (Linear sRGB working
space). Document this assumption and emit a warning at export time if the
project uses OCIO/ACE. Full OCIO support can come in Phase 2.

---

## 8. Old plugin findings (v1.1.8) — reusable patterns

Source: `reference-docs/ps-export_Rizum v1.1.8/ps-export-Rizum/`. The old
plugin is JS/QML on the SP side and ExtendScript (.jsx) on the PS side.

### 8.1 PS-side ExtendScript recipes

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

### 8.2 Documented bugs to avoid regressing

- Old plugin's blend-mode `switch` drops **`Darken`, `Lighten`, `Inverse
  divide`, `Inverse Subtract`, `Tint`, `Value`, `Signed addition`** as
  `blendingMode = ""` — i.e. silently omits the entire `blendMode` set
  line, leaving PS at its default `NORMAL`. `blend_map.py` covers all of
  these (`design.md §4.1`).
- Old plugin mutates `app.preferences.rulerUnits`, `typeUnits`,
  `displayDialogs` globally. The current JSX scripts save and restore
  `displayDialogs` around their work.

---

## 9. Build request contract

Painter first traverses the open project into request-preview JSON
(`request_type: "preview"`). It has the shape of the build request (§9.2)
but names no PNG files.

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

### 9.1 Bake decision fields

Each layer/effect record also carries pure metadata decisions:

| Field | Meaning |
|---|---|
| `bake_policy` | `keep_editable`, `bake`, `hidden`, or `no_blending` |
| `sync_direction` | `both`, `sp_to_ps_only`, or `none` |
| `ps_blend_mode` | Photoshop blend mode for the relevant channel/mask, if any |
| `warnings` | Human-readable limitations, e.g. approximate mapping or unsupported blend mode |

Which modes stay editable, are converted or are baked follows the Blend modes
setting (`design.md §4.1`); `blend_map.py` makes the decision.

### 9.2 Build bundle contract

Painter writes one bundle per texture-set/stack/channel/UDIM request:

```text
<bundle>/
  build_request.json
  png/
    uid_<uid>.png
    uid_<uid>_mask.png
    uid_<uid>_geometry_mask.png
```

`build_request.json` is the preview request promoted to
`request_type: "build"` with these additional fields:

- `build_request_file`: absolute path to the JSON file.
- `asset_dir`: absolute path to the `png/` directory.
- `psd_file`: absolute output PSD path.
- `export_settings`: resolved padding, dilation, bit depth, keep-alpha, and
  per-UDIM resolution values for the stack-node export.
- Per-node `asset` entries for editable or baked pixel payloads.
- Per-node `mask_asset` entries when a layer has an enabled mask.

PNG payloads are written by the stack-node export (`stack_node_export.py`);
target discovery also uses `alg.mapexport.channelIdentifiers` to hide unused
stack channels.

`build_request.json` keeps the Python-facing channel name (for example
`BaseColor`) and also stores `channel_identifier` (for example `basecolor`),
the identifier Painter's map export reports, which for a user channel can be
its label rather than the Python enum name.

## 10. Desktop runtime direction

The desktop bridge is now a GPUiX application using Bun, strict TypeScript,
React 19, and an exact-pinned `@gpuix/react`. GPUiX supplies the GPUI native
renderer; direct GPUI, Electron, Tauri, WinUI, and webview implementations are
not parallel fallbacks.

### 10.1 Desktop file contracts

Per Bridge session Painter writes, in the system temp folder
(`rizum-pt-bridge/<project>/`):

- `painter_snapshot.json` (`request_type: "painter_snapshot"`,
  `schema_version: 1`): the project, Painter's active context, the Photoshop
  blend modes Painter imports as they are, and one context per texture set /
  stack / channel with its layer tree. Opacities are percentages.
- `photoshop_documents.json` (`schema_version: 1`): which PSD each context
  uses.

The mapper reads the connected PSD itself. On Apply it writes
`desktop_transfer.json` (`request_type: "desktop_transfer"`,
`schema_version: 3`) there and names it in its Apply request
(`desktop/README.md`); nothing watches the folder. Each transfer holds:

- `direction`, and an `insertion` of `before`, `after` or `inside`;
- `source` and `target` with `host`, `id`, `kind`, `name` and `path`, plus
  `index_path` for Photoshop layers. `path` joins the names from the root
  with "/"; a name may contain "/" itself ("Hue/Saturation 1"), so `name`
  carries the layer's own name;
- for a Photoshop source, the PNG files the mapper rendered into
  `photoshop_assets/`, or a `color` for a solid fill, and `children` for a
  folder;
- `replace`, when Apply deletes the target once the row is in place.
