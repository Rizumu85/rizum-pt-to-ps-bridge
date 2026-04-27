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
- [ ] Host-test Painter export on representative projects: non-UDIM,
      multi-UDIM, grouped layers, masks, anchor references, and at least one
      unsupported blend/effect that must bake.
- [ ] Decide how to populate `normal_map_format` for already-open Painter
      projects, because the local docs do not expose a direct getter.

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
- [x] Create a Photoshop document at the requested size and resolution.
- [x] Resolve request-path PSD saving through UXP file entries.
- [x] Place top-level raster PNGs and group child PNGs into the target PSD.
- [x] Preserve layer/group visibility, opacity, and per-channel Photoshop blend
      mode where representable.
- [x] Remove Photoshop's empty default `Layer 1` without deleting real Painter
      layers named `Layer 1`.
- [x] Attach flattened mask PNGs to placed Photoshop raster layers.
- [x] Add readable ` [rz:<uid>]` suffixes and write a `.rizum.json` sidecar for
      provenance and possible future automation.
- [x] Record request nodes that are intentionally not placed as separate
      Photoshop layers.
- [x] Keep document blend-gamma mutation disabled in normal builds because the
      host can show a blocking "Set is not currently available" modal error.
- [ ] Host-test remaining PSD fidelity gaps: clipping behavior, nested groups,
      baked unsupported modes, color-layer behavior, and normal-channel output.
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
- [x] Add `Export Selected (Applied Mask)` for one PNG per selected Photoshop
      layer with the current mask applied.
- [x] Add `Export Selected + Masks` for a layer PNG plus a separate grayscale
      mask PNG when the selected layer has a user mask.
- [x] Use a user-chosen export folder through UXP local file storage.
- [x] Keep filenames human-readable and order-prefixed so users can inspect
      them before manually importing to Painter.
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
- [ ] Add matching uninstall support for the Windows offline path.
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
