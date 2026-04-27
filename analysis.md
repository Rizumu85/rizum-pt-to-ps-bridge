# API Analysis

## Current Project State

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

## 0. Local API documentation coverage

| Area | Included local source | Coverage status |
|---|---|---|
| Substance Painter Python API | `pt-python-doc-md/substance_painter/` | Covered for traversal, export, resources, UI, events, layer-stack mutation, color management, and JS bridge |
| Legacy Painter JS API | `javascript-doc/` | Covered for the two required fallbacks: `alg.mapexport.save` and `alg.mapexport.exportPath` |
| Photoshop DOM / UXP / Spectrum | `uxp-photoshop-main/src/pages/ps_reference/`, `uxp-photoshop-main/src/pages/uxp-api/`, `uxp-photoshop-main/src/pages/guides/` | Covered for PSD creation, layers, files, modal execution, panel UI, and `batchPlay` escape hatches |
| Host-recorded Action Manager descriptors | Not included as ready-to-use project files | Must be recorded or validated in Photoshop for layer-mask pixel transfer and the RGB blend-gamma setting |

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
panel and treats the automatic push/inbox path as deprecated.

## Summary of findings

- Every capability in `design.md §5–6` that is SP-side has a Python API
  mapping, **except per-layer PNG export** — that requires one JS fallback
  (`alg.mapexport.save`) via `substance_painter.js.evaluate`.
- `design.md §4` (color fidelity bake vs pre-compensation), `§5` (layer
  structure mapping), and `§7` (metadata schema) remain feasible for the
  SP-to-PS build path.
- Paint layer strokes are not Python-writable. The earlier automatic PS-to-SP
  apply path tried generated Fill layers as a workaround, but user host testing
  showed that approach is too heavy and crash-prone for the current 4K payload.
- `design.md §6` has been revised: Phase 1 return data is manual Photoshop PNG
  export, not automatic Painter inbox import or layer-stack mutation.

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

## 3. UXP Photoshop API

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
| SP Python has no per-layer `last_modified` timestamp | Use channel/tile cache-key comparison or re-exported hashes for conservative conflict warnings |

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
- **UXP `getEntryWithUrl("file:...")` with `fullAccess`**: referenced by the
  local UXP changelog and implied by the manifest v5 permission model, but
  the generated reference page is not expanded in this repo. Validate in-host
  before relying on path-only sidecar writes.
- **Panel UI behavior while `executeAsModal` is running**: per docs the
  panel stays responsive (events queue up). If we hit a blocking issue,
  split the long export into smaller modal scopes per UDIM tile.
- **PSD "Blend RGB Colors Using Gamma 1.0" settability via UXP** — see
  §6.3 below. Big potential payoff, verification needed at M3 start.
- **Current Painter normal-map orientation getter**: `NormalMapFormat` is
  documented for project creation settings, but no direct getter for the
  currently opened project was found in the local `project.md`. Store the
  value when known, infer from existing normal sources if possible, or expose
  a user setting before Normal-channel sync-back.

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
Painter, the only host call used is still `alg.mapexport.save`.

`build_request.json` keeps the Python-facing channel name (for example
`BaseColor`) and also stores `channel_identifier` (for example `basecolor`) for
the legacy JS `alg.mapexport.save` call. The JS docs define export channels as
channel identifiers, not Python enum names.
