# Rizum PT-to-PS Bridge — Design Decisions

## Project Goal

Build a two-plugin bridge between Substance 3D Painter and Photoshop that turns
Painter texture stacks into editable PSDs while preserving as much layer
structure, blend behavior, channel context, UDIM layout, and color fidelity as
the two hosts allow. Returning work between the hosts is explicit: the native
desktop mapper shows both layer trees, the user maps selected layers to target
positions, and nothing changes in either host until the user presses Apply.

Source of truth for design choices agreed in the pre-implementation discussion.
Subject to revision only if `analysis.md` later reveals an API constraint that
makes one of these infeasible — otherwise these are locked.

This document owns user-facing behavior, workflow shape, UI expectations, and
design tradeoffs. Low-level API findings belong in `analysis.md`; implementation
directions and concrete steps belong in `plan.md`.

API-doc status: revised against the local SP Python docs, legacy SP JS docs,
and Photoshop docs listed in `analysis.md §0`. The remaining uncertainties
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
clutter. **Bridge** opens the desktop mapper for the active texture set and the
last connected Photoshop document.

The **Export** action opens a focused export dialog. The scope selector has two
display scopes only: the currently edited texture set/stack, or all stacks.
This selector controls what the dialog shows, not a separate hidden export
mode. The implementation resolves **Current Stack** with
`substance_painter.textureset.get_active_stack()` and shows an explicit empty
state when the host cannot report an active stack; it must not silently export
the first available target. Current Stack starts with its exportable channels
selected, parent rows show selected/total counts, and the Export action stays
disabled while nothing is selected. The dialog keeps group/channel checkboxes,
explicit **All** and **None** actions,
and footer buttons with large rounded proportions matching Photoshop-style
inner panels. **All** means "click to select all"; **None** means "click to
deselect all". Do not include extra eye/filter icons until those actions have
real behavior. Mask Probe remains a developer utility and does not appear
beside the normal Cancel/Export actions.

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
Mapped rows use a quiet raised surface with a 2px white leading edge. This keeps
the established white/gray accent system while making mapped state visible;
blue is not introduced as a second global accent. A short faint drop hint may
follow the current Target content, but it should not become a boxed empty state.

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

Painter writes build bundles to `<exportPath>/<project>_photoshop_export/`,
resolving Painter's project export path through the JS
`alg.mapexport.exportPath()` fallback, plus `_last_export.json` listing the
exact requests of that run. The plugin is an automation bridge, so every
successful export continues straight into Photoshop: Painter writes a JSX
launcher for the export list and starts the configured Photoshop executable
with it. There is no auto-open setting and no manual handoff dialog. An invalid
executable path reports a focused error instead of pretending the build
started.

Painter build requests should include channel semantics in addition to the raw
channel enum: a display label, a role (`color`, `data`, `opacity`, `normal`, or
`user`), format, bit depth, and color/data flag. Photoshop should show those
fields in its sidecar before any channel-specific pixel behavior is
introduced.

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
For per-layer user-channel PNG export, the request-level engine identifier is
the primary export string, and documented fallbacks such as `user1`, `user 1`,
and the custom channel label are tried only if the primary string produces an
empty result or fails. This keeps old-plugin-compatible strings first without
making the exporter depend on one user-channel spelling.

The desktop mapper (`desktop/`) is the transfer queue between the hosts. It
shows Photoshop and Painter layer trees side by side and lets the user drag
selected layers onto a target group or insertion position: group highlights
mean "inside", thin insertion lines mean "after". Staged transfers are
selectable, retargetable, and undoable. Apply writes one transfer manifest and
closes the mapper; Painter then applies it and, for Painter-to-Photoshop
transfers, runs a confirmed Photoshop job.

Connecting another Photoshop document keeps the mapper open. Painter owns the
file picker and the Photoshop export, then hands the new selection back to the
open window, so the user keeps their Painter target. The mapper never hides
background sync behind the UI.

The Painter dock panel must also keep a module-level strong reference to its
Python panel object. Painter owns the dock widget after `sp.ui.add_dock_widget`,
but the Python object still owns timers, slots, and child-widget references; if
that object is garbage-collected, the dock can remain while its contents or
handlers disappear.

---

## 1. Architecture split

| Side | Language | Framework |
|---|---|---|
| Substance Painter plugin | **Python** (SP Python API) | PySide6 for UI |
| Photoshop automation | **ExtendScript** launched by Painter (`photoshop_*.jsx`) | Photoshop DOM + Action Manager |
| Desktop mapper | **TypeScript** on Bun (`desktop/`) | React 19 + GPUiX |
| Transport | **File-based** PNG + JSON contracts, plus the mapper's stdio link to Painter | — |

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

Per-layer and per-mask PNGs, including per-UV-tile payloads, come from
Painter 12.1's native stack-node texture export. It does not mutate the layer
stack, so no visibility isolation or temporary modification is needed.

Project-level bridge choices should be stored in Painter `project.Metadata`
when they belong to the current `.spp`, for example normal-map-format override,
last export preset, and last scoped target. Machine-level choices, such as the
Photoshop executable path, remain global.

`TextureStateEvent.cache_key` is a future integrity signal, not an active sync
requirement. If the bridge later needs to warn that a Painter stack changed
after PSD export, it should store cache keys per stack/channel/tile instead of
inventing a parallel dirty-state mechanism.

Normal-map orientation should be treated as unknown until it can be inferred or
set. Preferred future order: direct host setting if `alg.project.settings`
exposes it, normal-source `SourceBitmap.get_color_space()` inference when
available, then a user choice persisted in `project.Metadata`.

---

## 2. Photoshop automation

No Photoshop plugin is installed. Painter drives every Photoshop step by
starting the configured Photoshop executable with a generated JSX launcher:
building PSDs after export (`photoshop_build.jsx`) and inserting mapped
Painter layers (`photoshop_transfer.jsx`). Connecting a PSD needs no
Photoshop at all (see §6.1). This keeps the plugin zero-install and fully
automatic; a UXP panel was removed because UXP panels cannot receive a reliable
external launch event and duplicated the ExtendScript builder.

Each launched job publishes progress and a result receipt atomically, and
Painter treats the job as started only after the script's first receipt.

The release is the repository folder itself: the root Painter loader shims,
`sp_plugin/`, the vendored `rizum_ui/` and `icons/`, and the built desktop
mapper in `desktop/dist/`.

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

**Fallback** if Photoshop scripting cannot toggle this setting:
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
(`1.0` is fully opaque, `0.55` is 55%). Photoshop layer opacity is a
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

The Photoshop build places each PNG with Place Embedded and moves the placed
layer directly into its parent group, which avoids temporary anchor layers whose
stale DOM handles trigger unavailable Select commands. Placed PNGs stay smart
objects during assembly and are rasterized in one pass at the end. The new
document's initial layer is renamed to a unique placeholder and removed once
real content exists, so a Painter layer named `Layer 1` is never deleted.

The current mask slice attaches `mask_asset` PNGs to placed raster layers
through Photoshop's Imaging API: open mask PNG, read it as grayscale image
data, then call `imaging.putLayerMask()` on the target Photoshop layer. Mask
failures are reported separately and do not remove the successfully placed
pixel layer.

SP 12.1.0+ invalidates the old plugin's JS true-mask export path:
`alg.mapexport.save([uid, "mask"], ...)` now routes through the stack
`blendingmask` channel and does not return ordinary layer/folder mask pixels.
For Phase 1 compatibility, Painter mask PNGs are therefore derived from the
exported layer PNG alpha and marked as approximate. This preserves a useful
Photoshop visual mask while avoiding the host error, but it is not a lossless
Painter mask representation and cannot cover folder masks without a direct
layer PNG alpha source. A later Python layerstack mask exporter is required
before the design can claim original-mask fidelity again.

The Painter Export dialog may expose a temporary **Probe** action while this
mask exporter is being designed. Probe is read-only and writes `_mask_probe.json`
beside the normal export bundles. It is not a user workflow feature; it is a
host-diagnostic aid for deciding which mask structures can be reconstructed
from Python metadata and which require a rendered workaround.

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

### 5.3 Sub-effects inside a mask

Baked through the native stack-node mask export: Photoshop receives the
lossless rendered mask pixels, but not the editable mask-effect stack, which PS
has no concept of.

### 5.4 Anchor point references

Each anchor reference is **baked in place** as a regular Normal-mode raster
layer. No special locking, no hidden metadata beyond the standard
`rizum_sp_uid`. For return transfers it is simply another Photoshop layer.

---

## 6. Photoshop selected-layer export (PS to Painter)

**User-initiated.** No live sync and no background Painter mutation. Painter
changes only when the user presses Apply in the desktop mapper.

An earlier automatic inbox design imported 4K PNGs as Painter resources in the
background; host testing showed thumbnail stalls, unusable viewport slowdown,
and crashes, so return transfers must stay explicit (see
`docs/archive/deprecated-sync-inbox-design.md`).

### 6.1 Connecting a Photoshop document

**Connect Photoshop** asks Painter to pick a PSD/PSB, and the mapper reads the
saved file itself, so connecting never opens Photoshop. Because nothing comes
from Photoshop's own renderer, the mapper treats layers this way:

- Raster, text, and smart-object layers transfer as Painter fill layers; their
  user masks transfer as real Painter masks.
- Clipped layers merge into their base when transferred. Clipped rows stay
  visible but locked with "Clipped · merges into <base>", and the base row
  says how many layers merge into it.
- Layer styles are not transferred; the row says so.
- Adjustment and fill layers are locked, because Painter has no equivalent.
- A Photoshop folder arrives in Painter as a folder of its layers. The mapper
  shows no group composite previews.

Only mapped layers are rendered to PNG, at Apply. The mapper reads the saved
file, so unsaved Photoshop edits are not seen until the PSD is saved.

### 6.3 Non-goals for return data

The return path deliberately does not:

- watch folders or apply transfers without an explicit Apply;
- depend on `[rz:<uid>]` suffixes, sidecar matching, hash diffing, or layer
  rename rules;
- attempt conflict detection between Photoshop edits and later Painter edits.

---

## 7. Metadata schema

### 7.1 Photoshop layer names

Plugin-created Photoshop layers and groups use clean user-facing names, without
visible ` [rz:<uid>]` suffixes. Provenance lives in the build request and the
PSD sidecar instead.

### 7.2 Sidecar JSON

The Photoshop build writes `<psdname>.rizum.json` next to each saved PSD. It
carries only what the desktop mapper reads to open a connected PSD on its
source Painter context:

```json
{
  "schema_version": 1,
  "psd_file": "C:/.../Body_basecolor.psd",
  "texture_set": "Body",
  "stack": "",
  "channel": "BaseColor",
  "channel_label": "Base Color"
}
```

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
- Decide how the exporter records `normal_map_format`: no direct getter for
  an already-open Painter project's normal orientation was found in the local
  API docs. Prefer storing it when known or asking once in the export UI.
- Warn and defer full fidelity support for OCIO/ACE Painter projects. Phase 1
  assumes legacy color management with a linear sRGB working space.
