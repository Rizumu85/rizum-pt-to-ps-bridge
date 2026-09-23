# UXP Photoshop Plugin Design

Archived from `design.md` when the UXP panel was removed in favor of
Painter-driven ExtendScript automation.

## 2. Photoshop plugin distribution

Must install on **any Photoshop ≥ 23.3 regardless of Creative Cloud status,
Adobe ID, or license legitimacy.**

Method: unpacked UXP plugin folder written directly into
`%APPDATA%\Adobe\UXP\Plugins\External\` (Windows) or
`~/Library/Application Support/Adobe/UXP/Plugins/External/` (macOS). The
current Windows offline path also upserts
`%APPDATA%\Adobe\UXP\PluginsInfo\v1\PS.json`, based on the user's existing
installed external plugins.

API-doc caveat: the local UXP docs emphasize loading development plugins via
the UXP Developer Tool and packaging/distribution workflows. They do not
document the offline `Plugins/External` + `PluginsInfo\v1\PS.json`
registration path. Keep this installer approach as a Phase 1 requirement, but
validate it on target Photoshop versions before treating it as guaranteed.

Current local test path: use UXP Developer Tool's "Add Plugin" flow and select
`ps_plugin/manifest.json`. This is the documented development workflow and is
independent from the Painter plugin's root loader.

Offline local test path on this Windows machine: copy `ps_plugin/` into
`%APPDATA%\Adobe\UXP\Plugins\External\com.rizum.pt-to-ps-bridge` and upsert an
enabled UXP entry into `%APPDATA%\Adobe\UXP\PluginsInfo\v1\PS.json`. This was
derived from existing installed plugins on the user's machine and must still be
validated by restarting Photoshop and checking the Plugins menu.

Ship a `.zip` release containing:

```
rizum-pt-to-ps-bridge-vX.Y.Z.zip
├── __init__.py                        # local root Painter loader shim
├── rizum_pt_to_ps_bridge.py           # importable Painter loader shim
├── plugin.json                        # Painter plugin metadata at root
├── sp_plugin/rizum_sp_to_ps/          # Painter implementation package
├── ps_plugin/                         # unpacked UXP plugin
├── install-ps-plugin-windows.bat
├── install-ps-plugin-mac.sh
├── uninstall-ps-plugin-windows.bat
├── uninstall-ps-plugin-mac.sh
└── README.md
```

Optional later: add `.ccx` packaging for CC-enabled users (not Phase 1).

---

### 6.1 Photoshop export controls

The Photoshop panel exposes two explicit export actions:

- **Export Selected (Applied Mask)**: writes one PNG per selected Photoshop
  layer. The current layer pixels are exported with the layer mask applied.
- **Export Selected + Masks**: writes a layer PNG and, when the layer has a
  user mask, a separate grayscale mask PNG. The layer PNG is intended to be the
  unmasked layer content; the mask PNG is intended for manual mask handling in
  Painter.

The user chooses the output folder through UXP local file storage. Filenames are
simple, human-readable, and prefixed with the selection order, for example
`01_Layer_Name.png`, `01_Layer_Name_layer.png`, and
`01_Layer_Name_mask.png`.

### 6.2 API contract

The manual export path uses documented Photoshop/UXP APIs already present in
the local docs:

- `Document.activeLayers` to read the selected Photoshop layers.
- `core.executeAsModal` for document-mutating or document-reading operations
  that the Photoshop host requires to run in modal scope.
- `imaging.getPixels` to read rendered layer pixels.
- `imaging.getLayerMask` to read user-mask pixels when present.
- `Layer.layerMaskDensity` as the best available way to temporarily disable a
  mask while exporting separate layer content, then restore it.
- `storage.localFileSystem.getFolder()` and `Folder.createFile()` for the
  user-selected destination.
- A temporary transparent document plus `Document.saveAs.png()` to write PNG
  files from Photoshop image data.

## 9. M2 UXP request intake slice

M2 starts with a deliberately small Photoshop-side validation slice before PSD
construction. The UXP panel's **Build from Painter** button opens a
`build_request.json` file picker, reads the selected file through UXP local file
storage, validates the M1 build request shape, and displays a summary:

- texture set, stack, channel, UDIM
- output PSD path
- top-level layer count
- referenced PNG asset count

This validates Photoshop plugin loading, `fullAccess` file picker behavior, and
JSON contract compatibility before adding document mutation, PNG placement,
layer grouping, masks, and sidecar writing.

The panel shell must render its minimal controls from static HTML first, then
bind behavior from JS. This prevents a blank panel when the offline host fails
early during `entrypoints.setup` or local module loading; failures should show
inside the panel status/details area instead. `entrypoints.setup` itself must
still be called immediately at plugin startup because the local UXP docs flag
delayed setup as unreliable.

For the user's offline Photoshop validation path, the panel can use a Manifest
v4 compatibility build with `main: "src/main.js"` and `host.minVersion:
"22.0.0"`. The JS entrypoint renders the entire minimal UI into the panel root
node. This keeps the test panel compatible with Photoshop 2021-style UXP while
the v5 lifecycle behavior remains unverified on the offline host.

The official Photoshop starter plugin uses `main: "index.html"` and static
panel body markup before JS behavior is layered on. For diagnosing the user's
offline Photoshop host, prefer that pattern first: a static, no-script panel
should render before any UXP lifecycle or module-loading code is reintroduced.
If Photoshop 2025 registers the plugin but leaves that static body blank, keep
`main: "index.html"` but load one small startup script that immediately calls
`entrypoints.setup` and renders into the provided panel root node. That keeps
the boot path official-doc shaped while testing the explicit panel lifecycle.
If logs prove `panel.create/show` are firing but the panel remains visually
blank, avoid `innerHTML` for the diagnostic shell and build the panel with
direct DOM APIs plus Spectrum UXP elements. This keeps the UI path closer to
Adobe's supported component set and removes HTML parser/style injection as a
variable.

The `0.1.6` command diagnostic confirmed that Photoshop executes the plugin
JavaScript and can show alerts when `featureFlags.enableAlerts` is enabled.
Because the panel still appears blank, the next diagnostic should stop relying
on only Spectrum elements or only the panel lifecycle. Version `0.1.7` renders
the same plain, high-contrast HTML controls from plugin startup, panel
`create/show`, and the command handler. If the command can force visible
content into `document.body` but the docked panel stays blank, the issue is
specific to Photoshop's panel root/lifecycle surface rather than plugin
registration or JavaScript execution.

The `0.1.7` panel was confirmed visible in Photoshop 2025. Continue M2 from the
plain HTML panel shell, with direct DOM updates and explicit inline or local
CSS. Defer Spectrum components until after the request-validation and PSD-build
paths are stable.

The `0.1.8` request-intake panel keeps that shell and makes **Build from
Painter** validate a selected `build_request.json`. This is the last
Photoshop-side validation step before document mutation: file picker access,
JSON parsing, schema checks, recursive asset counting, and user-visible
summary must work before PSD creation is reintroduced.

The panel does not include a restart control. UXP does not provide a reliable
safe host-restart API for this workflow, and a non-executable helper button
adds clutter without advancing the bridge.

Photoshop 2025 resolves CommonJS modules loaded from the HTML panel relative
to the plugin document/root in this setup, so panel code should require local
modules with root-relative plugin paths such as `./src/build-psd.js`. The panel
also needs explicit vertical scrolling because docked panel height can be
smaller than the request summary.

Version `0.1.9` follows that rule and keeps a fallback require path for any
runtime that resolves relative to `src/main.js`.

If Photoshop locks the panel to manifest dimensions, size changes should be
made in `manifest.json` first. The panel should request a taller minimum and
preferred height, while the HTML shell remains scrollable so the UI still works
when Photoshop clamps the docked panel smaller than requested.

Version `0.1.10` sets the UXP panel minimum height to `560`, preferred docked
height to `720`, and preferred floating height to `760`.

The first PSD-building slice creates a transparent RGB document using the
validated request resolution and request-derived document name. It runs inside
Photoshop `executeAsModal` and intentionally stops before PNG placement, layer
groups, masks, blend modes, suffix metadata, or sidecar writing. This isolates
the Photoshop document-mutation path from the larger layer-construction work.

Do not automatically run Photoshop's `rgbColorBlendGamma = 1.0` `Set`
descriptor during normal PSD construction. Host validation showed this can
surface a modal "Set is not currently available" error even when JS does not
report a normal exception. Color-gamma handling should remain an explicit
diagnostic/calibration task until a host-safe descriptor is validated.

When the request includes an absolute `psd_file`, the plugin may attempt to
resolve it through UXP filesystem URL access and call `document.saveAs.psd`.
Because that absolute-path behavior is not fully documented in the local UXP
reference and may fail when the file does not yet exist, a failed save is not a
build failure for this slice. The panel should report "document created,
unsaved" with the exact save error so the next filesystem slice can fix the
path-entry strategy without blocking document-creation validation.

For Photoshop-host diagnostics, the details area should be copy-friendly. Use a
readonly selectable text area instead of a plain `<pre>` block, and provide a
small `Copy Details` action backed by UXP clipboard access. This keeps host
error reporting lightweight and avoids forcing screenshots for long filesystem
or API errors.

Saving a new PSD at the request path should use UXP's file-entry creation API,
not lookup. `localFileSystem.getEntryWithUrl` is suitable for existing files
only; for a new output PSD, resolve the request path to a `file:` URL and call
`localFileSystem.createEntryWithUrl(url, { overwrite: true })`, then pass the
returned File entry to `document.saveAs.psd`.

The first PNG placement slice stays deliberately narrow. After creating the
transparent document, Photoshop opens each top-level request node that has a
direct `asset.path`, duplicates the opened PNG's first layer into the target
PSD, applies the request layer name, visibility, and opacity, closes the
temporary PNG document without saving, and then saves the PSD. It does not yet
build Photoshop groups, masks, clipping sub-effects, blend modes, layer-name
metadata suffixes, or sidecar JSON. Those remain part of the broader M2 layer
construction step after this top-level raster path is validated in-host.

## Former UXP Sidecar Schema

UXP has no reliable per-layer XMP metadata API (see `analysis.md §3.10`), so
Phase 1 keeps durable metadata in the sidecar JSON instead of visible Photoshop
layer names.

### 7.1 Photoshop layer names

Plugin-created Photoshop layers and groups should use clean user-facing names,
without visible ` [rz:<uid>]` suffixes. The earlier automatic sync-back
prototype used layer-name suffixes for matching, but the active Phase 1 return
workflow is manual PNG export and no longer needs that visible key.

The sidecar remains the provenance record for `sp_uid`, source asset path,
mask path, blend mode, clipping state, and other build metadata.

### 7.2 Sidecar JSON

Next to the PSD, one file per PSD: `<psdname>.rizum.json`.

```json
{
  "rizum_version": "2.0.0",
  "sp_project_path": "C:/.../project.spp",
  "sp_project_uuid": "<str(sp.project.get_uuid())>",
  "baseline_timestamp": "ISO-8601",
  "texture_set": "Body",
  "stack": "",
  "channel": "BaseColor",
  "udim": 1001,
  "normal_map_format": "OpenGL",
  "baseline_cache_key": 123456789,
  "layers": [
    {
      "sp_uid": "a3f7",
      "sp_kind": "layer",
      "sync_direction": "both",
      "ps_name": "DiffuseBase ‡a3f7",
      "baseline_hash": "sha1:..."
    },
    {
      "sp_uid": "b912",
      "sp_kind": "baked_effect",
      "sync_direction": "sp_to_ps_only",
      "ps_name": "[baked] Tint_Layer ‡b912",
      "baseline_hash": "sha1:..."
    }
  ]
}
```

`sp_kind` values: `layer`, `fill_effect`, `paint_effect`, `baked_effect`,
`flattened_mask`. ("anchor_ref" merged into `baked_effect` per `design.md §5.4`.)

`baked_effect` entries get `sync_direction: "sp_to_ps_only"` — UXP panel
renders them as "cannot sync" entries.

`baseline_hash` is the SHA1 of the PNG exported from SP when the PSD was
originally built. It was used by the deprecated automatic push preview to detect
changed Photoshop pixels. The active manual return export does not require it.

The sidecar also has `unplaced_nodes` for request nodes that were not created
as Photoshop layers. The current use is mask-stack/content-effect metadata that
has already been baked into a parent raster or mask PNG.

`texture_set`, `stack`, `channel`, `udim`, and `normal_map_format` remain in
the PSD sidecar for provenance and future automation. There is no active push
manifest in the Phase 1 manual return workflow.

## Former analysis.md §3

Source: `uxp-photoshop-main/src/pages/ps_reference/` + `uxp-api/reference-js/`
+ `guides/uxp_guide/`.

Entry point: `const { app, action, core, constants } = require('photoshop');`

### 3.1 Minimum Photoshop version

Manifest v5 requires **Photoshop ≥ 23.3** (UXP ≥ 6.0). Keep
`manifest.host.minVersion = "23.3.0"`, but avoid DOM conveniences introduced
after 23.3 unless guarded. In particular, `Document.createPixelLayer()` is
documented as 24.1, so Phase 1 should use the older `Document.createLayer()`
pixel-layer overload when it needs a blank raster layer.

This revises `design.md §2` which said "PS ≥ 23"; update to 23.3.

### 3.2 PSD creation & save — ✅ covered

| Need | API |
|---|---|
| New doc | `await app.createDocument({width, height, resolution, depth, mode: "RGBColorMode", fill: "transparent"})` |
| Open existing | `await app.open(fileEntry)` — takes UXP File entry |
| Save PSD | `await doc.saveAs.psd(fileEntry, {embedColorProfile: true}, false)` |
| Save current | `await doc.save()` |
| Close | `await doc.close(SaveOptions.DONOTSAVECHANGES)` |

Color mode: `"RGBColorMode"` (default). Bit depth should be set at document
creation with `DocumentCreateOptions.depth` (`8`, `16`, or `32`); `doc.bitsPerChannel`
is also writable but setting the depth up front is cleaner.

### 3.3 Layer creation & arrangement — ✅ covered via high-level DOM

| Need | API |
|---|---|
| New raster layer | `await doc.createLayer(constants.LayerKind.NORMAL, {name, opacity, blendMode})` (23.0); `doc.createPixelLayer()` exists but requires 24.1 |
| New group | `await doc.createLayerGroup({name, opacity, blendMode, fromLayers})` |
| Group existing | `await doc.groupLayers([layer1, layer2])` |
| Duplicate / move across doc | `await layer.duplicate(targetDoc)` |
| Reorder | `layer.move(relativeLayer, ElementPlacement.PLACEBEFORE\|PLACEAFTER\|PLACEINSIDE\|PLACEATBEGINNING\|PLACEATEND)` |
| Delete | `layer.delete()` |
| Visibility | `layer.visible = bool` |
| Opacity / fill | `layer.opacity = 0–100`, `layer.fillOpacity = 0–100` (percent numbers) |
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
pngDoc.closeWithoutSaving();
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

`manifest.requiredPermissions.localFileSystem = "fullAccess"` is the intended
permission for arbitrary project-path access. The included manifest v5 docs
state that `fullAccess` allows inspecting/modifying/deleting accessible files,
with install/update consent.

Use the UXP native filesystem APIs:
```javascript
const fs = require('uxp').storage.localFileSystem;
const entry = await fs.getEntryWithUrl("file:" + absolutePath);   // needs fullAccess
await entry.write(data);
// or getFileForOpening() / getFileForSaving() for user pickers
```

The local docs do **not** document Node-style `require('fs')` as a Photoshop
plugin API. Do not make it the primary implementation path. `getEntryWithUrl`
is referenced in the local UXP changelog but its concrete generated reference
page is not expanded in this repo, so M4 must validate it in-host. Use
`getFileForOpening()` for the initial "pick a build_request.json" action and
UXP File/Folder entry APIs for manifest and PNG I/O where possible. `.write()`
is shown in the included guides; `.read()` and URL-based entry lookup should
be validated in-host because their generated reference pages are placeholders
in this repo.

SHA1/hash: use the plugin's local pure JavaScript SHA-1 helper. Do not depend
on Web Crypto because the user's Photoshop UXP runtime does not expose
`crypto.subtle.digest`.

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

History suspension: `doc.suspendHistory(cb, historyStateName)` OR
`ctx.hostControl.suspendHistory({documentID, name})` followed by
`ctx.hostControl.resumeHistory(suspensionID, true)` inside modal scope —
collapses all our mutations into one undoable step.

### 3.10 Metadata — ⚠ revised: layer-name suffix + sidecar JSON

The local docs mention XMP support in the UXP changelog, but the generated
XMP reference pages in this repo are placeholders. Per-layer XMP is not
exposed in the high-level Photoshop DOM. `batchPlay` can potentially poke
layer metadata, but that path is fragile across PS versions.

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
    "sp_project_uuid": "<str(sp.project.get_uuid())>",
    "baseline_timestamp": "ISO-8601",
    "texture_set": "Body",
    "stack": "",
    "channel": "BaseColor",
    "udim": 1001,
    "normal_map_format": "OpenGL",
    "baseline_cache_key": 123456789,
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
  key; sidecar JSON is cross-reference to detect renames/duplicates and to
  carry channel/UDIM/normal-orientation context that is not recoverable from
  an arbitrary edited PSD layer.

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
