# Analysis History

Archived from `analysis.md`: the former project-state notes, the numbered
host-correction log, and the original findings summary. Several entries
describe approaches that were later replaced (alpha-derived masks, Mask
Probe, manual return export, the sync inbox); `analysis.md` holds the
constraints that still apply.

## Former Project State

This document is the technical record for API docs read, reference
implementations inspected, code findings, constraints, edge cases, and
implementation conclusions. User-facing behavior and interaction choices belong
in `design.md`; concrete next steps belong in `plan.md`.

Current active direction:

- Substance Painter to Photoshop remains the structured build path: Painter
  writes a `build_request.json` bundle plus PNG payloads; Photoshop builds an
  editable PSD from that request.
- Photoshop to Painter is manual in Phase 1: Photoshop exports selected layers
  as PNGs, optionally with separate mask PNGs, and the user imports or places
  those files in Painter manually.
- The automatic `_pt_sync_inbox` / manifest / Painter resource-import path was
  implemented experimentally, then deprecated after user host validation showed
  severe 4K thumbnail-generation stalls and crash risk.
- Checks are not run by default under the active Rizum Guidelines. Run syntax,
  static, build, or host checks only when requested or when debugging feedback
  makes them necessary.
- User host feedback showed Painter can freeze or crash while painting when the
  plugin is enabled, but not when it is disabled. The only active background
  behavior found in the Painter side is a 1-second `QTimer` in the dock panel
  that polls `substance_painter.project.is_open()` to refresh button state.
  Even though that timer does not mutate the project, it violates the current
  no-background-polling design and may interfere with Painter's main UI/event
  loop during brush strokes. The Painter panel should therefore use only
  user-triggered project checks and no periodic refresh.
- User host feedback also confirmed that `alg.mapexport.save([effectUid,
  channel], ...)` is not a valid export target in this runtime. Painter reports
  `ExportError: Error while searching object: The given Uid doesn't reference
  any layer`. Treat direct `content_effects` and `mask_effects` as metadata or
  as data baked through their parent layer/mask export, not as independently
  exportable PNG assets.
- SP 12.1.0+ also breaks the old plugin's true mask export path:
  `alg.mapexport.save([layer.uid, "mask"], ...)` now resolves through the
  stack `blendingmask` channel. Stacks without that channel fail with
  "The channel Blending mask is not available"; adding a `blendingmask`
  channel only produces transparent empty PNGs, not the original layer/folder
  mask. The active exporter must therefore not rely on JS `"mask"` export for
  lossless mask data.
- Phase 1 explicitly abandons editable Photoshop clipping reconstruction for
  Painter content effects. The exporter should keep those effects as
  provenance and rely on parent layer/mask PNGs. A future version can revisit
  clipping only if Adobe exposes or we validate a real per-effect export path.
- Until a true Python layerstack mask exporter is validated, Painter mask PNGs
  are an approximate compatibility fallback derived from the exported layer
  PNG alpha. This keeps Photoshop builds usable and avoids the SP 12.1.0
  `blendingmask` failure, but it is not a lossless original Painter mask and
  cannot represent group masks without a direct layer PNG alpha source.
- The first true-mask investigation step is a read-only Painter **Mask Probe**:
  it walks masked layers/folders and their `mask_effects()`, records mask
  backgrounds, effect kinds, source types, and rebuild hints into
  `_mask_probe.json`. This probe intentionally does not mutate visibility,
  create temporary layers, or export pixels; it exists to decide whether a
  future true-mask exporter should rebuild simple source structures, use a
  controlled render/solo-export path, or classify a mask as not recoverable
  through Python alone.
- The Painter exporter already supports `texture_sets`, `stacks`, and
  `channels` filters. The UI now exposes those filters as larger manual export
  scopes: one selected texture-set/stack/channel, all channels for the selected
  texture-set/stack, the selected channel across the project, or all targets.
  This keeps batch export user-triggered while avoiding the old all-or-one
  workflow.
- The Painter panel no longer exposes `_pt_sync_inbox` scan/apply controls.
  That code can remain as inert historical support, but Phase 1 UI should not
  send users back to the deprecated automatic Photoshop-to-Painter path.
- Scoped exports still write bundle folders into the shared
  `<project>_photoshop_export` root. Because older bundle folders can remain
  there, Photoshop folder-build can accidentally build stale requests. Painter
  now writes `_last_export.json` after each export with the exact
  `build_request.json` paths from that run, and Photoshop can build that list
  directly through **Build Export List**.
- Painter requests now carry lightweight channel semantics:
  `channel_label`, `channel_role`, `channel_format`, `bit_depth`, and
  `is_color`. Photoshop reports those fields and stores them in the sidecar.
  This is metadata/reporting only for now; it does not yet change pixel
  construction for opacity, normal, or user channels.
- User channel labels come from `Channel.label()` when available, so Painter UI
  can show user-facing names such as `SCol`, `TNrm`, or `SDF` while requests
  still keep the stable enum channel (`User0`, `User1`, etc.).
- User channel labels are also used for bundle and PSD filenames when present,
  while standard channels keep their Painter enum names.
- After PNG export, Painter removes layer assets whose exported PNG alpha is
  fully transparent. If an entire channel request has no remaining layer PNGs,
  that build bundle is skipped. This is based on actual exported pixels rather
  than guessing from layer metadata.
- Before PNG export, Painter now asks the legacy JS map-export API for the
  stack's used channel identifiers and filters empty stack channels out of the
  target picker/build list. The transparent-PNG prune remains a layer-level
  fallback for host ambiguity and per-layer empty payloads.
- User channel PNG export must use the resolved JS map-export channel
  identifier, not only the Python enum name. For user channels, identifiers can
  be labels such as `SCol`, `TNrm`, or `SDF`; exporting with `User1`/`User2`
  can produce transparent payloads even when layers use that channel.
- Painter Python exposes `active_channels` on fill/effect-style nodes. Use it
  to avoid annotating/exporting nodes that are not active for the current
  request channel. Paint stroke pixels are still not readable from Python, and
  Python's texture export API exports full final textures rather than isolated
  layer PNGs, so per-layer PNG writing still relies on the JS map-export path.
- Because user-channel identifier behavior differs between Python enum names,
  user labels, and JS resolved identifiers, user-channel layer PNG export now
  tries multiple channel identifier candidates and keeps the first non-empty
  result.
- The old v1.1.8 plugin did not use Python channels for export. It read
  `alg.mapexport.documentStructure().materials[].stacks[].channels` and reused
  those exact strings for both full-channel snapshots and per-layer
  `alg.mapexport.save([layer.uid, channel], ...)`. The current exporter should
  prefer that legacy document-structure channel list when deciding target
  channels and channel identifiers, with `channelIdentifiers(stackPath)` as a
  fallback.
- User testing showed `documentStructure()` / `channelIdentifiers(stackPath)`
  can under-report channels on a stack that uses Fill layers with externally
  referenced maps. The target filter therefore treats Python `active_channels`
  as a second positive signal: if JS does not list a channel but a traversed
  layer/effect explicitly marks that channel active, the exporter keeps the
  channel instead of filtering it out.
- User testing also showed single-channel export could succeed while the
  selected-stack/all-channel button did not produce the same channel set. The
  Painter UI now passes the refreshed target's explicit `channels` list into
  selected-stack export so the batch path uses the same discovered targets as
  the single-channel path.
- User host testing then confirmed both single-channel and selected-stack
  exports are working for the current Wings reference-map case.
- Painter export actions should require both `project.is_open()` and
  `project.is_in_edition_state()`. The Python docs define edition state as
  "ready to work with"; exporting while the project is still loading or
  otherwise non-editable risks host errors.
- The local JS docs state `channelIdentifiers(stackPath)` returns only used
  channels with resolved user channels. Valid user-channel names for
  `alg.mapexport.save([uid, channel])` include lowercase compact names such as
  `user1`, lowercase spaced names such as `user 1`, and custom labels such as
  `SCol`. The exporter now keeps resolved engine strings first, but also tries
  the documented compact and spaced spellings before treating an export as
  unavailable.
- `alg.mapexport.save` `MapInfo` has no UV-tile or UDIM parameter. It supports
  export settings such as padding, dilation, resolution, bit depth, and alpha,
  but not per-tile filtering. If a future UDIM workflow requires true per-tile
  per-layer PNG assets, the known fallback is a Python visibility-isolation
  export using `Node.set_visible()`, `ScopedModification`, and
  `export_project_textures(... filter.uvTiles ...)`. That fallback must remain
  opt-in until host performance is measured because it temporarily mutates
  Painter visibility and may trigger recomputation.
- If the Python visibility-isolation fallback is implemented, wrap the
  visibility mutation/export block in `substance_painter.application
  .disable_engine_computations()` as well as `ScopedModification`. The local
  Python docs define this context manager as the way to pause texture/viewport
  computation during bulk edits, which directly addresses the thumbnail-refresh
  risk seen during the deprecated inbox/apply path.
- Project-scoped preferences should use `substance_painter.project.Metadata`
  when they belong to the `.spp` file, such as normal-map-format override,
  last export preset, or last scoped target. Global preferences such as a
  Photoshop executable path can stay global.
- `TextureStateEvent.cache_key` is persistent across sessions and can become a
  future baseline fingerprint for stack/channel/tile state. It is not needed
  for the active manual Photoshop return workflow, but it is the right API if
  the bridge later wants to report whether Painter changed since a PSD export.
- No direct Python getter for an already-open project's normal-map format has
  been found. Candidate inference paths are an unchecked JS
  `alg.project.settings` namespace, or reading a normal source's
  `SourceBitmap.get_color_space()` and mapping
  `NormalXYZRight`/`NormalXYZLeft` to OpenGL/DirectX. Fall back to a user
  setting stored in `project.Metadata`.
- `SourceBitmap.get_color_space()` can also support future color/data role
  classification for custom channels. Phase 1 keeps the current name-based
  channel role heuristic because it covers standard PBR channels.
- `ProjectWorkflow` distinguishes default projects, legacy texture-set-per-UV
  tile projects, and modern UV-tile UDIM projects. Store it in future request
  metadata if UDIM solo-export decisions need more precision than
  `texture_set.has_uv_tiles()`.
- `project.execute_when_not_busy()` and `async_utils.StopSource` are useful
  future primitives for deferred/asynchronous export, but the current
  user-triggered synchronous progress dialog remains simpler and adequate for
  Phase 1.
- Painter exports now run behind an application-modal progress dialog. This
  blocks normal UI interaction during export while still allowing cancellation
  between build requests and between PNG asset writes.
- Photoshop **Build Export List** now leaves built PSDs open after saving,
  because scoped export lists are small enough for inspection.
- The old v1.1.8 "no Photoshop click" path did not trigger a Photoshop plugin.
  Painter generated a `photoshopScript.jsx`, stored the user's Photoshop
  executable path in Painter settings, then launched Photoshop with that script
  path as an argument. For the current UXP build path, the closest small
  automation candidate is a generated `.psjs` launcher that runs the existing
  build-list logic. This needs host validation because local UXP docs document
  `.psjs` through File > Scripts > Browse, drag/drop, and Actions, but do not
  clearly guarantee the old `Photoshop.exe script.jsx` command-line behavior for
  `.psjs`.
- A future desktop bridge can act as a visual transfer queue between the two
  host plugins. It should not mutate Photoshop or Painter directly. Instead,
  each host plugin exports selected layers plus a layer-tree snapshot into a
  local interchange folder; the desktop app lets the user drag exported items
  onto target insertion positions and writes an explicit transfer manifest.
  The target host plugin applies that manifest only when the user clicks Apply.
  This keeps the workflow manual and inspectable while enabling partial-layer
  transfers and user-chosen placement.

**Status**:
- §1 SP Python API — **done**
- §2 SP JS API fallback — **done**
- §3 UXP Photoshop API — **done from local docs; host-recorded descriptors still need validation**
- §4 Gaps & decisions — **done**
- §5 Open questions — implementation-validation only

This doc has now been populated from the API documentation included in this
repo. Every design claim in `design.md §5–7` that is backed by documented API
surface has a concrete API call or an explicit fallback listed here. The only
remaining items are host-behavior validations that require running inside
Photoshop or Substance Painter.

## 0. Host Correction Log

### 0.1 Painter local plugin layout correction

The local development checkout lives directly under Painter's Python plugin
directory as `rizum-pt-to-ps-bridge`. The Python API docs say Painter plugins
are standard Python modules on `substance_painter_plugins.path` and must expose
`start_plugin()` and `close_plugin()`.

Because the checkout folder name contains hyphens, it is not itself a valid
Python package name. The root therefore exposes thin loader shims:

- `__init__.py` for loaders that execute the plugin folder as a package/path.
- `rizum_pt_to_ps_bridge.py` for loaders that need a valid Python module name
  after the project root has been added to the plugin search path.
- `plugin.json` at the root for Painter's plugin metadata/about dialog.

The actual Painter implementation stays in `sp_plugin/rizum_sp_to_ps/` so the
release zip can still copy that implementation package independently. Live
Painter validation is still required to confirm which of the two root shims the
current host build discovers from this hyphenated checkout directory.

### 0.2 Photoshop local plugin loading correction

The Photoshop UXP plugin is not discovered from Painter's Python plugin
directory. This repository contains both host plugins, but each host loads only
its own side:

- Substance Painter loads the root Painter shim from this checkout because the
  checkout is inside Painter's Python plugin directory.
- Photoshop loads only the UXP plugin described by `ps_plugin/manifest.json`.

The local UXP docs-backed development path is:

1. Open Photoshop.
2. Open Adobe UXP Developer Tool.
3. Add an existing plugin by selecting `ps_plugin/manifest.json`.
4. Load the plugin from UXP Developer Tool.
5. Open the panel from Photoshop's Plugins menu as `Rizum PT Bridge`.

The direct `%APPDATA%\Adobe\UXP\Plugins\External\` installer remains a Phase 1
distribution goal, but the local docs do not specify the required
`plugins.json` registration schema. Until that is validated in a live
Photoshop install, UXP Developer Tool is the reliable local test path.

### 0.3 Offline Photoshop external registration discovery

The user's offline Photoshop setup already has external UXP plugins installed
under `%APPDATA%\Adobe\UXP\Plugins\External\`. Those plugins are registered in:

```text
%APPDATA%\Adobe\UXP\PluginsInfo\v1\PS.json
```

Observed schema:

```json
{
  "plugins": [
    {
      "hostMinVersion": "23.3.0",
      "name": "Plugin Name",
      "path": "$localPlugins\\External\\plugin-folder",
      "pluginId": "plugin.id",
      "status": "enabled",
      "type": "uxp",
      "versionString": "1.0.0"
    }
  ]
}
```

The Windows installer should therefore copy `ps_plugin/` into
`%APPDATA%\Adobe\UXP\Plugins\External\com.rizum.pt-to-ps-bridge` and upsert a
matching enabled entry into `PluginsInfo\v1\PS.json`. This is a host-discovered
offline registration path, not a local-docs-backed API contract, so user-side
Photoshop validation is still required.

The matching Windows uninstaller should be the inverse operation:

- read `ps_plugin/manifest.json` to get the plugin ID;
- remove only `%APPDATA%\Adobe\UXP\Plugins\External\<pluginId>`;
- remove only registry entries whose `pluginId` matches from
  `%APPDATA%\Adobe\UXP\PluginsInfo\v1\PS.json`;
- write `PS.json` back as UTF-8 without BOM;
- verify the resolved target path stays inside Adobe's UXP External plugin
  folder before deleting anything.

### 0.4 Photoshop panel blank-content correction

After offline registration, Photoshop showed the plugin entry, but the panel
did not show test buttons. The previous `index.html` left `<main id="app">`
empty and relied on `src/main.js` to dynamically create all controls through
`entrypoints.setup`. In an offline host, a script load, local `require`, or
entrypoint registration failure can therefore leave the panel visually blank.

M2 should keep the panel boot path more defensive:

- Put the minimal test controls directly in `index.html`.
- Bind button handlers from JS after the DOM exists.
- Lazy-load local modules only when a button is pressed, so a module-loading
  problem appears as an in-panel error instead of a blank panel.
- Call `entrypoints.setup` immediately at plugin startup. The local UXP docs
  list delayed setup as a known issue that can produce panel lifecycle failure.

### 0.5 Offline Photoshop v4 compatibility fallback

The panel tab can appear while its content remains blank when the offline host
does not execute the HTML/body path or does not trigger the Manifest v5 panel
lifecycle as expected. The local docs state Manifest v4 is valid for Photoshop
22.0+, and the user's existing offline external plugin list includes a working
Manifest v4 Photoshop plugin.

Compatibility decision for the current local test slice:

- Use `manifestVersion: 4`.
- Use `host.minVersion: "22.0.0"` so Photoshop 2021 can load the panel.
- Point `main` directly at `src/main.js` instead of `index.html`.
- Render all panel controls from `entrypoints.setup` into the provided panel
  root node.

This is a compatibility test path. If the user later confirms Photoshop 2025
with UXP v5 works reliably, the manifest can return to v5 before distribution.

### 0.6 PS.json encoding correction

Photoshop 2025 UXP logs reported:

```text
Failed to parse JSON C:\Users\Rizum\AppData\Roaming\Adobe\UXP\PluginsInfo\v1\PS.json
```

The first bytes of the generated file were `EF BB BF`, meaning PowerShell wrote
UTF-8 with BOM. Adobe's plugin-info parser appears to reject that file. The
Windows installer must write `PS.json` as UTF-8 **without** BOM and should bump
the plugin version during compatibility iterations to avoid stale host caches.

### 0.7 Photoshop panel diagnostic slice

After fixing `PS.json`, Photoshop 2025 logs show `com.rizum.pt-to-ps-bridge`
is added to the UXP plugin manager, but the panel still renders blank and no
Rizum console output is visible. The next diagnostic slice should remove all
secondary module loading and test only the UXP lifecycle:

- Manifest v5 for Photoshop 2025.
- `main: "src/main.js"` so the entry script is the plugin initialization file.
- `console.log` at top level, `plugin.create`, `panel.create`, and
  `panel.show`.
- A single diagnostic panel body rendered directly into the provided root node.

If this produces no logs, Photoshop is not executing our entry script or is
serving a stale cached plugin. If logs appear but the panel is blank, the root
node handling is wrong.

### 0.8 Official starter-template correction

Adobe's Photoshop UXP "Creating your first plugin" guide shows the starter
panel with `manifest.main` pointing to `index.html`; that HTML file defines the
panel body directly and then loads JS for button behavior. This means the
lowest-risk diagnostic is not an entrypoint-rendered JS panel, but a pure
static HTML panel with no script at all.

Current diagnostic decision:

- Use Manifest v4 with `main: "index.html"` like the official starter pattern.
- Temporarily remove all panel script loading.
- Put a visible status block and two disabled diagnostic buttons directly in
  `index.html`.

If this does not render in Photoshop, the failure is below application JS:
Photoshop is not loading the panel document from the External registration.
If it does render, the previous blank panel was caused by JS/bootstrap behavior.

Installation note: Photoshop keeps UXP WebView/cache files locked while the
host is running. After installing this diagnostic build, fully quit Photoshop
and relaunch it before judging whether the static HTML renders. Reloading the
panel alone is not a valid test for this External-registration path.

### 0.9 Photoshop 2025 root-node diagnostic correction

After a full Photoshop 2025 restart, the plugin is still registered in the
latest UXP log and no manifest parse error is reported, but the panel remains
blank. A pure static `index.html` body is therefore not enough to prove the
panel surface is receiving document body content in this offline External
registration path.

The next diagnostic should combine the official `main: "index.html"` shape with
immediate `entrypoints.setup`. `index.html` loads `src/main.js`; `main.js`
registers `panels.rizumBridge.create/show` and writes the diagnostic controls
into the host-provided panel root node. This tests the documented panel
entrypoint mapping directly while still avoiding secondary modules and PSD
business logic.

After the `0.1.4` restart test, the plugin still appears in the UXP plugin
manager but the latest log contains no Rizum startup line and the panel stays
blank. Add a separate command entrypoint as the next diagnostic. A command
click should execute plugin JS without depending on panel rendering. If the
command does not show an alert either, the failure is in the External
registration/load layer rather than in panel UI code.

The `0.1.5` diagnostic proved plugin execution is working: the latest Photoshop
2025 log contains `main.js loaded`, `plugin.create`, `panel.create`,
`panel.show`, and `command.rizumDiagnostics`. The alert did not appear, but the
command log line proves the command handler ran. The remaining blank-panel
failure is therefore a DOM/rendering compatibility issue. Replace the
`innerHTML` render path with direct DOM node creation and native Spectrum UXP
elements, and enable alerts explicitly in the manifest for future command
diagnostics.

The `0.1.6` command diagnostic was confirmed by the user: Photoshop displayed
the `Rizum Diagnostics 0.1.6` alert. This closes the External registration and
plugin-JS execution question. Remaining validation is now limited to whether
the direct-DOM Spectrum panel renders visibly in the docked panel surface.

The latest `0.1.6` log after the command click contains
`command.rizumDiagnostics` but no `panel.create/show` or `panel rendered direct
DOM` entries. The next diagnostic should not depend solely on the panel
lifecycle. Render the same visible diagnostic body from plugin startup, panel
`create/show`, and the command handler, using plain HTML elements with explicit
high-contrast inline styles.

The `0.1.7` diagnostic implements that approach and was installed into the
offline External plugin directory. It keeps Manifest v5 + `main: "index.html"`
but uses plain HTML elements only, no Spectrum components, and renders from
startup, `plugin.create`, command execution, and panel `create/show`. This
means a full Photoshop restart should distinguish three cases:

- The command alert appears and the command forces visible body content:
  document-body painting works, panel root/lifecycle is the remaining issue.
- Logs show `panel.create/show` plus `panel rendered plain HTML` but the panel
  is blank: Photoshop is not displaying the root node we are mutating.
- No `0.1.7` startup log appears after restart: Photoshop is serving stale
  plugin state or not loading the installed files.

The user confirmed the `0.1.7` panel is visible in Photoshop 2025 and the
diagnostic buttons respond. This proves the External registration, Manifest v5
HTML entry, script execution, and plain DOM painting path all work. The next
M2 slice can restore the real "Build from Painter" file picker and
`build_request.json` validation on top of this plain-HTML shell, keeping
Spectrum components out until there is a reason to reintroduce them.

The `0.1.8` slice restores the real request-intake flow on top of the
confirmed plain-HTML panel. The **Build from Painter** button opens a UXP JSON
file picker, reads the selected `build_request.json`, validates schema version
1 with `request_type: "build"`, and displays an in-panel summary of texture
set, stack, channel, UDIM, resolution, output PSD path, top-level layer count,
PNG asset count, mask asset count, and baked asset count. It intentionally does
not create or mutate a Photoshop document yet.

The first Photoshop test of `0.1.8` showed two host-specific issues. First,
`require("./build-psd.js")` resolves relative to the plugin document/root in
this UXP runtime, not relative to `src/main.js`, so the request module must be
loaded as `./src/build-psd.js` with a fallback for alternate runtimes. Second,
the docked panel can be shorter than the diagnostic content, so the panel and
details area must use explicit overflow scrolling and tighter spacing.

The `0.1.9` slice applies those fixes and is installed in the offline External
plugin path. It uses root-relative `require("./src/build-psd.js")` first,
falls back to `require("./build-psd.js")`, and adds scrolling to the body,
panel container, and details box for narrow or short docked panels.

The next panel sizing adjustment should increase the UXP panel manifest
dimensions because Photoshop can lock extension panel size from manifest
metadata. Use a taller minimum and preferred docked/floating height, while
keeping the HTML layout scrollable for hosts that still clamp the docked panel.

The `0.1.10` panel sizing build requests a taller Photoshop panel through the
manifest: minimum `280x560`, preferred docked `320x720`, and preferred floating
`380x760`. The HTML shell now has a `520px` minimum content height and the
request details box can expand to `360px`.

The next M2 slice should create only a minimal transparent PSD skeleton from a
validated `build_request.json`. The local Photoshop UXP docs support document
mutation through `require("photoshop").core.executeAsModal(...)` and document
creation through `app.createDocument({ width, height, resolution, mode, fill,
name })`. This slice should not place PNGs, create groups, or write masks yet.

Saving the skeleton directly to the absolute `psd_file` path remains a live
host validation gate. The local docs mention `localFileSystem.getEntryWithUrl`
in related filesystem coverage, but the expanded reference page is not included
here and it is unclear whether Photoshop will create a missing file entry at an
arbitrary absolute path. The implementation should therefore attempt request-path
saving conservatively, keep the newly created document open if saving fails, and
show the save status/error in the panel.

Version `0.1.11` implements that PSD skeleton slice and was installed through
the Windows External-plugin installer. Local static checks passed, and the
installed manifest plus `PS.json` registration both report `0.1.11`. Photoshop
host validation is still required to confirm whether `executeAsModal` document
creation succeeds and whether request-path saving works in this runtime.

The user confirmed the `0.1.11` skeleton document is created at the expected
request resolution. The panel reported `Saved: no`, and `getEntryWithUrl`
could not find an entry for the target PSD path. This validates the assumption
that request-path saving needs a different UXP file-entry strategy when the PSD
does not already exist.

The same test also showed that the docked panel's `<pre>` output is cumbersome
to report because the text cannot be copied easily. The local UXP docs show
clipboard access through `navigator.clipboard.setContent({ "text/plain": text })`
and require `"clipboard": "readAndWrite"` in Manifest v5. The next panel slice
should switch diagnostics to a readonly selectable `<textarea>` and add a
`Copy Details` button.

The same clipboard permission can be used for a small **Paste Request Path**
helper in the Photoshop panel. UXP runtimes may expose clipboard text as either
a plain string from `navigator.clipboard.readText()` or a keyed object such as
`{ "text/plain": "..." }`, so the panel normalizes both. If clipboard reading
is unavailable in a given Photoshop runtime, the direct path input remains
usable through manual Ctrl+V.

Version `0.1.12` implements that copy-friendly diagnostics slice and was
installed through the Windows External-plugin installer. The installed manifest
declares clipboard access and `PS.json` registers `0.1.12`.

Official Adobe UXP docs clarify the save-path fix: `getEntryWithUrl` throws
when the file or folder does not already exist, while `createEntryWithUrl(url,
{ overwrite: true })` creates a file entry when the parent folder exists. Folder
entries also expose `createFile(name, { overwrite })`, but the direct
`createEntryWithUrl` path is the smallest change for the current absolute
`psd_file` request path.

Version `0.1.13` implements that `createEntryWithUrl` save attempt with the old
`getEntryWithUrl` lookup kept only as a fallback. Photoshop host validation is
still required to confirm that `document.saveAs.psd` accepts the newly-created
File entry for an absolute `file:` URL in the user's runtime.

Painter's Python API still reports a single default UV tile as UDIM 1001 when a
texture set is not a UDIM project. Keep `udim: 1001` in the request for internal
tile math and compatibility, but mark synthetic non-UDIM tiles with
`uv_tile.is_udim: false`. User-facing bundle names, PSD names, and Photoshop
panel summaries should omit the `1001` suffix when that flag is false.

Version `0.1.14` implements this non-UDIM naming rule. Painter-generated
non-UDIM bundles and PSD paths no longer include `1001`; UDIM projects still do.
The Photoshop summary also displays `UDIM: (none)` when `uv_tile.is_udim` is
false.

Version `0.1.15` places only top-level raster PNG assets into the new PSD.
The local Photoshop UXP docs support this path with
`app.open(pngEntry)`, `layer.duplicate(targetDoc)`, layer property writes
(`name`, `visible`, `opacity`), and `doc.closeWithoutSaving()` for the
temporary PNG documents. The implementation should resolve PNGs through
lookup-only UXP file entries so missing assets fail as placement errors instead
of accidentally creating empty files. Groups, masks, sub-effects, blend modes,
metadata suffixes, and sidecar JSON remain out of scope for this slice.

### 0.10 Painter no-project startup stability

The local `sdf` Painter plugin provides a stable reference for plugin loading
when Painter starts without an open project. Its `start_plugin()` only creates
a Qt widget and calls `sp.ui.add_dock_widget(widget)`; project-dependent layer
queries are deferred to panel refresh/action handlers and wrapped in
`try/except`, with a `(No project loaded)` UI state.

The Rizum Painter panel now follows the same rule:

- register the dock with the documented default `add_dock_widget(widget)`
  shape, avoiding unnecessary keyword arguments;
- keep plugin startup free of project, texture-set, and layer-stack queries;
- detect `substance_painter.project.is_open()` before enabling the smoke-test
  action;
- show an in-panel "Open a Painter project" status instead of failing plugin
  load or failing only after the button click.

### 0.11 Missing PNG asset correction

The first `0.1.15` top-level raster test created and saved the PSD, but placed
`0 of 7` top-level PNG layers because the selected `build_request.json` pointed
to PNG paths that did not exist on disk. This happens when the M1 smoke panel
writes a JSON-only bundle: asset records are still present in the JSON because
they describe what Photoshop should consume later, but no PNG payload files
are created.

Correction:

- default the Painter smoke panel's `Export PNGs` checkbox to enabled for M2
  host testing;
- write `assets_exported: true/false` into `build_request.json` so Photoshop
  can distinguish a JSON-only diagnostic bundle from a usable PNG bundle;
- keep JSON-only generation available for local/static validation;
- shorten Photoshop missing-PNG errors to the source path and add a clear hint
  to re-run Painter with `Export PNGs` enabled.

Version `0.1.16` applies this correction on both sides and was installed into
the local Photoshop External plugin path.

### 0.12 Painter opacity unit correction

The first successful top-level PNG placement test showed that Photoshop layers
were created, but most imported layers appeared at `1%` opacity. The selected
`build_request.json` records Painter opacity values as normalized floats:
`1` means fully opaque and `0.55` means 55%. Photoshop UXP layer opacity
expects percentages in the `0..100` range.

Correction:

- keep the Painter request contract unchanged because it reflects the host API;
- normalize opacity in the Photoshop builder immediately before assigning
  `duplicated.opacity`;
- treat values from `0` through `1` as normalized Painter opacity and multiply
  by 100;
- leave values above `1` as already-percent values for forward compatibility
  with any manually-authored or future request files.

Version `0.1.17` applies this correction in the Photoshop UXP builder.

### 0.13 Top-level blend-mode placement

The first editable-layer fidelity slice after opacity is to apply Photoshop
blend modes to the already-working top-level PNG placement path. Because Painter
stores blend modes per channel, Photoshop must prefer
`node.blend_decisions[request.channel].ps_blend_mode` over the collapsed
top-level `node.ps_blend_mode`. The collapsed field can be `null` when the
same node uses different modes across BaseColor, Opacity, and user channels.

Scope for this slice:

- apply blend mode only to top-level raster layers that are already duplicated
  from PNG assets;
- use Photoshop `constants.BlendMode[...]` values where available;
- skip `PASSTHROUGH` on raster layers because it is group-only;
- keep group construction, group blend modes, masks, clipping sub-effects,
  metadata suffixes, and sidecar JSON out of scope.

Version `0.1.18` applies this top-level raster blend-mode mapping in the
Photoshop UXP builder.

### 0.14 Top-level group construction

The next M2 structure slice creates Photoshop groups for top-level Painter
groups and places only their direct PNG child layers inside. The local
Photoshop UXP docs support this through:

- `document.createLayerGroup({ name, opacity, blendMode })` for an empty group;
- `layer.duplicate(groupLayer, constants.ElementPlacement.PLACEINSIDE, name)`
  to duplicate opened PNG pixels directly into that group;
- group property writes for `visible`, `opacity`, and `blendMode`.

Scope for this slice:

- only top-level Painter groups are created as Photoshop groups;
- only direct child nodes with `asset.path` are placed inside those groups;
- nested groups, masks, clipping sub-effects, metadata suffixes, and sidecar
  JSON remain out of scope;
- group visibility is set after child placement, matching the old plugin note
  that Photoshop can otherwise reset folder visibility during construction.

Version `0.1.19` applies this top-level group/direct-child raster mapping in
the Photoshop UXP builder.

### 0.15 Top-level group insertion correction

The first `0.1.19` host screenshot showed the `Working` Photoshop group was
created, but subsequent top-level raster layers were inserted inside that group.
This indicates Photoshop keeps the newly-created group as the active insertion
context, and later `duplicate(targetDocument)` calls can still land inside that
active group.

Correction:

- place all top-level raster nodes into the document first;
- create top-level groups afterward;
- place only each group's direct child PNGs with `PLACEINSIDE`;
- move the completed group back to its original top-level position by placing
  it below the nearest previous top-level raster or above the nearest next
  top-level raster;
- keep this as a host-ordering correction only; no nested groups, masks,
  clipping sub-effects, metadata suffixes, or sidecar JSON are added here.

Version `0.1.20` applies this top-level group insertion correction.

### 0.16 Default Photoshop layer cleanup and child asset diagnostics

The next host screenshot showed the top-level hierarchy was corrected, but the
new document still contained Photoshop's default empty `Layer 1`. That layer is
not part of the Painter request and should be removed immediately after
`app.createDocument()` creates the new document, before any Painter layers are
placed. The local Photoshop UXP docs support `layer.delete()`. Cleaning the
single initial non-background layer before placement avoids deleting a real
Painter layer that happens to share Photoshop's default `Layer 1` name.

The same screenshot showed some `Working` child layers with small/low-detail
thumbnails. The PNG payloads on disk are non-empty, so the next debugging step
is to include each placed layer's source PNG path in the copyable panel summary.
This distinguishes a Photoshop placement issue from a Painter export-content
issue without adding image inspection logic to the plugin.

Version `0.1.21` removes the default empty Photoshop layer before requested
content placement and expands placement diagnostics with source PNG paths.

### 0.17 Group child PNG placement correction

The `0.1.21` host test proved the default Photoshop layer cleanup worked, but
all direct children of the `Working` group failed with:

```text
You can only move layers in the same document.
```

The failure happens because a PNG layer is opened in a temporary document, then
duplicated directly into a layer group owned by the target PSD. In this
Photoshop UXP runtime, cross-document duplication can target the document, but
the group insertion/move must happen after the duplicated layer already belongs
to the target document.

The corrected sequence is:

1. open the PNG as a temporary document;
2. duplicate its first layer into the target Photoshop document;
3. move the duplicated target-document layer into the target group with
   `ElementPlacement.PLACEINSIDE`;
4. apply name, visibility, opacity, and blend mode;
5. close the temporary PNG document without saving.

This keeps the current top-level group slice narrow and does not add masks,
nested groups, clipping sub-effects, metadata suffixes, or sidecar JSON.

Version `0.1.22` applies this group child placement correction.

### 0.18 Residual default layer cleanup

The `0.1.22` host test placed all 14 expected PNG layers and fixed the group
child placement errors, but Photoshop still showed a blank top-level `Layer 1`
even though the initial cleanup reported success. This suggests Photoshop can
recreate or retain a default empty layer after the document stops being empty.

The safer cleanup is now two-pass:

- delete the initial single default layer immediately after document creation;
- after all requested layers/groups are placed, delete a residual top-level
  `Layer 1` only if that name is not present in the request's top-level layer
  or group names.

This preserves a real Painter `Working/Layer 1` child layer and also avoids
deleting a future real top-level Painter layer named `Layer 1`.

Version `0.1.23` adds this residual top-level default-layer cleanup.

The user confirmed the `0.1.23` host test succeeds: Photoshop reports
`PNG layers placed: 14 of 14`, both default-layer cleanup passes report `yes`,
there are no placement errors, and the PSD saves successfully. The current M2
top-level raster/group placement slice is therefore validated in-host.

### 0.19 Layer mask placement slice

The next M2 slice should attach flattened Painter mask PNGs to the Photoshop
layers/groups already created by the validated top-level placement path. The
old ExtendScript plugin implemented this by opening a mask PNG, copying its
pixels, deleting the temporary layer, creating a reveal-selection mask on the
target layer, selecting the mask channel, and pasting the copied pixels.

Photoshop UXP now exposes a smaller documented path through the Imaging API:

- `imaging.getPixels({ documentID, colorSpace: "Grayscale", ... })` can read
  the opened mask PNG as grayscale image data;
- `imaging.putLayerMask({ documentID, layerID, imageData, replace: true })`
  can create/replace the target layer's user pixel mask.

Use the Imaging API first because it avoids fragile active-channel state and
keeps this slice smaller than a hand-ported `batchPlay` copy/paste sequence.
Keep failures non-fatal: if a mask fails, the raster/group layer should remain
placed and the panel should report a mask error separately from placement
errors.

Version `0.1.24` applies this first layer-mask placement slice for placed
top-level raster layers and direct group child raster layers. Nested groups,
clipping sub-effects, suffix metadata, and sidecar JSON remain out of scope.

The user confirmed the `0.1.24` host test succeeds: Photoshop reports
`Layer masks applied: 9 of 9`, all 14 PNG layers still place, both default
layer cleanup passes still report `yes`, and the PSD saves successfully.

### 0.20 Transparent per-layer PNG export correction

The successful mask test exposed a Painter-side asset issue: exported paint
layer PNGs still contain an opaque gray background. The current
`build_request.json` confirms why:

```json
{
  "padding": "Infinite",
  "keep_alpha": false
}
```

Those settings are useful for some final texture exports, but they are wrong
for editable Photoshop layer payloads. Per-layer PSD assets must preserve
transparency so Photoshop layer content and Photoshop layer masks do not fight
a baked gray background.

For Photoshop build bundles, the default export settings should therefore be:

- `padding: "Transparent"`;
- `dilation: 0`;
- `keepAlpha: true`.

This change affects newly generated Painter bundles. Existing bundles must be
re-exported from Painter so their PNG payloads are regenerated with alpha.

### 0.21 Metadata suffix and sidecar slice

The next M2 slice should add the minimum metadata needed for future
Photoshop-to-Painter sync-back:

- every plugin-created Photoshop layer/group gets a stable UID suffix;
- a sidecar JSON file is written next to the PSD.

Although the original design proposed a double-dagger suffix, the local docs
already show mojibake around that character in this Windows checkout. The
implementation should use an ASCII suffix for robustness:

```text
Layer Name [rz:5d76e]
```

The sidecar remains the authoritative lookup. The layer-name suffix is only the
stable anchor that survives user edits to the visible layer-name prefix.
Users can rename the readable prefix, but Phase 1 expects them to keep the
`[rz:<uid>]` suffix. If that suffix is deleted, the layer becomes untracked for
automatic sync-back and should be reported as a new/unmatched Photoshop layer.

Version `0.1.25` applies this metadata slice and writes
`<psdname>.rizum.json` next to the PSD.

### 0.22 Blend-gamma diagnostic slice

M3 starts with a non-fatal Photoshop-side diagnostic for the document-level
"Blend RGB Colors Using Gamma 1.0" setting. The local docs do not provide a
ready host-recorded descriptor, so the first implementation should attempt the
document `colorSettings.rgbColorBlendGamma = 1.0` `batchPlay` descriptor from
the design notes and report success or the exact host error in the panel.

This attempt must not block PSD construction. If the descriptor fails, the PSD
should still build normally and M3 should continue with either a corrected
recorded descriptor or the compensation fallback.

Version `0.1.26` adds this blend-gamma diagnostic.

### 0.23 Photoshop restart control removed

UXP docs expose `openExternal` / `openPath` behind `launchProcess`
permissions, but they do not expose a reliable "restart the current Photoshop
host" API. A plugin also should not silently terminate Photoshop because users
may have unsaved documents.

Version `0.1.27` briefly added a guided **Restart Photoshop** helper button,
but the control did not perform a real restart. Version `0.1.28` removes it so
the panel only exposes actions that directly advance the bridge workflow.

### 0.24 Photoshop host validation for build path

User-side Photoshop validation for `0.1.27` confirms the current M2/M3 build
path:

- `build_request.json` validation succeeds for a non-UDIM BaseColor request.
- PSD creation succeeds at 4096x4096, 72 ppi.
- Top-level group creation succeeds: 1 of 1 group.
- PNG layer placement succeeds: 14 of 14 layers.
- Layer mask application succeeds: 9 of 9 masks.
- The automatic `rgbColorBlendGamma = 1.0` diagnostic appeared to report
  success in panel text, but Photoshop also showed a host modal error:
  `The command "Set" is not currently available.`
- Default Photoshop `Layer 1` cleanup succeeds, including the residual
  top-level cleanup pass.
- Sidecar JSON writing succeeds.
- PSD saving succeeds.

This means the next implementation focus should move from basic Photoshop PSD
construction to unsupported nested effects, clipping behavior, and the
Photoshop-to-Painter push path.

### 0.25 Unplaced request-node metadata

The M1 test request contains mask-stack effects such as `AnchorPointEffect`
nodes. These nodes are intentionally not placed as standalone Photoshop layers
in the current M2 build; their rendered result is already baked into the
flattened mask PNG applied to the parent layer.

Version `0.1.29` records those unplaced request nodes in the Photoshop panel
summary and in the sidecar JSON under `unplaced_nodes`. This avoids a future
Push to Painter implementation mistaking baked mask-stack effects for missing
Photoshop layers. The PSD layer construction path remains unchanged.

### 0.26 Disable automatic blend-gamma Set command

Photoshop host validation for `0.1.29` showed a blocking modal:

```text
Rizum PT-to-PS Bridge: The command "Set" is not currently available.
```

The most likely source is the automatic `rgbColorBlendGamma = 1.0` `batchPlay`
`set` descriptor. Even if the panel summary previously printed `Blend gamma
set: yes`, a host modal makes the descriptor unsafe for the normal build path.

Version `0.1.30` disables this automatic command and reports it as skipped. It
also removes the unused first-pass default-layer cleanup report; only the
effective top-level `Layer 1` cleanup is shown.

### 0.27 Push-to-Painter preview slice

M4 should start with a read-only preview before any Photoshop pixels are
exported or Painter inbox files are written. Version `0.1.31` changes the
**Push to Painter** button from placeholder text to a sidecar-driven preview:

- user selects the `.rizum.json` sidecar;
- UXP scans the active Photoshop document's layer tree;
- layer names are matched by the ASCII ` [rz:<uid>]` suffix;
- sidecar records are categorized as matched editable, known cannot-sync,
  missing tagged records, new untagged Photoshop layers, unmatched tagged
  Photoshop layers, and duplicate UID warnings;
- no `_pt_sync_inbox` files are written yet.

This validates the suffix + sidecar matching contract before adding PNG export,
hash comparison, or Painter-side inbox application.

User-side Photoshop validation for `0.1.31` confirmed the preview matching
contract on the current test PSD:

- sidecar records: 15;
- Photoshop layers scanned: 15;
- matched editable records: 15;
- missing tagged records, new untagged layers, unmatched tagged layers, and
  duplicate UIDs: all 0;
- known unplaced request nodes: 10.

Version `0.1.32` extends the preview with non-mutating diff/mask status. Because
the sidecar still has `baseline_hash: null`, diff status is reported as
`no_baseline_hash`. Mask status is detected with a best-effort Photoshop
`hasUserMask` property lookup and reported as intact, missing-or-applied, new,
or unknown. No Painter inbox files are written.

User-side Photoshop validation for `0.1.32` confirmed mask detection:

- matched editable records: 15 of 15;
- mask intact: 9;
- mask missing/applied, new masks, and mask unknown: all 0;
- no baseline hash yet: 15.

Version `0.1.33` writes best-effort SHA-1 baseline hashes for placed raster
source PNGs into the sidecar. Group records remain `baseline_hash: null`
because they do not have a direct source PNG. Push preview should therefore
move raster records from `no_baseline_hash` to `current_hash_pending`, leaving
actual current Photoshop pixel hashing for a later slice.

User-side validation for `0.1.33` showed the sidecar version updated but all 15
`baseline_hash` fields remained null. The likely cause is doing baseline PNG
file reads and sidecar writes inside the Photoshop `executeAsModal` block.
Version `0.1.34` moves baseline hashing and sidecar writing outside the modal
scope so the modal only covers Photoshop document mutation.

User-side validation after `0.1.34` still reported 15 records with
`no_baseline_hash`. Version `0.1.35` makes Push preview resilient by computing
missing baseline hashes directly from sidecar `asset_path` values in memory.
The sidecar file remains read-only during preview; the report now distinguishes
baseline sources: `sidecar`, `asset_path`, `missing`, or `error`.

User-side validation for `0.1.35` showed all 14 asset-path baseline attempts
failed with `Cannot read properties of undefined (reading 'digest')`. Photoshop
UXP does not expose `crypto.subtle.digest` in this environment. Version
`0.1.36` replaces Web Crypto SHA-1 with a small pure JavaScript SHA-1 helper
shared by Build and Push preview.

User-side validation for `0.1.36` confirmed the asset-path baseline fallback:
14 raster records computed baselines from source PNG assets, 0 baseline errors,
and the only missing baseline was the `Working` group record with no pixel
payload. The next diff slice must compare like with like: baseline and current
Photoshop layer hashes should both be computed from normalized Imaging API
pixel buffers, not from PNG file bytes versus live layer pixels.

Version `0.1.37` implements that normalized pixel-hash preview path. It adds a
shared `pixel-hash.js` helper that reads Photoshop Imaging API pixel buffers at
8-bit RGB/RGBA representation and hashes a small metadata header plus the
chunky pixel data. Build-side sidecars now mark new baseline hashes with
`baseline_hash_kind: "pixel_v1"`. Push preview trusts sidecar hashes only when
that kind is present; otherwise it computes the baseline from the source PNG
pixels and computes current hashes from the matched Photoshop layer pixels.

User-side validation for `0.1.37` showed the normalized baseline source path
still needs a modal scope. Opening the source PNG through `app.open()` is a
Photoshop state-changing operation and fails outside `executeAsModal`, even
when the caller only wants to read pixels and close the temporary document.
Version `0.1.38` wraps source-PNG pixel hashing in `executeAsModal` while
keeping sidecar JSON reads/writes outside modal scopes.

User-side validation for `0.1.38` confirmed the modal-wrapped source PNG path
works for 12 raster records, but current Photoshop layer `getPixels()` also
requires a modal scope in this host. The same test also showed fully empty
source PNG layers can produce `grabPixels: got invalid empty image region`.
Treat empty pixel regions as a stable empty-pixel hash rather than an error so
empty-vs-empty reports `unchanged` and empty-vs-painted reports `changed`.

Version `0.1.39` wraps current Photoshop layer pixel hashing in a modal scope
and adds a stable empty-pixel hash fallback for Photoshop Imaging API empty
region errors.

User-side validation for `0.1.39` produced 0 hash errors and 14 computed
baselines, but 7 masked layers reported changed. This indicates Photoshop
`getPixels()` is returning the current layer with its user mask applied, while
the temporary source-PNG baseline was still unmasked. Version `0.1.40` applies
`mask_path` to the temporary source PNG before hashing so masked current pixels
and masked baseline pixels use the same representation.

User-side validation for `0.1.40` confirmed the normalized diff preview is now
clean for an unedited PSD: 14 raster records reported `unchanged`, 0 reported
`changed`, 0 current pixel hash errors, and 0 baseline hash errors. The only
record without a baseline remains the `Working` group, which has no direct
pixel payload. This closes the M4 read-only diff-preview gate.

Version `0.1.41` starts the write-out side of M4 without applying anything in
Painter. The **Push to Painter** button now runs the same preview first, then
exports only `changed` raster records to PNG files and writes a
`manifest.json` under `<sp_project_dir>/_pt_sync_inbox/<psd>_<timestamp>/`.
If there are no changed layers, no inbox folder is created. If any changed
layer export fails, the manifest is not written so Painter will not see a
partial push.

User-side Photoshop validation for `0.1.41` confirmed both write-out branches:
an unedited PSD reported 14 unchanged raster records, selected 0 changed
layers, and wrote no inbox; after editing one Photoshop layer, the panel
selected 1 changed layer, exported 1 PNG, and wrote a valid Painter inbox
manifest under the current Painter project directory.

The next Painter-side slice should remain read-only: scan the current
project's `_pt_sync_inbox`, parse any `manifest.json` files, verify that each
referenced PNG exists, and display the pending layer updates in the Painter
panel. Actual layer-stack mutation stays deferred until this inbox-discovery
step is validated in Painter.

User-side Painter validation for `0.1.42` confirmed the read-only inbox scan:
Painter found the Photoshop-created `_pt_sync_inbox`, parsed 1 valid manifest,
verified 1 referenced PNG, and displayed the pending `Layer 1 [rz:9bd5f]`
update.

Version `0.1.43` adds the first minimal Painter apply slice. It imports PNGs
from the newest valid push manifest as project-embedded `Usage.TEXTURE`
resources, finds the original target node by `sp_uid`, inserts a top Fill
effect into that node's content stack, sets the Fill source to the imported
resource for the manifest channel, and renames the manifest to
`manifest.applied.json` only if all layer updates succeed. This is intentionally
not a full final sync algorithm yet: it validates embedded resource import and
target-node mutation before adding the richer diff dialog, conflict detection,
mask apply handling, and automatic watching.

User-side Painter validation for `0.1.43` reported the apply summary as
successful, but Painter crashed when the user rotated the 3D viewport
afterward. Treat the content-stack insertion strategy as unsafe until proven
otherwise. Version `0.1.44` changes the minimal apply strategy to insert a
standalone Fill layer above the target node instead of inserting a Fill effect
inside the target node. This keeps the original layer internals untouched and
makes the temporary PS sync payload easier to inspect, hide, delete, or undo.

User-side Painter feedback after `0.1.44` showed `Apply Latest PS Inbox`
correctly reports no pending manifest after a successful apply because the
manifest has already been renamed to `manifest.applied.json`. The same session
also showed the dock can remain visible while its child controls disappear
after some use. Version `0.1.45` keeps a module-level strong reference to the
active panel object and explicitly stops the panel timer during unregister, so
Qt/Python ownership cannot drop the panel state while Painter still owns the
dock widget.

Further Painter host validation showed the standalone Fill-layer strategy is
also not safe enough: the 4K imported resource can leave Painter generating a
thumbnail, make viewport rotation unusably slow, and crash when the generated
layer is deleted. Version `0.1.46` therefore disables actual Painter mutation
from the panel. The former apply button is now a safe validation action: it
checks the newest pending manifest and PNG files, reports the pending updates,
but does not call `import_project_resource`, does not insert layers/effects, and
does not rename the manifest. The next real apply design must avoid immediate
4K project-resource import on the UI/viewport path or use an explicit,
warned, asynchronous import workflow.

User direction changed after the `0.1.46` Painter validation: Photoshop-to-
Painter should no longer try to automate matching, inbox manifests, Painter
resource import, or layer-stack mutation. The active return path is now a
manual Photoshop export tool. The user selects the Photoshop layers they want
to return to Painter and chooses one of two export modes:

- applied-mask export: one PNG per selected layer, with the current Photoshop
  layer mask applied to the exported pixels;
- separate layer/mask export: one PNG for the selected layer content plus a
  separate grayscale mask PNG when the layer has a user mask.

The user then imports or places those PNGs into Substance Painter manually.
This removes the fragile dependencies on `[rz:<uid>]` suffix preservation,
sidecar matching, changed/unchanged hash detection, `_pt_sync_inbox` manifests,
and automatic Painter resource import.

The relevant local Photoshop/UXP docs support this simpler path:

- `Document.activeLayers` exposes the user's current layer selection.
- `core.executeAsModal` is required around Photoshop document operations in
  this runtime, matching previous host errors for `open`, `getPixels`, and
  related document access.
- `imaging.getPixels` can read rendered selected-layer pixels.
- `imaging.getLayerMask` can read a user layer mask as image data.
- `Layer.layerMaskDensity` is a documented read/write percentage and is the
  best available temporary switch for exporting separate layer content without
  the mask applied, followed by restoring the original density.
- `storage.localFileSystem.getFolder()` and `Folder.createFile()` provide the
  user-selected output folder and PNG file entries.
- A temporary transparent document plus `saveAs.png()` is the existing proven
  UXP pattern in this project for writing image data to PNG.

Version `0.1.47` implements this manual selected-layer export in the Photoshop
panel and treats the automatic push/inbox path as deprecated. Version `0.1.48`
keeps the same manual workflow and adds the empty-pixel export fix for
Photoshop's `No pixels in the requested area` response.

The applied-mask export mode should also populate `maskDetected` in the panel
details. It still exports only one applied PNG per selected layer, but it should
probe and dispose the user mask so the diagnostics are consistent across both
manual export modes. Version `0.1.49` applies this reporting-only refinement.

The next manual-export refinement should improve diagnostics without changing
the workflow: record per-selected-layer export details in the panel result.
Each layer should report the original Photoshop layer name, whether a user mask
was detected, and which PNG files were written. This makes user host testing
easier without reintroducing manifests, sidecars, or automatic Painter import.

User validation of the separate layer/mask export found that Photoshop can
return `No pixels in the requested area` for a selected layer that still has a
detectable mask. Treat this the same as the existing empty-region case: export
a transparent full-document PNG for the layer instead of failing the whole
layer entry, then continue exporting the separate mask PNG if one exists.

User feedback after `0.1.50` confirmed that visible `[rz:<uid>]` suffixes are
no longer desirable now that Photoshop-to-Painter return is manual. Remove the
suffix from Photoshop layer/group names and keep UID/provenance only in the
sidecar. The old suffix-based matching notes remain historical context for the
deprecated automatic push path.

The attempted direct content-effect clipping slice exposed a Painter export
constraint. Request nodes carry `content_effects`, but `alg.mapexport.save`
accepts layer UIDs for channel/mask exports in this runtime and rejects effect
UIDs. The exporter must therefore not annotate `FillEffect`, `PaintEffect`,
or other effect nodes as independent PNG assets. Content/mask effects remain
metadata or are baked into their parent layer/mask export until a supported
per-effect export strategy is found and host-validated.

Nested group reconstruction can be implemented without a new Painter export
primitive because nested groups only need hierarchy and already-exported
descendant layer PNGs. The Photoshop builder should recurse through group
children, create a Photoshop group for every placeable Painter group, move
nested groups into their parent group, and keep nested asset nodes out of the
unplaced report once created.

Nested content-effect chains and filter/generator-specific reconstruction
remain later fidelity work. A fuller future slice may wrap layers into a
dedicated Photoshop group with the parent mask on the group, but it first needs
a valid source PNG for each effect.

The Photoshop panel should not present all non-placed request nodes as equal
problems. Split them into:

- `known_baked`: expected metadata already represented by a parent raster or
  mask PNG, especially mask-stack effects;
- `unsupported`: known fidelity work that is recorded for provenance but not
  editable yet, especially content effects after the effect-UID export failure;
- `needs_attention`: a request node with an asset or mask asset that the build
  tree did not place.

This keeps normal baked mask/effect provenance from looking like a failed PSD
build while still surfacing true missing asset coverage.

For multi-channel or multi-texture-set exports, Photoshop can reduce repeated
manual file picking by accepting a folder and recursively finding
`build_request.json` files. Batch build should remain conservative: process
requests sequentially, report per-request failures, keep going after failures,
and close a document only after its PSD save succeeds. This avoids leaving
dozens of 4K PSDs open while still preserving failed documents for inspection
when saving did not complete.

## Summary of findings

- Every capability in `design.md §5–6` that is SP-side has a Python API
  mapping except map-export gaps: per-layer PNG export still needs
  `alg.mapexport.save`, project export path uses `alg.mapexport.exportPath`,
  and stack-level used-channel filtering uses `alg.mapexport.channelIdentifiers`
  via `substance_painter.js.evaluate`.
- `design.md §4` (color fidelity bake vs pre-compensation), `§5` (layer
  structure mapping), and `§7` (metadata schema) remain feasible for the
  SP-to-PS build path.
- Paint layer strokes are not Python-writable. The earlier automatic PS-to-SP
  apply path tried generated Fill layers as a workaround, but user host testing
  showed that approach is too heavy and crash-prone for the current 4K payload.
- `design.md §6` has been revised: Phase 1 return data is manual Photoshop PNG
  export, not automatic Painter inbox import or layer-stack mutation.

---
