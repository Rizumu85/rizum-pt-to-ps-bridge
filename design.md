# Rizum PT-to-PS Bridge — Design Decisions

## Project Goal

Build a two-plugin bridge between Substance 3D Painter and Photoshop that turns
Painter texture stacks into editable PSDs while preserving as much layer
structure, blend behavior, channel context, UDIM layout, and color fidelity as
the two hosts allow. Photoshop-to-Painter return data is intentionally manual in
Phase 1: Photoshop exports user-selected layers or layer/mask PNG pairs, and the
user imports those files into Painter through Painter's normal workflows.

Source of truth for design choices agreed in the pre-implementation discussion.
Subject to revision only if `analysis.md` later reveals an API constraint that
makes one of these infeasible — otherwise these are locked.

This document owns user-facing behavior, workflow shape, UI expectations, and
design tradeoffs. Low-level API findings belong in `analysis.md`; implementation
directions and concrete steps belong in `plan.md`.

API-doc status: revised against the local SP Python docs, legacy SP JS docs,
and Photoshop UXP docs listed in `analysis.md §0`. The remaining uncertainties
are host-recorded `batchPlay` descriptors and live host validation, not missing
documentation in the repo.

Local development note: this repository is placed directly in Painter's Python
plugin directory as `rizum-pt-to-ps-bridge`. The root therefore contains
Painter loader shims that delegate to `sp_plugin/rizum_sp_to_ps/`, because the
hyphenated project folder is not a valid Python module name by itself.

Painter startup must stay project-agnostic. The plugin can be enabled when
Painter has no open project, so startup should only create/register UI. Any
texture-set, stack, layer, or export-path query belongs behind a user action or
project-ready check, and the panel should show a no-project state until
`substance_painter.project.is_open()` is true.

The Painter panel must not run periodic timers, inbox watchers, automatic
project scans, or background refresh while the user paints. User host feedback
showed that even lightweight UI polling can correlate with brush-time freezes
or crashes. Button state and project readiness should be checked only when the
user clicks an action.

The Painter dock now exposes three action buttons only: **Export**, **Bridge**,
and **Settings**. The dock title comes from Painter's native dock title bar. A
no-project message such as "Open a Painter project to export." appears only
when no project is open; when a project is ready, the dock avoids extra status
clutter.

The **Export** action opens a focused export dialog. The scope selector has two
display scopes only: the currently edited texture set/stack, or all stacks.
This selector controls what the dialog shows, not a separate hidden export
mode. The first implementation resolves **Current Stack** with
`substance_painter.textureset.get_active_stack()` and falls back to the first
available export target only if the host cannot report the active stack. The
dialog keeps group/channel checkboxes, explicit **All** and **None** actions,
and footer buttons with large rounded proportions matching Photoshop-style
inner panels. **All** means "click to select all"; **None** means "click to
deselect all". Do not include extra eye/filter icons until those actions have
real behavior.

Export dialog groups should not auto-expand on hover; expansion is an explicit
row/arrow action. Bridge app layer rows should follow the desktop-reference
behavior: rows and groups are visually quiet by default, with their rounded
card container and remove control appearing only on hover or drag. Layer
descriptions in the bridge app should use two lines, with the primary name
above secondary metadata such as layer count, blend mode, opacity, or mask
state. Masked layers should show a visible mask badge or paired thumbnail so
the user can tell which rows have separate mask data.
The export dialog uses the same hover hierarchy: hovering a stack shows the
larger stack container, while hovering an individual channel also shows that
channel's smaller row container.

The desktop bridge app should not require one large outer card around both
hosts. A transparent shell with two independent host cards is preferred because
the Photoshop source list may be short while the Substance Painter target tree
may be much taller. The insertion target should be a clear horizontal drop line
inside the Painter card. Photoshop and Painter may therefore use different card
heights in the same transfer view: the Photoshop source side can shrink after
layers are moved, while the Painter target side can remain tall enough for a
larger layer tree. Each host card header should use a compact logo plus two
text lines: host name first, then the active PSD or texture-set/channel context.

The settings panel should be quieter than the current draft: use section
separators and compact controls rather than many nested outlined cards. If
padding is set to Infinite, the dilation control should disappear because it is
not applicable. Automatic Photoshop build should remain the default behavior
for Workflow A when the Photoshop path is configured; it does not need a
prominent visible setting in the first mockup.
The first implemented Painter settings dialog stores machine-level settings via
Qt `QSettings`: Photoshop executable path, infinite padding, and an optional
8/16-bit export override. When bit depth is left as **Texture Set**, exports use
the channel's native bit depth from Painter.
Painter-wide UI scaling belongs in a separate helper plugin, not the PT Bridge
settings panel. The bridge may coexist with that helper, but should not own
global Painter UI scale experiments.

The visual mockup should prefer MiSans when it is available on the user's
machine. Most UI text should use 13px/600, Painter dock action labels should
use 10px/500, secondary metadata should use 11px/400, and the mockup may expose
a small live font-size control while the final type scale is being tuned.

Painter build bundles should no longer default to the repository-local smoke
test directory during normal use. The panel resolves Painter's project export
path through the JS `alg.mapexport.exportPath()` fallback and writes bundles to
`<exportPath>/<project>_photoshop_export/`. After export, the panel should let
the user copy the last `build_request.json` path, copy the last export-list
path, and open the output folder.

The Photoshop panel should support both the file picker and a direct
`build_request.json` path. The direct-path flow pairs with Painter's **Copy
Last Request Path** button: the user can click **Paste Request Path** in
Photoshop when UXP clipboard reading is available, or paste into the path field
manually, then click **Build Request Path**.

For larger Painter exports, the Photoshop panel should also provide **Build
Request Folder**. The user chooses a folder such as `<project>_photoshop_export`;
the panel recursively finds `build_request.json` files, builds them one by one,
and closes each PSD only after it has saved successfully. Failures are reported
per request and do not stop the remaining builds.

For scoped Painter exports, the safer Photoshop batch path is **Build Export
List**. Painter writes `_last_export.json` into the export root after each run;
Photoshop reads that list and builds only the exact requests from the most
recent export, avoiding stale bundle folders left from earlier broader exports.

Workflow A can also offer a one-action **Export and Build in Photoshop** path
after the user sets the Photoshop executable path in Painter. This should follow
the old plugin's user-facing pattern but use the current UXP builder: Painter
writes the build bundles and `_last_export.json`, writes a tiny generated
`.psjs` launcher that builds that export list, then launches Photoshop with the
launcher path if host validation confirms Photoshop accepts that command-line
flow. If `.psjs` command-line launch is not reliable, keep **Build Export List**
as the supported fallback rather than reintroducing a second JSX builder.

Painter build requests should include channel semantics in addition to the raw
channel enum: a display label, a role (`color`, `data`, `opacity`, `normal`, or
`user`), format, bit depth, and color/data flag. Photoshop should show those
fields in build summaries and sidecars before any channel-specific pixel
behavior is introduced.

The Painter target picker should show user channel labels when Painter exposes
them, while keeping the raw enum channel as the internal export key. Layer PNGs
that export as fully transparent should be pruned from the request, and a
channel with no remaining layer PNGs should not write a build bundle. The
target picker and request generator should first ask Painter's legacy JS
`alg.mapexport.channelIdentifiers(stackPath)` for stack-level used channels so
entire unused channels can be hidden/skipped before per-layer PNG export.
The same resolved identifier should be written into `build_request.json` and
passed to `alg.mapexport.save`; for user channels this may be the Painter label
(`SCol`, `TNrm`, `SDF`) rather than the Python enum name (`User0`, `User1`).
For user-channel exports, Painter may try several known identifier spellings
and keep the first non-transparent result. Python `active_channels` should be
used as a pre-export filter so layers that are not active on the requested
channel do not produce misleading empty PNGs.
The preferred channel identifier source is the same one used by the old plugin:
`alg.mapexport.documentStructure().materials[].stacks[].channels`.
User channel labels should also be used in generated bundle and PSD filenames
so names such as `SCol`, `TNrm`, or `SDF` match the Painter UI.
Because Painter can under-report used channels for Fill layers that reference
external maps, `active_channels` from Python traversal is also treated as a
positive target-discovery signal. JS used-channel data can hide clearly unused
channels, but it should not suppress a channel that a layer explicitly marks
active.
The selected-stack export button should reuse the same refreshed channel list
shown in the UI, rather than doing an unfiltered second scan. This keeps
"Export Selected Target" and "Export Selected Stack" consistent when host
channel discovery is imperfect.
Host testing confirmed this target-discovery design for both single-channel
and selected-stack export on the current Wings reference-map case.
For per-layer user-channel PNG export, the request-level engine identifier is
the primary export string, and documented fallbacks such as `user1`, `user 1`,
and the custom channel label are tried only if the primary string produces an
empty result or fails. This keeps old-plugin-compatible strings first without
making the exporter depend on one user-channel spelling.

Photoshop should leave PSDs open when building from `_last_export.json`, so the
user can inspect the small scoped batch immediately after creation. Large
recursive folder builds may still close after save to avoid opening too many
documents.

Phase 2 may add a desktop bridge app as a visual transfer queue. The app should
connect to both host plugins through local interchange folders, show Photoshop
and Painter layer trees side by side, and let the user drag selected exported
layers onto a target group/layer insertion position. Hover feedback should show
the target position clearly: group highlights for inserting into a group, and
thin insertion indicators for placing before/after a layer. The app writes a
manifest; the destination plugin applies it only after the user confirms.

The desktop app should own path setup, recent projects, transfer presets, and
manual placement decisions. It should not hide automatic background sync behind
the UI. Partial export/import remains explicit: source plugin exports selected
layers, desktop app maps them, target plugin applies the selected manifest.

The Painter dock panel must also keep a module-level strong reference to its
Python panel object. Painter owns the dock widget after `sp.ui.add_dock_widget`,
but the Python object still owns timers, slots, and child-widget references; if
that object is garbage-collected, the dock can remain while its contents or
handlers disappear.

Photoshop local development is separate from Painter loading. Photoshop will
not scan this Painter plugin directory for UXP panels. For local testing, load
`ps_plugin/manifest.json` through Adobe UXP Developer Tool, then open the panel
from Photoshop's Plugins menu as `Rizum PT Bridge`.

---

## 1. Architecture split

| Side | Language | Framework |
|---|---|---|
| Substance Painter plugin | **Python** (SP Python API) | PySide6 for UI |
| Photoshop plugin | **UXP plugin** (`.ccx`/unpacked folder) | UXP JS + Spectrum Web Components |
| Transport | **File-based** (SP-to-PS uses PNG + JSON build request; PS-to-Painter manual return uses selected PNG exports) | — |

**Rule**: Python first on SP side. Fall back to the legacy SP JS API (`alg.*`)
only if a specific capability is genuinely absent from Python. JS fallback will
be invoked via `substance_painter.js.evaluate` (or equivalent) and the list of
such calls kept explicit in `analysis.md §2`.

**No sockets, no daemons, and no background polling in the active Phase 1
workflow.** The user triggers every cross-boundary action.

Painter exports should show an application-modal progress dialog while work is
running. The dialog blocks normal Painter interaction to reduce brush/viewport
operations during export, but keeps a Cancel button. Cancellation is checked
between build requests and between PNG asset writes; an in-flight host export
call may finish before cancellation takes effect.
Export actions should only start when Painter reports the project is in edition
state, not merely open. If the project is still loading or non-editable, the
panel should report that state and wait for a later user retry.

UDIM per-layer PNG export has a known API gap: the fast JS
`alg.mapexport.save` path has no per-tile filter. Non-UDIM projects should keep
that fast non-mutating path. If true per-tile per-layer UDIM output is needed,
use a future opt-in Python solo-export fallback that temporarily isolates one
node's visibility and calls Painter's normal texture export with a `uvTiles`
filter. That fallback must wrap visibility changes and export work with both
`ScopedModification` and `application.disable_engine_computations()` so Painter
does not recompute thumbnails or viewport textures after each temporary
visibility change.

Project-level bridge choices should be stored in Painter `project.Metadata`
when they belong to the current `.spp`, for example normal-map-format override,
last export preset, and last scoped target. Machine-level choices, such as a
Photoshop executable path for a future one-click build action, remain global.

`TextureStateEvent.cache_key` is a future integrity signal, not an active sync
requirement. If the bridge later needs to warn that a Painter stack changed
after PSD export, it should store cache keys per stack/channel/tile instead of
inventing a parallel dirty-state mechanism.

Normal-map orientation should be treated as unknown until it can be inferred or
set. Preferred future order: direct host setting if `alg.project.settings`
exposes it, normal-source `SourceBitmap.get_color_space()` inference when
available, then a user choice persisted in `project.Metadata`.

---

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

## 3. UDIM handling & file naming

**One PSD per UDIM tile.** Each tile's PSD has an identical layer structure
(same `rizum_sp_uid` on corresponding layers across tiles). Export progress
UI reports per tile.

### 3.1 Filename pattern — follow user's SP export preset

The plugin does **not** invent its own `MatName_Channel.psd` naming scheme.
Instead it reads the user's selected SP export preset (from
`sp.export.list_resource_export_presets()`) and reuses the preset map's
`fileName` pattern, replacing only the file extension with `.psd`.

UI: a "Naming preset" dropdown in the export dialog, defaulting to the
preset remembered from the user's last run (or SP's default if first run).
Tokens SP resolves automatically: `$project`, `$mesh`, `$textureSet`,
`$sceneMaterial`, `$udim`.

### 3.2 UDIM token insertion

If the selected preset's `fileName` pattern:
- **already contains `$udim`** → use as-is; each tile writes to the tile-
  resolved filename (e.g. `MetalDoor_BaseColor.1001.psd`,
  `MetalDoor_BaseColor.1002.psd`)
- **does not contain `$udim`** and the stack has UV tiles → plugin
  auto-appends `.$udim` immediately before the extension
  (`MetalDoor_BaseColor` → `MetalDoor_BaseColor.$udim`)
- **does not contain `$udim`** and the stack has no UV tiles → use as-is

This matches the convention Mari / Painter users already follow and keeps
generated files predictable for manual inspection and future automation.

Non-UDIM Painter projects still map internally to the default UV tile/UDIM
`1001`, but generated user-facing names should not include `1001` in that case.
The request keeps `udim: 1001` for compatibility and sets
`uv_tile.is_udim: false`; bundle folders, PSD filenames, and panel summaries use
that flag to omit the tile suffix.

### 3.3 Export path — follow SP project default

The plugin uses SP's **project-level** export path, fetched fresh at the
moment of each export via `alg.mapexport.exportPath()` (JS bridge, see
`analysis.md §2.1`). This path tracks whatever the user has configured in
Painter's Export Textures dialog and updates dynamically if they change it.
PSDs are written to `<exportPath>/<project>_photoshop_export/` (matching the
v1.1.8 layout).

The Python-side `sp.export.get_default_export_path()` returns the
**application** default, not the project-specific path — not suitable here.

No UI option to override the export path. If the user wants a different
destination they change it in Painter's normal export dialog.

### 3.4 Padding & dilation

UI exposes two knobs (same semantics as v1.1.8 but expanded range):

| Knob | UI | Passed to `alg.mapexport.save` |
|---|---|---|
| **Padding** | Checkbox "Infinite padding" (default off for PSD layer payloads) | `padding: "Infinite"` when on, `padding: "Transparent"` when off |
| **Dilation** | Slider 0-64 px, enabled only when padding is off | `dilation: <n>` |

Dilation hint in UI, right below the slider: *"Suggested: 2px for 512, 4px for 1K, 8px for 2K, 16px for 4K, 32px for 8K."*

Range rationale: v1.1.8 capped at 10 which is insufficient for 4K+ work.
64 covers 8K comfortably with headroom. Formula that matches the hints:
`suggested_dilation ~= resolution / 256`.

Bit depth stays at whatever the channel format declares
(`Channel.bit_depth()`) unless user explicitly forces 8/16 via a dropdown —
same logic as v1.1.8.

For editable Photoshop build bundles, layer PNG payloads default to transparent
padding and `keepAlpha: true`. Infinite padding remains a useful final texture
export option, but it bakes edge/background pixels into standalone layer PNGs
and is therefore not the default for PSD construction.

---

## 4. Color fidelity strategy

**Primary mechanism (new in v2)**: set the PSD's document-level
**"Blend RGB Colors Using Gamma 1.0"** when building it. PS will then
decode sRGB → linear → blend → re-encode, matching SP's linear
compositing exactly. All PS-representable linear-friendly blend modes
produce SP-identical output with **zero per-layer pre-compensation**. See
`analysis.md §6.3` for details.

**Fallback** if UXP cannot toggle this setting (to be verified at M3):
empirical per-mode pre-compensation LUT. Some blend modes in the
Overlay/SoftLight/HardLight family will have residual drift.

Adobe's public Painter support guidance aligns with this design: Painter blend
modes should mostly match Photoshop, but color-space management can produce
differences. Treat that as validation of the gamma/blend-fidelity work, not as
proof that raw Photoshop defaults are enough.

### 4.1 Default: "Bake unsupported modes" (A+B hybrid)

- PS-representable blend modes (Normal, Multiply, Screen, LinearDodge,
  LinearBurn, Darken, Lighten, ColorBurn, ColorDodge, Difference,
  Exclusion, Overlay, SoftLight, HardLight, VividLight, LinearLight,
  PinLight, Color, Saturation, PassThrough[group-only]) → kept as editable
  PS layers. Accuracy comes from the gamma 1.0 toggle above.
- SP-only modes (`SignedAddition`, `InverseDivide`, `InverseSubtract`,
  `Tint`, `Value`, `NormalMapCombine`, `NormalMapDetail`,
  `NormalMapInverseDetail`, `Replace`) → that layer **plus everything
  below it in its enclosing stack** is baked to a single Normal raster
  layer. Remaining layers above stay editable.

### 4.2 Toggle: "Preserve all layers" (B-only)

- Every SP layer → exactly one PS layer, no baking.
- Unrepresentable SP-only modes map to the closest PS equivalent (with
  `[!]` prefix in the PS layer name): `Tint` → `HUE`, `Value` →
  `LUMINOSITY`, `SignedAddition` → `LINEARDODGE`, etc. Full mapping in
  `analysis.md §3.6`.
- Explicitly accepts color drift on those specific layers.

### 4.3 Rejected: option C (rewrite SP viewport shader)

SP layer blending happens inside the Substance Engine, not in any
user-controllable shader. The view shader sees already-composited channel
textures. Impossible to rewrite from a plugin.

---

## 5. Layer structure mapping

### 5.1 Top-level layers

| SP | PS |
|---|---|
| Paint layer | Raster layer, blend mode mapped, opacity mapped |
| Fill layer | Raster layer (fill baked to PNG), blend mode mapped |
| Group/folder | PS layer group, blend mode mapped; PassThrough folder → PASS THROUGH |
| Layer mask (SP) | PS layer mask on the generated PS layer/group |

Painter layer opacity is stored in the request as the normalized host value
(`1.0` is fully opaque, `0.55` is 55%). Photoshop UXP layer opacity is a
percentage, so the Photoshop builder normalizes `0..1` values to `0..100`
right before assigning layer opacity. Values greater than `1` are preserved as
already-percent values for compatibility.

Blend mode mapping must stay per-channel. A Painter layer can have different
blend settings for BaseColor, Normal, Roughness, and other channels, so a
BaseColor PSD must use that node's BaseColor blend value rather than a generic
layer-level fallback. Group/folder blend modes must also be preserved because a
non-PassThrough group composites its children first and then blends that result
with the stack below.

The current top-level raster placement slice applies per-channel blend mode to
duplicated PNG layers only. `PASSTHROUGH` remains reserved for future group
construction and is not assigned to raster layers.

The current group slice creates Photoshop groups recursively for any group that
contains placeable raster descendants. Group `visible`, `opacity`, masks, and
per-channel blend mode are applied after child placement. This keeps nested
Painter folder hierarchy visible in Photoshop when descendants have exported
PNG payloads.

Photoshop can keep a newly-created group as the active insertion context, so
top-level raster layers are placed before groups. Completed groups are then
moved back to their Painter top-level position. This prevents unrelated
top-level layers from being inserted inside the most recently created group.
PNG children of groups are first duplicated into the target Photoshop document
and then moved into their parent group from inside the same document, because
this UXP runtime rejects direct cross-document duplication into a group. Nested
groups use the same pattern: create the group, move it into its parent group,
then place its children.

The PSD builder removes Photoshop's default empty `Layer 1` immediately after
creating the Photoshop document and before placing requested layers/groups. It
also performs a final top-level cleanup after placement, deleting a residual
default `Layer 1` only when the Painter request did not contain a real
top-level item with that name. Placement diagnostics include source PNG paths
so suspicious thumbnails can be traced back to Painter-exported payload files.

The current mask slice attaches flattened `mask_asset` PNGs to placed raster
layers through Photoshop's Imaging API: open mask PNG, read it as grayscale
image data, then call `imaging.putLayerMask()` on the target Photoshop layer.
Mask failures are reported separately and do not remove the successfully placed
pixel layer.

### 5.2 Sub-effects inside a layer's channel

For non-group raster nodes with direct `content_effects`, the desired PSD shape
is still one clipped Photoshop layer per editable SP fill/paint effect above a
base silhouette layer. Host validation showed that the current Painter JS
export call cannot target effect UIDs directly, so this shape requires a future
export strategy instead of the existing `alg.mapexport.save([uid, channel])`
path.

```
PS group "<sp_layer_name>"     (group mask = SP layer's combined mask)
  ├─ effect_n  (clipped to base, blend mode = sub-effect's blend mode)
  ├─ …
  ├─ effect_1  (clipped to base)
  └─ base      (SP layer's underlying content, silhouette source for clipping)
```

Filter/generator/level sub-effects (non-fill/paint) → baked into a static
raster sibling.

Implementation scope for Phase 1: do not export effect UIDs as standalone PNG
assets. Keep effect records in `build_request.json` and the Photoshop sidecar
as provenance/unplaced nodes, while parent layer pixels and masks continue to
use layer UID exports. Editable clipping reconstruction for Painter content
effects is intentionally abandoned for Phase 1; dedicated wrapper groups,
nested content-effect chains, and any future supported per-effect export remain
later fidelity work.

The Photoshop panel groups non-placed request nodes by severity. Expected baked
mask/effect metadata is reported separately from unsupported editable content
effects, and both are kept separate from true unplaced assets that need
attention.

### 5.3 Sub-effects inside a mask

**Flattened** to a single grayscale PNG used as the PS layer mask. PS has no
native concept of stacked mask effects. Loss of editable stack is declared in
the export report.

### 5.4 Anchor point references

Each anchor reference is **baked in place** as a regular Normal-mode raster
layer. No special locking, no hidden metadata beyond the standard
`rizum_sp_uid`. In the active Phase 1 return workflow it is simply another
Photoshop layer the user may choose to export manually.

---

## 6. Manual return export (PS to Painter)

**User-initiated and manual.** No live sync, no automatic Painter mutation, and
no `_pt_sync_inbox` apply path in Phase 1.

Host testing of the automatic inbox/apply design showed that importing 4K PNGs
as Painter project resources and inserting generated Fill layers can leave
Painter generating thumbnails, make viewport navigation unusably slow, and
crash when the generated layer is deleted. The safer Phase 1 return workflow is
therefore to export files from Photoshop and let the user place/import them in
Painter manually.

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

### 6.3 Non-goals for Phase 1 return data

The manual export path deliberately does not:

- write a push manifest;
- scan, apply, or write `_pt_sync_inbox`;
- import resources into Painter;
- mutate the Painter layer stack;
- depend on `[rz:<uid>]` suffixes, sidecar matching, hash diffing, or layer
  rename rules;
- attempt conflict detection between Photoshop edits and later Painter edits.

### 6.4 Deprecated automatic inbox design

The notes below describe the earlier automatic sync-back design that was
implemented experimentally through `0.1.46`, then superseded by the manual
export workflow above after Painter host testing showed unacceptable
performance and crash risk.

#### Historical 6.1 Push (UXP side)

UXP panel lists every PS layer tagged with `rizum_sp_uid`:

```
☑ DiffuseBase         [changed 2m ago]
☑ Scratches_Overlay   [changed 14s ago]
☐ Rust_Fill           [unchanged]
⊘ [!baked] anchor_L3  cannot sync
```

User checks what to push + clicks **Push to Painter**. UXP writes to
`<sp_project_dir>/_pt_sync_inbox/<psdname>_<timestamp>/`:

- `manifest.json` (schema below)
- `uid_<uid>.png` for each selected layer

Implementation note for the first write-out slice: selection is automatic.
Only layers whose normalized diff status is `changed` are exported. Unchanged
layers are omitted, and Painter apply remains disabled until the inbox writer
is validated.

#### Historical 6.2 Apply (SP side)

Python plugin watches the inbox with `QFileSystemWatcher`. New manifest →
non-blocking toast. User opens the diff dialog, reviews each update with
old/new thumbnails, clicks Apply. Python imports PNGs as **embedded project
resources** (`resource.import_project_resource(..., Usage.TEXTURE)`) and
mutates the layer stack accordingly. Manifest renamed to
`manifest.applied.json`; PNGs may remain on disk for audit/debugging, but the
applied data lives inside the `.spp`.

**PNGs are transport only.** Once applied, data lives inside `.spp`. Deleting
the inbox folder is always safe.

Implementation note for the first Painter-side sync slice: the Painter panel
only scans and validates pending push manifests. It reports manifest count,
target texture set/stack/channel/UDIM, pending layer updates, and missing PNGs.
It does not import resources or mutate the layer stack until inbox discovery is
validated in the host.

Implementation note for the first apply slice: applying is still intentionally
minimal and user-triggered. The panel applies only the newest valid manifest
and imports each PNG as a project `Usage.TEXTURE`. After `0.1.43` host testing
showed that inserting a Fill effect inside an existing target node can crash
Painter during viewport refresh, the safer validation strategy is to insert a
standalone Fill layer above the target node and set that layer's source to the
incoming PNG/channel. This keeps the original node internals untouched. A full
diff dialog, conflict detection, mask reconciliation, and automatic watcher are
still later M4 work.

Host validation then showed that even the standalone Fill-layer path is too
heavy for the current 4K payload: Painter can remain in thumbnail generation,
viewport navigation becomes unusably slow, and deleting the generated layer can
crash. Until a safer import/apply strategy is designed, the Painter panel must
not mutate the project from the inbox button. It may validate pending manifests
and PNGs, but actual resource import and layer-stack mutation are disabled.

#### Historical 6.3 Mask sync-back

**Non-destructive, implicit** (no per-layer opt-in needed):

- SP's existing mask effect stack → every effect set `visible=false` as a
  hidden backup
- PS's flat mask → inserted as a single new fill effect at the **top** of the
  SP mask stack, visible

User can recover the original stack by deleting the top effect and re-enabling
the hidden ones.

#### Historical 6.4 "Apply Layer Mask" in PS

If UXP detects a layer that had a mask in the original SP export but no mask
channel in PS (user ran `Apply Layer Mask`), the sync panel flags it:

```
☑ DiffuseBase   [changed 2m]   ⚠ mask was applied in PS
```

Apply logic on SP side:

1. Split incoming RGBA into RGB + A
2. RGB → paint layer content (SP's existing content stack becomes hidden
   backup, new fill on top — same pattern as §6.3)
3. A → new top-of-mask-stack fill; original mask stack hidden as backup

Avoids the double-mask pitfall.

#### Historical 6.5 Manifest schema

```json
{
  "psd_file": "absolute/path/to.psd",
  "timestamp": "ISO-8601",
  "texture_set": "Body",
  "stack": "",
  "channel": "BaseColor",
  "udim": 1001,
  "normal_map_format": "OpenGL",
  "baseline_cache_key": 123456789,
  "baseline_export_timestamp": "ISO-8601",
  "layers": [
    {
      "uid": "<sp_uid>",
      "channel": "BaseColor",
      "png": "uid_<sp_uid>.png",
      "mode": "update",
      "ps_name": "…",
      "ps_hash": "sha1:…",
      "baseline_cache_key": 123456789,
      "mask_applied_in_ps": false,
      "include_mask": false
    }
  ],
  "new_layers": [
    {
      "png": "new_<guid>.png",
      "ps_name": "…",
      "insert_after_uid": "<sp_uid>",
      "blend_mode": "Multiply",
      "opacity": 80
    }
  ],
  "deleted_uids": []
}
```

#### Historical 6.6 Confirmed sync rules

1. Per-layer selective push, not global
2. New layers in PS can be inserted as new paint layers in SP; position chosen
   by "insert after" picker in UXP panel (default: nearest tagged neighbor)
3. PS → SP deletion is **not** supported in Phase 1. `deleted_uids` stays
   empty. User deletes in SP manually if wanted.
4. Mask sync-back is implicit & non-destructive per §6.3
5. Conflict detection: SP Python docs do not expose per-layer
   `last_modified`. Store baseline `TextureStateEvent.cache_key` values per
   stack/channel/UDIM tile when exporting; if the current cache key differs
   at apply time, show a conservative conflict warning for affected incoming
   layers and ask: use PS / keep SP / keep both.

---

## 7. Metadata schema

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

### 7.3 Build request preview

M1 starts with a read-only `request_type: "preview"` JSON contract. Preview
requests share the final `build_request.json` metadata shape but omit PNG
payload paths until the `alg.mapexport.save` bridge is implemented. This keeps
Painter traversal testable before Photoshop PSD construction depends on it.

Preview node records include `bake_policy`, `sync_direction`, `ps_blend_mode`,
and `warnings`. These are metadata decisions only in M1; actual raster baking
is still deferred to the PNG export slice.

The executable M1 bundle promotes the preview to `request_type: "build"`,
writes `build_request.json`, creates a sibling `png/` payload directory, and
annotates each PS-consumable node with either `asset` or `mask_asset` records.
The actual PNG writes use the SP JS bridge around `alg.mapexport.save`; local
static checks may generate the JSON without host PNG export.

The build request carries both `channel` (Python enum-style display name) and
`channel_identifier` (legacy JS mapexport identifier such as `basecolor`) so
Painter traversal and PNG export do not silently depend on the same spelling.

M1 also includes a temporary Painter dock panel for validation. It exposes a
single smoke-test action with an `Export PNGs` checkbox. When unchecked, the
button writes JSON-only bundles; when checked, it also calls the JS
`alg.mapexport.save` bridge and writes PNG payloads. This panel is intentionally
minimal and will be replaced by the full export dialog later. For M2 host
testing the checkbox defaults to enabled, and generated build requests carry an
`assets_exported` flag so Photoshop can report JSON-only bundles clearly.

### 7.4 Deprecated automatic sync-back matching

The matching rules below are historical notes from the attempted automatic
Photoshop-to-Painter push path. They are not part of the active Phase 1 manual
export workflow.

1. UXP reads every PS layer, matches suffix regex → gets `sp_uid`
2. Cross-references sidecar JSON for `sp_kind` and `sync_direction`
3. `sync_direction == "sp_to_ps_only"` layers marked "⊘ cannot sync"
4. SP-side `sync_inbox.py` uses `sp_uid` from manifest to find the node
   via `sp.layerstack.get_node_by_uid(int(uid, 16))`

The first M4 implementation is preview-only. **Push to Painter** asks the user
to select the `.rizum.json` sidecar, scans the active Photoshop document, and
shows matched/missing/new-layer categories. It must not export PNGs or write
`_pt_sync_inbox` files until this matching report is validated in Photoshop.

The preview may also show mask and diff status. Diff status is informational
until sidecar `baseline_hash` values are populated. Mask status is best-effort:
Photoshop layer-mask state is queried when possible, but a failed query should
produce `unknown` instead of blocking the preview.

Baseline hashes are written during PSD build from the source PNG payloads that
created Photoshop raster layers. Group records do not get baseline hashes
because they have no direct pixel payload. Until current Photoshop layer pixels
are exported and hashed, Push preview should report baseline-bearing records as
`current_hash_pending` rather than claiming changed/unchanged.

Sidecar JSON reads/writes should run outside Photoshop `executeAsModal`.
However, normalized pixel baseline hashing opens source PNG payloads as
temporary Photoshop documents, so that open/read/close sequence must run inside
`executeAsModal`. Current Photoshop layer pixel reads also require modal scope
in the user's Photoshop runtime.

Push preview should not depend solely on the sidecar already containing
`baseline_hash`. If a raster record has `asset_path` but no hash, preview may
compute a temporary baseline hash from the source PNG and report the source as
`asset_path`. This keeps preview useful with older or partially populated
sidecars while still leaving the sidecar file unchanged.

Do not depend on Web Crypto for SHA-1 in Photoshop UXP. The user's Photoshop
runtime does not expose `crypto.subtle.digest`, so baseline hashing uses the
project's local pure JavaScript SHA-1 helper.

Pixel diffing must compare hashes produced from the same representation.
Baseline hashes for editable raster records are normalized Photoshop Imaging
API pixel hashes of the source PNG payloads, not hashes of PNG file bytes.
Push preview computes the current Photoshop layer pixel hash with the same
normalization before reporting `changed` or `unchanged`.

If Photoshop reports an empty image region while hashing a layer, the hash
helper returns a stable empty-pixel hash. This keeps fully transparent/empty
layers comparable instead of reporting false hash errors.

For records with `mask_path`, the baseline pixel hash applies the same mask to
the temporary source PNG before hashing. Photoshop's current-layer pixel read
includes the active user mask in this runtime, so masked baselines must be
hashed the same way to avoid false `changed` reports.

---

## 8. Remaining validation questions

These are no longer blocked on missing local API docs. They require live host
validation during implementation:

- Confirm the exact `batchPlay` descriptor for enabling Photoshop's
  document-level "Blend RGB Colors Using Gamma 1.0" setting. If it works,
  no per-layer compensation LUT is needed for PS-representable blend modes.
- Record or port the exact `batchPlay` sequence for converting a temporary
  grayscale layer into a target layer mask. The old ExtendScript descriptor
  sequence in `ps-export_Rizum v1.1.8/ps-export-Rizum/footer.jsx` is the
  starting point.
- Verify `fullAccess` file handling in the user's Photoshop UXP runtime,
  especially `localFileSystem.getEntryWithUrl("file:...")` for sidecar paths.
  The local docs do not document Node-style `require('fs')` as a Photoshop
  plugin API, so the primary path is UXP File/Folder entries.
- Decide how the exporter records `normal_map_format`: no direct getter for
  an already-open Painter project's normal orientation was found in the local
  API docs. Prefer storing it when known or asking once in the export UI.
- Validate the direct unpacked-plugin installer path (`Plugins/External` plus
  `PluginsInfo\v1\PS.json` on Windows) because the included UXP docs cover UXP
  Developer Tool and packaging workflows, not that offline registration
  mechanism.
- Warn and defer full fidelity support for OCIO/ACE Painter projects. Phase 1
  assumes legacy color management with a linear sRGB working space.

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
