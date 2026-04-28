# Rizum PT-to-PS Bridge Phase 1 Plan

This plan follows the current Rizum Guidelines structure: high-level directions
first, concrete implementation steps second. Technical findings live in
`analysis.md`; user-facing behavior and workflow design live in `design.md`.

## Working Agreement

- Rizum Guidelines are active for this project/thread until the user says otherwise.
- Karpathy Guidelines are active for this project/thread until the user says otherwise.

Working mode:

- Work in the local tree only. Do not create or switch branches unless the user
  asks.
- Write project files, code comments, and technical docs in English.
- Summaries in chat should be in Chinese.
- Do not run syntax, build, or test commands by default. Run checks only when
  the user asks, or when debugging feedback makes the check necessary.
- Leave Photoshop and Substance Painter functional testing to the user unless
  the user explicitly asks the agent to perform it.

## Direction 1: Painter Export Request

Goal: Painter creates a reliable `build_request.json` bundle with PNG payloads
that Photoshop can consume to build an editable PSD.

- [x] Keep the repository loadable from Painter's Python plugin directory with
      root loader shims and root `plugin.json`.
- [x] Keep Painter startup project-agnostic so the plugin can load when no
      Painter project is open.
- [x] Traverse texture sets, stacks, channels, layer trees, groups, content
      effects, mask effects, blend modes, opacity, visibility, and UV tiles.
- [x] Use the legacy Painter JS `alg.mapexport.save` fallback for per-layer,
      per-effect, and per-mask PNG export because the Python export API only
      exports full channels.
- [x] Emit one bundle per texture set / stack / channel / UV tile containing
      `build_request.json`, layer PNGs, mask PNGs, and baked PNGs.
- [x] Omit the user-facing `1001` suffix for non-UDIM projects while retaining
      internal default tile metadata.
- [x] Keep the Painter smoke-test UI minimal and user-triggered.
- [x] Remove Painter panel background polling so the plugin does not run a
      periodic Qt timer while the user paints.
- [x] Add a manual target picker to the Painter panel so the user can refresh
      texture-set/stack/channel options and export one selected target instead
      of always writing every project channel.
- [x] Add scoped Painter export buttons for the selected texture-set/stack and
      the selected channel across the project, reusing the existing exporter
      filters.
- [x] Write normal Painter exports to the project export path under
      `<project>_photoshop_export`, and add panel buttons to copy the last
      `build_request.json` path or open the output folder.
- [x] Write `_last_export.json` after each Painter export so Photoshop can
      build the current run without recursively picking up stale older bundles.
- [x] Add channel semantic metadata to each build request: label, role, format,
      bit depth, and color/data flag.
- [x] Show Painter user-channel labels in the target picker while keeping raw
      enum channel names as the internal export keys.
- [x] Use Painter user-channel labels in generated bundle and PSD filenames
      when labels are available.
- [x] Prune fully transparent exported layer PNGs from build requests and skip
      channel bundles that have no remaining layer PNGs.
- [x] Pre-filter export targets with Painter's JS used-channel list so
      stack-level empty channels are not offered or exported when the host
      reports them unused.
- [x] Use resolved JS map-export channel identifiers for user-channel PNG
      export so labels such as `SCol`, `TNrm`, and `SDF` are passed to
      `alg.mapexport.save` instead of raw `User*` enum names.
- [x] Use Python `active_channels` metadata to avoid exporting node PNGs for
      channels where that node is inactive.
- [x] Try multiple user-channel identifier spellings during PNG export and keep
      the first non-transparent result.
- [x] Prefer the old plugin's `documentStructure().stacks[].channels` channel
      identifiers when deciding Painter export channels, with
      `channelIdentifiers(stackPath)` as fallback.
- [x] Add a raw channel-string export path so resolved engine identifiers and
      documented user-channel spellings are passed to `alg.mapexport.save`
      without being remapped a second time.
- [x] Let Python `active_channels` override JS used-channel under-reporting so
      Fill layers with externally referenced maps can still generate user
      channel build requests.
- [x] Make selected-stack export pass the refreshed target's explicit channel
      list so the all-channels button matches single-channel target discovery.
- [x] Gate Painter export actions on `project.is_in_edition_state()` in
      addition to `project.is_open()`.
- [x] Show a modal Painter export progress dialog with Cancel, blocking normal
      UI interaction while checking cancellation between requests and PNG
      writes.
- [x] Replace the old long Painter dock controls with a three-button dock and
      an Export dialog that lets the user choose visible stacks/channels before
      writing build bundles.
- [x] Add a Painter Settings dialog for machine-level Photoshop path, infinite
      padding, and optional bit-depth override stored with Qt `QSettings`.
- [x] Host-confirm single-channel and selected-stack export on the current
      Wings reference-map case.
- [ ] Design and host-test an opt-in Python solo-export fallback for UDIM
      per-tile per-layer PNGs using visibility isolation, `ScopedModification`,
      `application.disable_engine_computations()`, and
      `export_project_textures(... uvTiles ...)`.
- [ ] Store project workflow metadata in build requests if UDIM export behavior
      needs to distinguish `UVTile` from `TextureSetPerUVTile`.
- [ ] Host-test Painter export on representative projects: non-UDIM,
      multi-UDIM, grouped layers, masks, anchor references, and at least one
      unsupported blend/effect that must bake. Multi-UDIM per-layer fidelity
      depends on the solo-export fallback before claiming full support.
- [ ] Decide how to populate `normal_map_format` for already-open Painter
      projects: try direct JS settings if available, infer from
      `SourceBitmap.get_color_space()` on normal sources, then fall back to a
      user setting stored in `project.Metadata`.
- [ ] Move project-scoped preferences to `project.Metadata` when the full
      export dialog grows beyond the current smoke-test panel.
- [ ] If future automation needs Painter-change detection, populate
      `baseline_cache_key` from `TextureStateEvent.cache_key` instead of
      leaving it permanently null.

## Direction 2: Photoshop PSD Build

Goal: Photoshop consumes Painter bundles and builds editable PSDs that preserve
as much Painter structure, mask data, blend behavior, and file naming as the
hosts allow.

- [x] Load the UXP plugin separately from Painter; Photoshop does not discover
      plugins from Painter's Python plugin directory.
- [x] Use a robust plain-HTML panel shell that works in the user's offline
      Photoshop 2025 setup.
- [x] Provide `Build from Painter` to choose and validate a
      `build_request.json`.
- [x] Add a direct `Build Request Path` flow so users can paste the path copied
      from Painter instead of navigating through the file picker every time.
- [x] Add a `Paste Request Path` helper in the Photoshop panel with a manual
      Ctrl+V fallback when UXP clipboard reading is unavailable.
- [x] Add `Build Request Folder` so Photoshop can recursively build all
      `build_request.json` files under a selected export folder.
- [x] Add `Build Export List` so Photoshop can build only the requests listed
      by Painter's latest scoped export.
- [x] Show channel semantics in Photoshop build summaries and store them in the
      `.rizum.json` sidecar.
- [x] Leave PSDs open after **Build Export List** so small scoped batches are
      inspectable immediately after save.
- [ ] Add Painter settings for the Photoshop executable path and an explicit
      **Export and Build in Photoshop** action.
- [ ] Generate a `.psjs` build-list launcher from Painter and host-validate
      whether launching Photoshop with that script path works like the old JSX
      command-line flow.
- [x] Create a Photoshop document at the requested size and resolution.
- [x] Resolve request-path PSD saving through UXP file entries.
- [x] Place top-level raster PNGs and group child PNGs into the target PSD.
- [x] Build nested Photoshop groups recursively when nested Painter folders
      contain placeable raster descendants.
- [x] Preserve layer/group visibility, opacity, and per-channel Photoshop blend
      mode where representable.
- [x] Remove Photoshop's empty default `Layer 1` without deleting real Painter
      layers named `Layer 1`.
- [x] Attach flattened mask PNGs to placed Photoshop raster layers.
- [x] Keep Photoshop layer/group names clean by removing visible ` [rz:<uid>]`
      suffixes; store UID/provenance in the `.rizum.json` sidecar instead.
- [x] Record request nodes that are intentionally not placed as separate
      Photoshop layers.
- [x] Split non-placed request node reporting into known baked metadata,
      unsupported editable effects, and assets needing attention.
- [x] Stop exporting Painter effect UIDs as standalone PNG assets after host
      validation showed `alg.mapexport.save([effectUid, channel])` fails.
- [x] Abandon editable content-effect clipping reconstruction for Phase 1 and
      keep those effects as sidecar provenance baked through parent exports.
- [x] Keep document blend-gamma mutation disabled in normal builds because the
      host can show a blocking "Set is not currently available" modal error.
- [ ] Host-test remaining PSD fidelity gaps: nested groups, baked unsupported
      modes, color-layer behavior, and normal-channel output.
- [ ] Validate whether a recorded `batchPlay` descriptor can safely set
      document-level "Blend RGB Colors Using Gamma 1.0" without host modal
      errors. Keep it off by default until proven safe.

## Direction 3: Manual Photoshop Return Export

Goal: Photoshop-to-Painter return data is simple and manual: the user selects
Photoshop layers, exports PNG files, and imports or places them in Painter
manually.

- [x] Deprecate the automatic `_pt_sync_inbox` / manifest / Painter resource
      import path after user testing showed 4K thumbnail stalls, viewport
      slowdown, and crash risk.
- [x] Remove the active `Push to Painter` UI path from the Photoshop panel.
- [x] Remove the Painter panel's manual `_pt_sync_inbox` scan entry so the UI
      no longer points users toward the deprecated automatic return path.
- [x] Add `Export Selected (Applied Mask)` for one PNG per selected Photoshop
      layer with the current mask applied.
- [x] Add `Export Selected + Masks` for a layer PNG plus a separate grayscale
      mask PNG when the selected layer has a user mask.
- [x] Use a user-chosen export folder through UXP local file storage.
- [x] Keep filenames human-readable and order-prefixed so users can inspect
      them before manually importing to Painter.
- [x] Report per-selected-layer export details in the Photoshop panel: original
      layer name, mask detected yes/no, and files written for that layer.
- [x] Treat Photoshop Imaging API empty-pixel responses as valid transparent
      layer exports so empty or fully transparent selected layers do not block
      separate mask export.
- [x] Make applied-mask export mode report `mask detected=yes/no` too, without
      exporting a separate mask file in that mode.
- [ ] Host-test applied-mask export in Photoshop: select one or more raster
      layers, export, and confirm the PNGs open correctly.
- [ ] Host-test separate layer/mask export in Photoshop: select a masked layer,
      confirm `_layer.png` and `_mask.png` are written, and confirm whether
      temporarily setting `layerMaskDensity = 0` produces the intended
      unmasked layer content in Photoshop 2025.
- [ ] If `layerMaskDensity = 0` does not reliably export unmasked content,
      revise the separate export path to a safer Photoshop-supported method or
      clearly label the layer PNG as mask-applied.

## Direction 4: Local Installation And Distribution

Goal: The project can be loaded locally by Painter and Photoshop without
branching, Creative Cloud dependency, or manual file copying by the user.

- [x] Keep this checkout usable directly inside Painter's Python plugin folder.
- [x] Provide a Windows Photoshop installer that copies `ps_plugin/` into
      `%APPDATA%\Adobe\UXP\Plugins\External\com.rizum.pt-to-ps-bridge`.
- [x] Register the Photoshop UXP plugin in
      `%APPDATA%\Adobe\UXP\PluginsInfo\v1\PS.json` using UTF-8 without BOM.
- [x] Make the Windows installer clean this plugin's target directory before
      copying files so removed source files do not linger in Photoshop's UXP
      External folder.
- [ ] Host-validate the Windows offline installer after a full Photoshop
      restart whenever the manifest version or installed files change.
- [x] Add matching uninstall support for the Windows offline path: remove this
      plugin's UXP External folder and delete its `pluginId` entry from
      `%APPDATA%\Adobe\UXP\PluginsInfo\v1\PS.json`.
- [ ] Add and validate a macOS installer path only after the Windows local
      workflow is stable.
- [ ] Update README instructions whenever the tested install flow changes.

## Direction 5: Documentation Hygiene

Goal: Keep `analysis.md`, `design.md`, and `plan.md` useful for future agents
without turning them into noisy line-by-line logs.

- [x] Record Rizum and Karpathy activation in `AGENTS.md`.
- [x] Make `AGENTS.md` prefer loading local skills, with merged guideline text
      as fallback for agents that cannot load skills.
- [x] Keep `design.md` starting with `Project Goal`.
- [x] Clarify that `analysis.md` owns technical findings, `design.md` owns
      user-facing workflow/design, and `plan.md` owns directions plus concrete
      steps.
- [x] Revise the plan from historical milestones into Direction sections with
      concrete implementation steps.
- [ ] Update docs only when direction, implementation approach, API findings,
      or meaningful plan status changes.
- [ ] When user testing is needed, provide a short handoff with what changed,
      exact test steps, expected result, and what feedback to send back.

## Direction 6: Desktop Transfer Queue

Goal: Explore a future desktop bridge app that lets users manually map selected
Photoshop and Painter layer exports into chosen target layer positions.

- [x] Add a local HTML UI mockup that reflects the revised dock/export/settings
      direction and the hover-only bridge row/card behavior.
- [x] Revise the mockup toward the latest transfer design: explicit export
      group disclosure, clean export-dialog background, rounded no-outline
      footer buttons, masked layer indicators, independent Photoshop/Painter
      host cards, and Painter insertion-line feedback.
- [ ] Define the desktop app interchange manifest: source host, target host,
      exported PNG/mask files, source layer metadata, target tree snapshot, and
      requested insertion position.
- [ ] Add a host-plugin command to export selected layers plus a lightweight
      layer-tree snapshot for the desktop app.
- [ ] Add a host-plugin apply command that reads a desktop transfer manifest
      and inserts selected files at explicit target positions after user
      confirmation.
- [ ] Prototype the desktop UI with side-by-side Photoshop and Painter layer
      trees, drag placement, group hover highlights, insertion-line feedback,
      and an Apply button.
- [ ] Keep the desktop bridge manual and inspectable; do not reintroduce
      background sync, watchers, or automatic Painter resource import.
